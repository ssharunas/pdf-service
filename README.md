<h1 align="center">WeasyPrint in Docker</h1>
<p align="center"><strong>Stateless HTTP API to convert HTML to PDF</strong></p>
<p align="center">
  <a href="https://codecov.io/github/mormahr/pdf-service?branch=main"><img alt="codecov.io" src="https://codecov.io/github/mormahr/pdf-service/coverage.svg?branch=main"/></a>
  <a href="https://hub.docker.com/r/mormahr/pdf-service"><img alt="Docker Image Version" src="https://img.shields.io/docker/v/mormahr/pdf-service?sort=semver" /></a>
  <a href="https://hub.docker.com/r/mormahr/pdf-service"><img alt="Docker Pulls" src="https://img.shields.io/docker/pulls/mormahr/pdf-service" /></a>
  <a href="https://hub.docker.com/r/mormahr/pdf-service"><img alt="Docker Image Size" src="https://img.shields.io/docker/image-size/mormahr/pdf-service?sort=semver" /></a>
</p>

A dockerized HTTP service, that generates PDF files from HTML using [WeasyPrint][weasyprint].
The primary use-case is generation of documents from developer controlled templates, such as
invoices. It is not meant as a general webpage to PDF converter. The service expects input HTML and
other resources to be safe and doesn't do any hardening or sandboxing that would be required for
arbitrary inputs. Please consult the [security](#security) section of this document.

## Usage

Run the docker image `mormahr/pdf-service` and `POST` the HTML to `/generate` on port 8080.

Consult the [API](#API) section for details about supported features and how to use them.
See the [deployment](#deployment) section ([security](#security) in particular) for best practices in
production environments.

```sh
docker run --rm -d --name pdf -p 8080:8080 mormahr/pdf-service

curl \
  -H "Content-Type: text/html" \
  --data '<p>Hello World!</p>' \
  http://localhost:8080/generate \
  > hello_world.pdf

docker stop pdf
```

## API
### Endpoints
- [POST] **/encrypt** - puts a password on the pdf file. Pdf file must NOT be encrypted before passing it for encryption.
    *Parameters:*
  - ?password=string - encrypt generated pdf with given password. Password can also be provided via heder 'X-Password'. Header has higher priority over query parameter.
  
  *Example:*
  Make a `POST` request to `/encrypt` with the HTML file you want to encrypt as the body and password as a parameter. The response will be the PDF.
    ```sh
    curl \
        --data-binary @test.pdf \
        --output encrypted.pdf \
        https://pdf.example.com/encrypt?password=xxx
    ```

- [GET] **/form-fields** - gets all form fields in the pdf file
    *Example:*
	Make a `GET` request to `/form-fields` with pdf as body and `Content-Type`of `application/pdf`. Returns `text/json` with all form fields in pdf.
    ```sh
    curl \
        --data-binary @form-test.pdf \
        https://pdf.example.com/form-fields
    > { "field-name": "field-value", "field-name2": null }
    ```

- [POST] **/form-fields** - sets form field values in pdf and returns filled pdf.
    *Example:*
	Make a `POST` request to `/form-fields` with pdf and form field values, with a `Content-Type` of `multipart/form-data`.
    ```sh
    curl \
        -F pdf=@form-test.pdf \
        -F field-name=field-value \
        -F field-name2=field-value2 \
        --output filled_form.pdf \
        https://pdf.example.com/form-fields
    ```
	
- [POST] **/generate** - generates PDF from html content. Content may be provided either as "text/html" body, either as "multipart/form-data" (see below). In case of "multipart/form-data", additional resources may be provided, such as images, styles, etc.
    *Parameters:*
  - ?isAllowExternalResources=[True|**False**] - by default loading external resources (i.e. https://exaple.com/image.png), not included in request will result in an error. This parameter allows to change that behaviour.
  - ?password=string - encrypt generated pdf with given password. Password can also be provided via heder 'X-Password'. Header has higher priority over query parameter.
  - ?rotate=int - rotates all pages. Supported values: 0, 90: 180, 270

  *Basic "simple" API example without asset support:*
  Make a `POST` request to `/generate` with the HTML file you want to render as the body. The response will be the PDF file. 
    ```sh
    curl \
        -H "Content-Type: text/html" \
        --data '<p>Hello World!</p>' \
        --output hello_world.pdf \
        https://pdf.example.com/generate 
    ```
  *Multipart API example:*
    Make a `POST` request to `/generate` with a `Content-Type` of `multipart/form-data`.
    Provide your HTML input as `index.html` and add any other required assets. The assets can be referenced _in the HTML_ either as an absolute URL like `/image.png` or a relative one `image.png`. Relative URLs are resolved against `/`. **Omit the leading slash** for the `multipart/form-data` `name` attribute.
    ```sh
    curl \
        -F index.html=@index.html \
        -F image.png=@image.png \
        -F sub-path/image.png=@sub-path/image.png \
        --output hello_world.pdf
        https://pdf.example.com/generate \
    ```

    ```html
    <!-- index.html -->
    <p>With an image:</p>
    <img src="/image.png" />
    <img src="/sub-path/image.png" />
    ```

## Deployment
### Versioning

The docker image is tagged as `mormahr/pdf-service`.

We follow [semver][semver] as well as possible, including visual changes when we detect them.
As such, we also tag release versions like `:1.1.0`. We support semver major (`:1`) or minor (`:1.1`) tags that use the latest minor or patch
release version.

Images of the current development version are continuously pushed to the `:edge` tag.
We strongly recommend that you use a release version instead of `:edge`.

### Licensing

The service code is licensed under the MIT license. WeasyPrint, the underlying PDF generator
library, is licensed under the BSD license. The prebuilt production container image contains a 
variety of licenses, including GPLv2 and GPLv3 code.

### Security

It's not recommended allowing untrusted HTML input.
Use trusted HTML templates and sanitize user inputs.

Fetching of external assets is prohibited by default. You can add internal assets with the [multipart
API](#multipart-API) or allow them with query parameter *isAllowExternalResources*.

If your instance is exposed publicly, I recommend using a reverse proxy to terminate TLS connections
and require authentication. You could use HTTP Basic Auth and then pass the pdf-service URL to your
client software via an environment variable. This way auth information can be embedded like this:
`https://API_USER:API_TOKEN@pdf.example.com/generate`, where `API_USER` and `API_TOKEN` are the
credentials you set up in the reverse proxy.

Alternatively you can pass environment variables *BASIC_AUTH_USERNAME* and *BASIC_AUTH_PASSWORD* for built-in basic auth.

### Environment variables

- `WORKER_COUNT` (default: 4) Sets the worker pool size of the gunicorn server executing pdf_service.

- `HOST` if the hostname isn't set on the container, pass it as an environment variable to identify
    the service in Sentry.
  
- `SENTRY_DSN` Enable the Sentry integration and use this DSN to submit data.
- `SENTRY_TRACES_SAMPLE_RATE` (`0.0` ... `1.0`) If the Sentry integration is enabled this controls
  the tracing sample rate. It defaults to `1.0`. Set it to `0.0` to disable tracing.
- `SENTRY_ENVIRONMENT` This sets the environment sent to Sentry. Defaults to `development`.
- `SENTRY_RELEASE` This sets the release sent to Sentry. We set this to the current git SHA and you
  normally shouldn't need to overwrite it.
- `SENTRY_TAG_*` Set a tag to a specific value for all transactions.
  For example to set the tag `test` to `abc`, set the environment variable `SENTRY_TAG_TEST=abc`.
- `BASIC_AUTH_USERNAME` - username for basic auth.
- `BASIC_AUTH_PASSWORD` - password for basic auth.

### Health check

The service has a `/health` endpoint that will respond with a `200` status code if the service is
running. This endpoint is also configured as a docker [`HEALTHCHECK`][docker-healthcheck].

### Supported architectures

The docker image supports the `linux/amd64` (regular Intel and AMD 64bit processors on x86_64) and 
`linux/arm64` (Apple Silicon, AWS Graviton, etc.) architectures.
Image sizes and other information that varies between architectures is taken from the `linux/amd64`
variant.

If you need a different architecture, please open an issue with your use-case.

Native Windows docker images are not supported. The linux image can be run on Windows using Docker
Desktop.

## Development

### Setup the development environment

- If you running windows - install GTK3 runtime: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases (dont' forget to logoff/login after install)
- Setup python venv `python -m venv venv/`
- `pip install -r requirements.txt -r requirements-dev.txt` (or: `pip install -e '.[dev]'`)
- Install docker and docker-compose to run tests. 
  Tests run in docker to ensure render output doesn't differ based on platform.
  
### Running

- Run the development server with `python -m pdf_service`
- Run tests with `./test` or `./test-watch`
  - Tests are executed within docker, to ensure render results are identical to the containerized
    version. The image contains external dependencies, but code and test files will be mounted from
    the project source. If you want to rebuild the dev image add `--build` to the end of the
    command. This will instruct `docker-compose` to rebuild the image.

### Visual tests with reference images

`e2e/data` contains reference inputs `*.html` and corresponding output `.png`.
The e2e test will render the html files and compare the output with the reference images to ensure 
no changes slipped in.

To update reference images or add new test cases run `./regenerate-e2e-references`.

[weasyprint]: https://weasyprint.org
[semver]: https://semver.org
[container-os-article-1]: https://opensource.com/article/18/1/containers-gpl-and-copyleft
[stackoverflow-aGPL-modified]: https://softwareengineering.stackexchange.com/questions/107883/agpl-what-you-can-do-and-what-you-cant#comment202259_107931
[docker-healthcheck]: https://docs.docker.com/engine/reference/builder/#healthcheck
