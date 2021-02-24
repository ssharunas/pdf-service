import fire
from pdf2image import convert_from_bytes
from weasyprint import HTML
from pathlib import Path


def create(name):
    """
    Creates a new reference image from an html file.
    Place the html file into the test-data folder.

    :param name: name of the test case without the file extension
    :return:
    """

    base = Path(__file__).parent.joinpath("test-data")
    pdf_file = base.joinpath(name + ".pdf").absolute()

    html = HTML(filename=base.joinpath(name + ".html").absolute())
    doc = html.render()

    pdf = doc.write_pdf()
    with open(pdf_file, mode="wb") as f:
        f.write(pdf)

    convert_from_bytes(pdf,
                       output_file=name + "_",
                       output_folder=base.absolute(),
                       fmt="png",
                       paths_only=True)


if __name__ == "__main__":
    fire.Fire({
        "create": create
    })
