max_width = 1400
max_height = 2000
top_width = 4000
top_height = 4000
min_width = 500
min_height = 600
def resize_image(images):
    resized_images = []
    for image in images:
        width, height = image.size  # get the first frame's width and height
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="PNG")
        if width > top_width or height > top_height:  # if tiff is super large, convert it to much smaller pdf
            pdf_bytes = image_to_pdf_bytes(image_bytes, resolution=500.0)  # make it a lot smaller size
        elif width > max_width or height > max_height:  # if tiff is too large, convert it to small pdf
            pdf_bytes = image_to_pdf_bytes(image_bytes, resolution=300.0)  # make it smaller size
        elif width < min_width or height < min_height:  # if tiff is too small, convert it to larger pdf
            pdf_bytes = image_to_pdf_bytes(image_bytes, resolution=100.0)  # make it larger size
        else:  # if tiff is small enough, then directly use tiff
            pdf_bytes = image_to_pdf_bytes(image_bytes, resolution=50.0)  # make it same size
        # convert one image each time
        resized_image = convert_from_bytes(pdf_bytes)[0]
        resized_images.append(resized_image)
    return resized_images

def image_to_pdf_bytes(image_file, resolution=300.0):
    """Converts an image including multi-page TIFF to a PDF and returns the PDF as bytes."""
    img = Image.open(image_file)
    images = []
    try:
        # tiff or png
        for i in range(img.n_frames):
            img.seek(i)
            images.append(img.convert('RGB'))
    except Exception as e:
        # jpg or other imgages
        images.append(img.convert('RGB'))
    # save all pages to the pdf.
    # resolution=100 keep original image size
    # resolution=200.0 has 1/3*1/3 image size (smaller image)
    # resolution=400.0 has 1/4 * 1/4 image size (smaller image)
    # resolution=50 has 2 times larger image size
    pdf_bytes = io.BytesIO()
    images[0].save(pdf_bytes, "PDF", resolution=resolution, save_all=True, append_images=images[1:])
    pdf_bytes.seek(0) # Reset the stream position to the beginning.
    return pdf_bytes.getvalue()