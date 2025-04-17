# QR code utilities

import io
import qrcode
from flask import send_file

def generate_qr_code(data, size=200):
    """
    Generate a QR code image from the provided data

    Args:
        data (str): The data to encode in the QR code
        size (int): The size of the QR code in pixels

    Returns:
        BytesIO: An in-memory file-like object containing the QR code image
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Create QR image
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    return img_byte_arr
