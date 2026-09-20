import base64
import io
import os
import tempfile

import colorgram
import cv2
import qrcode
from flask import render_template, request
from rembg import remove
from PIL import Image, ImageColor, ImageDraw, ImageOps
from pypdf import PdfReader
from pdf2docx import Converter

from app.utils import allowed_image_file, allowed_pdf_file, allowed_video_file


def _smart_background_remove(image):
    output = remove(image, alpha_matting=False)

    if isinstance(output, bytes):
        output = Image.open(io.BytesIO(output)).convert("RGBA")
    return output.convert("RGBA")


def _video_to_gif(video_bytes, suffix):
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as source_file:
        source_file.write(video_bytes)
        source_path = source_file.name

    try:
        capture = cv2.VideoCapture(source_path)
        if not capture.isOpened():
            raise ValueError("The uploaded video could not be read.")

        frames = []
        frame_limit = 150
        frame_count = 0
        while frame_count < frame_limit:
            success, frame = capture.read()
            if not success:
                break

            height, width = frame.shape[:2]
            if width > 640:
                resized_height = round(height * 640 / width)
                frame = cv2.resize(frame, (640, resized_height), interpolation=cv2.INTER_AREA)
            frames.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            frame_count += 1
        fps = capture.get(cv2.CAP_PROP_FPS) or 10
        capture.release()

        if not frames:
            raise ValueError("The uploaded video does not contain readable frames.")

        duration = max(40, round(1000 / min(fps, 20)))
        buffer = io.BytesIO()
        frames[0].save(
            buffer,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0,
            optimize=True,
        )
        return buffer.getvalue()
    finally:
        if os.path.exists(source_path):
            os.remove(source_path)


