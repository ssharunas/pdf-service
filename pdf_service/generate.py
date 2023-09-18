from io import BytesIO
from os import read
from typing import Optional

from flask import make_response, request, Response
from sentry_sdk import start_span, set_context
from weasyprint import HTML
from werkzeug.datastructures import FileStorage
import werkzeug
import pypdf

from .URLFetchHandler import URLFetchHandler

def encrypt(data: bytes, password: str) -> bytes:
    reader = pypdf.PdfReader(BytesIO(data))
    writer = pypdf.PdfWriter(reader)

    for page in reader.pages:
        writer.add_page(page)

    writer.encrypt(password, algorithm="AES-256")
    with BytesIO() as output:
        writer.write(output)
        output.seek(0)
        return output.read()

def generate() -> Response:
    with start_span(op='decode'):
        if request.content_type.startswith("multipart/form-data"):
            # Multipart
            html_file: Optional[FileStorage] = request.files.get("index.html")
            if html_file is None:
                raise werkzeug.exceptions.BadRequest(description="No index.html present")
            html_size = html_file.content_length

        else:
            # Basic
            html_file: BytesIO = BytesIO(request.get_data())
            html_size = html_file.getbuffer().nbytes

    with URLFetchHandler(request.files, request.args.get("isAllowExternalResources", default= False, type= bool)) as url_fetcher:
        with start_span(op='parse'):
            html = HTML(
                file_obj=html_file,
                base_url='/',
                url_fetcher=url_fetcher,
                encoding = 'UTF-8'
            )

        with start_span(op='render'):
            doc = html.render(presentational_hints=True)

    with start_span(op='write-pdf'):
        pdf = doc.write_pdf()

    password = request.headers.get('X-Password') or request.args.get("password")
    if password:
        pdf = encrypt(pdf, password)

    set_context("pdf-details", {
        "html_size": html_size,
        "pdf_size": len(pdf),
    })

    response = make_response(pdf)

    response.headers.set('Content-Type', 'application/pdf')
    response.headers.set('Content-Disposition', 'attachment; filename="generated.pdf"')

    return response
