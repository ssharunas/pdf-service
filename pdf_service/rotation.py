from io import BytesIO

import pypdf

def rotate_pdf(data: bytes, rotation: int) -> bytes:
    reader = pypdf.PdfReader(BytesIO(data))
    writer = pypdf.PdfWriter(reader)
    
    for page in reader.pages:
        page.rotation = rotation
        writer.add_page(page)
    
    with BytesIO() as output:
        writer.write(output)
        output.seek(0)
        return output.read()
    