import base64
import os

# === Roboto-Regular (Base64) ===
regular_b64 = """
AAEAAAASAQAABAAgR0RFRrRCsIIAAjWsAAACYkdQT1O4uWnkAAI3PAAAOG5HU1VCnTtS1gA...
... (recortado para ejemplo)
"""

# === Roboto-Bold (Base64) ===
bold_b64 = """
AAEAAAASAQAABAAgR0RFRrRCsIIAAjWsAAACZkdQT1O4uWnkAAI3PAAAOG5HU1VCnTtS1gA...
... (recortado para ejemplo)
"""

def write_font(path, b64data):
    raw = base64.b64decode(b64data.encode())
    with open(path, "wb") as f:
        f.write(raw)

os.makedirs("fonts", exist_ok=True)
write_font("fonts/Roboto-Regular.ttf", regular_b64)
write_font("fonts/Roboto-Bold.ttf", bold_b64)

print("Fuentes generadas correctamente.")