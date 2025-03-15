import qrcode
from PIL import Image

# URL to be encoded in the QR code
url = "http://127.0.0.1:8000/register/"

# Generate QR code
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4
)
qr.add_data(url)
qr.make(fit=True)

# Create an image from the QR Code instance
qr_image = qr.make_image(fill="black", back_color="white")

# ✅ Display the QR Code (for testing)
qr_image.show()

# ✅ (Optional) Save to file after confirming the output
save_path = "register_qr.png"
qr_image.save(save_path)

print(f"✅ QR Code generated and saved at '{save_path}'")
