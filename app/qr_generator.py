"""
qr_generator.py
Generates a QR code image for a batch. Scanning it opens the
customer-facing traceability page (GET /track/{batch_id}).

Requires: pip install qrcode[pil]
"""

import qrcode


def generate_qr_for_batch(batch_id: str, base_url: str = "http://127.0.0.1:8001",
                           output_path: str = None) -> str:
    """
    Generates a QR code encoding the URL to this batch's public
    traceability page. Returns the file path where the QR image was
    saved (PNG).

    In production, `base_url` should be your real deployed domain,
    e.g. "https://track.yourjasminebrand.com", and this QR would be
    printed directly on the product packaging.
    """
    url = f"{base_url}/track/{batch_id}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    if output_path is None:
        output_path = f"qr_{batch_id}.png"
    img.save(output_path)
    print(f"QR code saved to: {output_path}")
    print(f"Encodes URL: {url}")
    return output_path


if __name__ == "__main__":
    # Example: generate a QR for a sample batch.
    # Change this batch_id to match one you've already created via the API.
    generate_qr_for_batch("JAS-2026-001")