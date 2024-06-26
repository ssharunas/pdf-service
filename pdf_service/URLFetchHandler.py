import io
from typing import Optional
from urllib.error import HTTPError

from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import BadRequest, Forbidden, HTTPException
from sentry_sdk import add_breadcrumb
from urllib.parse import urlparse, ParseResult
from pdf_service.data_uri import parse as datauri_parse
import weasyprint

from .errors import URLFetcherCalledAfterExitException


class URLFetchHandler:
    """
    Implements an url_fetcher for WeasyPrint.
    Normally WeasyPrint will swallow any url fetch errors and demote them to warning.
    This implementation keeps track of thrown errors and throws an exception if any occured.

    It's important to note that the `url_fetcher` is stored by HTML and will then be used by the
     `.render` method, so the render call has to be inside the with, too.

    :raise: Throws exceptions as defined in `_handle_fetch`

    :example:
    >>> from weasyprint import HTML
    >>>
    >>> with URLFetchHandler() as url_fetcher
    >>>   html = HTML(string=html_string, url_fetcher=url_fetcher)
    >>>   doc = html.render()
    """

    def __init__(self, files: Optional[MultiDict] = None, isAllowExternal: Optional[bool] = False):
        self.http_errors = []
        self.closed = False
        self.isAllowExternal = isAllowExternal
        self.files = files

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.closed = True
        if len(self.http_errors) == 1:
            raise self.http_errors[0]
        elif len(self.http_errors) > 1:
            try:
                description = '\n'.join(map(lambda x: str(x), self.http_errors));
            except:
                pass
            raise BadRequest(description="Multiple errors occurred\n" + description )

    def __call__(self, url: str):
        if self.closed:
            raise URLFetcherCalledAfterExitException()

        try:
            return self._handle_fetch(url)
        except HTTPException as error:
            self.http_errors.append(error)
            raise error
        except HTTPError as error:
            if error.code == 404:
                self.http_errors.append(Exception(f"Resource not found: {error.url}"))
            else:
                self.http_errors.append(error)
            raise error

    def _handle_fetch(self, url: str):
        """
        Handle the fetching of a single URL

        :param url: URL to fetch
        :return: Info dict about resolved url

        :raise: :class:`werkzeug.exceptions.BadRequest`, if file wasn't found internally
        :raise: :class:`ForbiddenURLFetchError`, if file can't be fetched because it's not allowed
        """
        if url.startswith("data:"):
            return self._handle_data_fetch(url)

        parsed = urlparse(url)
        if not bool(parsed.netloc):
            # No domain name -> internal fetch
            return self._handle_internal_fetch(url, parsed)
        else:
            # External
            return self._handle_external_fetch(url, parsed)

    def _handle_internal_fetch(self, url: str, parsed: ParseResult):
        filename = parsed.path.removeprefix('/')

        if self.files is None or len(self.files) == 0:
            raise BadRequest(
                'Referenced local file (%s) in basic mode' % filename
            )

        file = self.files.get(filename)

        if file is None:
            add_breadcrumb(message="Failed to fetch internal URL", data={'url': url})
            raise BadRequest(
                "Missing file (%s) required by html file" % filename
            )
        else:
            add_breadcrumb(message="Fetched internal URL", data={'url': url})
            return {
                'file_obj': file,
                'mime_type': file.content_type
            }

    def _handle_data_fetch(self, url: str):
        missing_padding = len(url) % 4
        url_padded = url if missing_padding == 0 else url + ("=" * missing_padding)
        (mimetype, _, _, _, data) = datauri_parse(url_padded)
        file = io.BytesIO(data)

        return {
            'file_obj': file,
            'mime_type': mimetype,
        }

    def _handle_external_fetch(self, url: str, parsed: ParseResult):
        if self.isAllowExternal:
            return weasyprint.default_url_fetcher(url)
        else:
            add_breadcrumb(message="Refused to fetch URL", data={'url': url})
            raise Forbidden(
                description="Attempted to fetch forbidden url (%r)" % url
            )
