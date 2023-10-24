from io import BytesIO
from os import write
from flask import make_response, request, Response
from sentry_sdk import start_span
import pypdf

from .errors import make_error

def get_fields() -> Response:
    with start_span(op='decode'):
        pdf = request.get_data()

    if not pdf:
        return make_error("Request body is empty. Body content must be application/pdf.", 400)

    try:
        reader = pypdf.PdfReader(BytesIO(pdf))
        fields = reader.get_form_text_fields();
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

        pdf = pdf.stream.read();
        if not pdf:
            return make_error("PDF file was empty.", 400)

        fields = {};
        for item in request.form:
            if item == 'pdf':
                continue
            fields[item] = request.form.get(item);
    
    try:
        reader = pypdf.PdfReader(BytesIO(pdf))
        writer = pypdf.PdfWriter()

        writer.append(reader);

        for page in writer.pages:
            writer.update_page_form_field_values(page, fields)
            
        with BytesIO() as output:
            writer.write(output)
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
