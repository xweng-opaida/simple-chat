import logging
from PIL import Image


max_width = 1400
max_height = 2000
min_width = 500
min_height = 600

def resize_if_needed(img):
    width, height = img.size
    if width > max_width or height > max_height:
        logging.info(f"Resizing large image: {width}x{height}")
        aspect_ratio = width / height
        if (width / max_width) > (height / max_height):
            new_width = max_width
            new_height = int(max_width / aspect_ratio)
        else:
            new_height = max_height
            new_width = int(max_height * aspect_ratio)
        img = img.resize((new_width, new_height), Image.LANCZOS)
    elif width < min_width or height < min_height:
        logging.info(f"Upscaling small image: {width}x{height}")
        aspect_ratio = width / height
        if (width / min_width) < (height / min_height):
            new_width = min_width
            new_height = int(min_width / aspect_ratio)
        else:
            new_height = min_height
            new_width = int(min_height * aspect_ratio)
        img = img.resize((new_width, new_height), Image.LANCZOS)
    return img