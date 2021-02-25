from sentry_sdk import init, start_span, set_context, add_breadcrumb, set_tag
from flask import Flask, request, make_response
from weasyprint import HTML
from sentry_sdk.integrations.flask import FlaskIntegration
import os
import werkzeug

from .errors import ForbiddenURLFetchError


pdf_service = Flask(__name__)
init(
    dsn=os.environ.get("SENTRY_DSN"),
    environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
    release=os.environ.get("SENTRY_RELEASE"),
    server_name=os.environ.get("HOST"),
    integrations=[FlaskIntegration()],
    traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "1.0")),
)

for k, v in os.environ.items():
    if k.startswith("SENTRY_TAG"):
        processed_key = k.replace("SENTRY_TAG_", "").lower()
        set_tag(processed_key, v)


@pdf_service.route('/generate', methods=['POST'])
def generate_pdf():
    with start_span(op='decode'):
        data = request.get_data(as_text=True)

    url_errors = []

    def url_fetcher(url):
        error = ForbiddenURLFetchError(url)
        add_breadcrumb(message="Refused to fetch URL (%s)" % url)
        url_errors.append(error)
        raise error

    with start_span(op='parse'):
        # noinspection PyTypeChecker
        html = HTML(string=data, url_fetcher=url_fetcher)

    with start_span(op='render'):
        doc = html.render()

    if len(url_errors) != 0:
        raise werkzeug.exceptions.Forbidden()

    with start_span(op='write-pdf'):
        pdf = doc.write_pdf()

    set_context("pdf-details", {
        "html_size": len(data),
        "pdf_size": len(pdf),
    })

    response = make_response(pdf)

    response.headers.set('Content-Type', 'application/pdf')
    response.headers.set('Content-Disposition', 'attachment; filename="generated.pdf"')

    return response


@pdf_service.route('/health', methods=['GET'])
def health():
    response = make_response("Healthy")
    return response


if __name__ == '__main__':
    pdf_service.run()