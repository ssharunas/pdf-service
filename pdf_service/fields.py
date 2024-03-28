from io import BytesIO
from os import write
import os
from flask import make_response, request, Response
from sentry_sdk import start_span
import pypdf
import fitz

from .errors import make_error

def get_fields() -> Response:
    with start_span(op='decode'):
        pdf = request.get_data()

    if not pdf:
        return make_error("Request body is empty. Body content must be application/pdf.", 400)

    try:
        reader = pypdf.PdfReader(BytesIO(pdf))
        fields = reader.get_form_text_fields()
    except Exception as e:
        return make_error(str(e.args[0]), 500)

    response = make_response(fields)
    response.headers.set('Content-Type', 'text/json')
    return response


def set_fields() -> Response:
    with start_span(op='decode'):
        if not request.content_type.startswith("multipart/form-data"):
            return make_error("Invalid content type. Expected 'multipart/form-data'", 400)

        # Multipart
        pdf = request.files.get("pdf")
        if not pdf:
            return make_error("Body form-data is missing pdf key with pdf binary data", 400)

        pdf = pdf.stream.read()
        if not pdf:
            return make_error("PDF file was empty.", 400)

        fields = {}
        for item in request.form:
            if item == 'pdf':
                continue
            fields[item] = request.form.get(item)

    try:
        pdf_document = fitz.open(stream=pdf, filetype="pdf")
        root_dir  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        font_path = os.path.join(root_dir, "fonts", "DejaVuSansCondensed.ttf")

        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)

            widgets = page.widgets()
            for widget in widgets:
                if widget.field_name in fields:
                    field_rect = widget.rect
                    field_value = fields[widget.field_name]
                    page.insert_text(field_rect.bl, field_value, fontfile=font_path, fontname="EXT_1", color=(0, 0, 0))
                    page.delete_widget(widget)
        
        pdf_document.subset_fonts()

        with BytesIO() as output:
            pdf_document.save(output, 7)
            output.seek(0)
            pdf_data = output.read()

    except Exception as e:
        response = make_response(str(e.args[0]), 500)
        response.headers.set('Content-Type', 'text/plain')
        return response
   
    response = make_response(pdf_data)
    response.headers.set('Content-Type', 'application/pdf')
    response.headers.set('Content-Disposition', 'attachment; filename="form.pdf"')

    return response