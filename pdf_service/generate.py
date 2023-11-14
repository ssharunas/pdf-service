from io import BytesIO
from typing import Optional
from os import listdir
from os.path import isfile, join

from flask import make_response, request, Response
from sentry_sdk import start_span, set_context
from weasyprint import HTML
from werkzeug.datastructures import FileStorage

import os
import werkzeug
import weasyprint

from .URLFetchHandler import URLFetchHandler
from .encryption import encrypt

css = [];

def loadCustomCss():
    path = os.environ.get('CSS_PATH') or './pdf_service/css'
    css.clear()
    for f in os.listdir(path):
        if not f.endswith('.css'):
            continue;
        filename = os.path.join(path, f)
        if os.path.isfile(filename):
            css.append(weasyprint.CSS(filename= filename))

loadCustomCss()

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

    baseUrl = request.headers.get('X-BaseUrl') or request.args.get("base-url")
    isAllowExternal = bool(baseUrl) or request.args.get("isAllowExternalResources", default= False, type= bool);

    with URLFetchHandler(request.files, isAllowExternal) as url_fetcher:
        with start_span(op='parse'):
            html = HTML(
                file_obj=html_file,
                base_url=baseUrl  or '/',
                url_fetcher=url_fetcher,
                encoding = 'UTF-8'
            )

        with start_span(op='render'):
            doc = html.render(presentational_hints=True, stylesheets=css)

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