def _photos_to_gif(uploaded_files, delays, loop, crossfade, stack_frames, use_first_frame_background, optimize):
    images = []
    for uploaded_file in uploaded_files[:50]:
        image = Image.open(io.BytesIO(uploaded_file.read())).convert("RGB")
        images.append(image)

    if len(images) < 2:
        raise ValueError("At least two photos are required.")

    first_width, first_height = images[0].size
    output_width = min(first_width, 640)
    output_height = round(first_height * output_width / first_width)
    frames = []
    for image in images:
        frame = Image.new("RGB", (output_width, output_height), "white")
        contained_image = ImageOps.contain(image, (output_width, output_height))
        offset = ((output_width - contained_image.width) // 2, (output_height - contained_image.height) // 2)
        frame.paste(contained_image, offset)
        frames.append(frame)

    if use_first_frame_background:
        background = frames[0]
        frames = [Image.blend(background, frame, 1) for frame in frames]

    if crossfade:
        blended_frames = []
        blended_delays = []
        for index, frame in enumerate(frames):
            blended_frames.append(frame)
            blended_delays.append(delays[index])
            if index < len(frames) - 1:
                blended_frames.append(Image.blend(frame, frames[index + 1], 0.5))
                blended_delays.append(max(20, delays[index] // 2))
        frames = blended_frames
        delays = blended_delays

    buffer = io.BytesIO()
    frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=delays,
        loop=loop,
        disposal=1 if stack_frames else 2,
        optimize=optimize,
    )
    return buffer.getvalue()


def _pdf_to_docx(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if not any((page.extract_text() or "").strip() for page in reader.pages):
        raise ValueError("This PDF does not contain selectable text. Scanned PDFs need OCR before conversion.")

    source_path = None
    output_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as source_file:
            source_file.write(pdf_bytes)
            source_path = source_file.name

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as output_file:
            output_path = output_file.name

        converter = Converter(source_path)
        try:
            converter.convert(output_path)
        finally:
            converter.close()

        with open(output_path, "rb") as converted_file:
            return converted_file.read()
    finally:
        for path in (source_path, output_path):
            if path and os.path.exists(path):
                os.remove(path)


def init_routes(app):
    @app.route("/")
    def index():
        tools = [
            {
                "name": "QR Generator",
                "description": "Create QR codes from text, URLs, or contact info.",
                "href": "/qr-generator",
                "icon": "▣",
            },
            {
                "name": "Background Remover",
                "description": "Remove backgrounds from uploaded photos and download a clean result.",
                "href": "/background-remover",
                "icon": "◼",
            },
            {
                "name": "Color Extractor",
                "description": "Get dominant HEX color codes from an image palette.",
                "href": "/color-extractor",
                "icon": "◉",
            },
            {
                "name": "GIF Maker",
                "description": "Create an animated GIF from a video clip or photo sequence.",
                "href": "/gif-maker",
                "icon": "▶",
            },
            {
                "name": "PDF to Word",
                "description": "Convert a text-based PDF into an editable Word document.",
                "href": "/pdf-to-word",
                "icon": "▤",
            },
        ]
        return render_template("index.html", tools=tools)

    @app.route("/qr-generator", methods=["GET", "POST"])
    def qr_generator():
        qr_image = None
        qr_text = ""
        qr_color = "#111111"
        transparent_bg = False
        circular_qr = False
        error_message = None
        qr_download = None

        if request.method == "POST":
            qr_text = (request.form.get("qr_text") or "").strip()
            qr_color = request.form.get("qr_color") or "#111111"
            transparent_bg = request.form.get("transparent_bg") == "on"
            circular_qr = request.form.get("circular_qr") == "on"

            if not qr_text:
                error_message = "Please enter some text or a URL to generate a QR code."
            else:
                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                qr.add_data(qr_text)
                qr.make(fit=True)

                if circular_qr:
                    matrix = qr.get_matrix()
                    cell_size = 10
                    img_size = len(matrix) * cell_size
                    img = Image.new(
                        "RGBA",
                        (img_size, img_size),
                        (255, 255, 255, 0) if transparent_bg else (255, 255, 255, 255),
                    )
                    draw = ImageDraw.Draw(img)
                    color = ImageColor.getcolor(qr_color, "RGBA")

                    for y, row in enumerate(matrix):
                        for x, value in enumerate(row):
                            if not value:
                                continue
                            cx = x * cell_size + cell_size // 2
                            cy = y * cell_size + cell_size // 2
                            radius = cell_size // 2 - 1
                            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color)
                else:
                    img = qr.make_image(fill_color=qr_color, back_color=None if transparent_bg else "white")

                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                buffer.seek(0)
                encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
                qr_image = f"data:image/png;base64,{encoded}"
                qr_download = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return render_template(
            "qr_generator.html",
            qr_image=qr_image,
            qr_text=qr_text,
            qr_color=qr_color,
            transparent_bg=transparent_bg,
            circular_qr=circular_qr,
            error_message=error_message,
            qr_download=qr_download,
        )

    @app.route("/background-remover", methods=["GET", "POST"])
    def background_remover():
        image_data = None
        download_data = None
        error_message = None

        if request.method == "POST":
            uploaded_file = request.files.get("image")
            if not uploaded_file or uploaded_file.filename == "":
                error_message = "Please upload an image to remove the background."
            else:
                try:
                    input_bytes = uploaded_file.read()
                    image = Image.open(io.BytesIO(input_bytes)).convert("RGBA")
                    output = _smart_background_remove(image)
                    buffer = io.BytesIO()
                    output.save(buffer, format="PNG")
                    buffer.seek(0)
                    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    image_data = f"data:image/png;base64,{encoded}"
                    download_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
                except Exception:
                    error_message = "Unable to process that image. Please try a different file."

        return render_template(
            "background_remover.html",
            image_data=image_data,
            download_data=download_data,
            error_message=error_message,
        )

    @app.route("/gif-maker", methods=["GET", "POST"])
    def gif_maker():
        gif_data = None
        error_message = None

        if request.method == "POST":
            uploaded_video = request.files.get("video")
            uploaded_photos = [photo for photo in request.files.getlist("photos") if photo.filename]
            if uploaded_video and uploaded_video.filename:
                if not allowed_video_file(uploaded_video.filename):
                    error_message = "Please upload an MP4, MOV, AVI, MKV, or WebM video."
                else:
                    try:
                        gif_bytes = _video_to_gif(
                            uploaded_video.read(),
                            os.path.splitext(uploaded_video.filename)[1],
                        )
                        gif_data = base64.b64encode(gif_bytes).decode("utf-8")
                    except Exception:
                        error_message = "Unable to convert that video. Please try a different file."
            elif uploaded_photos:
                if not all(allowed_image_file(photo.filename) for photo in uploaded_photos):
                    error_message = "Please upload PNG, JPG, JPEG, or WebP photos."
                else:
                    try:
                        enabled_frames = request.form.getlist("frame_enabled")
                        selected_photos = [
                            photo
                            for index, photo in enumerate(uploaded_photos)
                            if not enabled_frames or index < len(enabled_frames) and enabled_frames[index] == "on"
                        ]
                        global_delay = max(1, int(request.form.get("global_delay", 35)))
                        frame_delays = request.form.getlist("frame_delay")
                        selected_delays = [
                            max(1, int(frame_delays[index])) if index < len(frame_delays) and frame_delays[index].isdigit() else global_delay
                            for index, enabled in enumerate(enabled_frames or ["on"] * len(uploaded_photos))
                            if enabled == "on"
                        ]
                        loop_value = request.form.get("loop_count", "").strip()
                        loop = int(loop_value) if loop_value.isdigit() else 0
                        gif_bytes = _photos_to_gif(
                            selected_photos,
                            [delay * 10 for delay in selected_delays],
                            loop,
                            request.form.get("crossfade") == "on",
                            request.form.get("stack_frames") == "on",
                            request.form.get("first_frame_background") == "on",
                            request.form.get("optimize_palette") == "on",
                        )
                        gif_data = base64.b64encode(gif_bytes).decode("utf-8")
                    except ValueError as error:
                        error_message = str(error)
                    except Exception:
                        error_message = "Unable to create a GIF from those photos. Please try different files."
            else:
                error_message = "Please upload a video or at least two photos."

        return render_template("video_to_gif.html", gif_data=gif_data, error_message=error_message)

    @app.route("/pdf-to-word", methods=["GET", "POST"])
    def pdf_to_word():
        document_data = None
        error_message = None

        if request.method == "POST":
            uploaded_file = request.files.get("pdf")
            if not uploaded_file or uploaded_file.filename == "":
                error_message = "Please upload a PDF to convert."
            elif not allowed_pdf_file(uploaded_file.filename):
                error_message = "Please upload a PDF file."
            else:
                try:
                    docx_bytes = _pdf_to_docx(uploaded_file.read())
                    document_data = base64.b64encode(docx_bytes).decode("utf-8")
                except ValueError as error:
                    error_message = str(error)
                except Exception:
                    error_message = "Unable to convert that PDF. Please try a different file."

        return render_template("pdf_to_word.html", document_data=document_data, error_message=error_message)

    @app.route("/color-extractor", methods=["GET", "POST"])
    def color_extractor():
        image_data = None
        colors = []
        error_message = None

        if request.method == "POST":
            uploaded_file = request.files.get("image")
            if not uploaded_file or uploaded_file.filename == "":
                error_message = "Please upload an image to extract colors."
            else:
                try:
                    input_bytes = uploaded_file.read()
                    image = Image.open(io.BytesIO(input_bytes)).convert("RGB")
                    buffer = io.BytesIO()
                    image.save(buffer, format="PNG")
                    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    image_data = f"data:image/png;base64,{encoded}"

                    extracted_colors = colorgram.extract(io.BytesIO(input_bytes), 5)
                    colors = [f"#{color.rgb[0]:02x}{color.rgb[1]:02x}{color.rgb[2]:02x}" for color in extracted_colors]
                except Exception:
                    error_message = "Unable to extract colors from that image. Please try another file."

        return render_template("color_extractor.html", image_data=image_data, colors=colors, error_message=error_message)
