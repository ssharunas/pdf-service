from flask import make_response

class URLFetcherCalledAfterExitException(Exception):
    def __init__(self):
        self.message = "Called URLFetchCather after it was closed."


class InvalidDataURI(ValueError):
    pass

def make_error(message, status):
    response = make_response(message, status)
    response.headers.set('Content-Type', 'text/plain')
    return response;