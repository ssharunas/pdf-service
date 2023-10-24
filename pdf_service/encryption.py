from io import BytesIO
from os import read
from urllib import response

from flask import make_response, request, Response
from sentry_sdk import start_span
import pypdf
import sys

from .errors import make_error

def encrypt(data: bytes, password: str) -> bytes:
    reader = pypdf.PdfReader(BytesIO(data))

    if reader.is_encrypted:
        raise Exception('PDF is already encrypted. Can not re-encrypt encrypted PDF.');

    writer = pypdf.PdfWriter(reader)

    for page in reader.pages:
        writer.add_page(page)

    writer.encrypt(password, algorithm="AES-256")
    with BytesIO() as output:
        writer.write(output)
        output.seek(0)
        return output.read()

def encryptPdf() -> Response:
    with start_span(op='decode'):
        pdf = request.get_data()
    
    password = request.headers.get('X-Password') or request.args.get("password")
    if not password:
        return make_error('Password must not be empty', 400);

    try:
        with start_span(op='encrypt'):
            pdf = encrypt(pdf, password);
    except Exception as e:
        return make_error(str(e.args[0]), 500)

    response = make_response(pdf)

    response.headers.set('Content-Type', 'application/pdf')
    response.headers.set('Content-Disposition', 'attachment; filename="encrypted.pdf"')
    
    return response
