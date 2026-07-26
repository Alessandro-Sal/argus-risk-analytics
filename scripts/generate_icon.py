"""
Script per generare l'icona ufficiale 'Occhio di Argus' (.ico) in alta risoluzione.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

def generate_argus_icon(output_path="docs/argus_icon.ico"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    cx, cy = size // 2, size // 2
    
    # 1. Sfondo scuro ottagonale/circolare ad alta tecnologia
    margin = 15
    draw.ellipse([margin, margin, size - margin, size - margin], fill=(10, 14, 23, 255), outline=(0, 245, 212, 255), width=10)
    
    margin_inner = 35
    draw.ellipse([margin_inner, margin_inner, size - margin_inner, size - margin_inner], fill=(15, 23, 42, 255), outline=(114, 9, 183, 180), width=6)
    
    # 2. Sagoma dell'Occhio di Argus (Forma a mandorla cibernetica)
    # Curva superiore dell'occhio
    eye_top = []
    eye_bottom = []
    w_eye = 190
    h_eye = 110
    
    for i in range(-w_eye, w_eye + 1):
        x = cx + i
        # Equazione parabola/curva liscia per palpebra superiore e inferiore
        normalized_x = i / w_eye
        y_top = cy - int(h_eye * (1 - normalized_x**2))
        y_bottom = cy + int(h_eye * (1 - normalized_x**2))
        eye_top.append((x, y_top))
        eye_bottom.append((x, y_bottom))
        
    # Disegna il contorno sfumato dell'occhio
    draw.line(eye_top, fill=(0, 245, 212, 255), width=8)
    draw.line(eye_bottom, fill=(0, 245, 212, 255), width=8)
    
    # 3. Iride dell'Occhio (Cerchio concentrico con sfumature quantitative)
    r_iris = 85
    draw.ellipse([cx - r_iris, cy - r_iris, cx + r_iris, cy + r_iris], fill=(72, 149, 239, 255), outline=(0, 245, 212, 255), width=6)
    
    # Raggi radiali dell'iride
    num_rays = 24
    for r in range(num_rays):
        angle = (2 * math.pi / num_rays) * r
        rx1 = cx + int(35 * math.cos(angle))
        ry1 = cy + int(35 * math.sin(angle))
        rx2 = cx + int((r_iris - 5) * math.cos(angle))
        ry2 = cy + int((r_iris - 5) * math.sin(angle))
        draw.line([(rx1, ry1), (rx2, ry2)], fill=(0, 245, 212, 150), width=3)

    # 4. Pupilla centrale cibernetica con grafico a barre/candele integrato
    r_pupil = 35
    draw.ellipse([cx - r_pupil, cy - r_pupil, cx + r_pupil, cy + r_pupil], fill=(10, 14, 23, 255), outline=(247, 37, 133, 255), width=5)
    
    # Candela di trading dentro la pupilla (Verde/Ciano)
    draw.rectangle([cx - 8, cy - 18, cx + 8, cy + 18], fill=(0, 245, 212, 255))
    draw.line([(cx, cy - 25), (cx, cy + 25)], fill=(0, 245, 212, 255), width=3)
    
    # 5. Riflesso di luce (Specularity Glare)
    draw.ellipse([cx - 50, cy - 50, cx - 25, cy - 25], fill=(255, 255, 255, 220))
    draw.ellipse([cx + 20, cy + 25, cx + 32, cy + 37], fill=(255, 255, 255, 180))

    # 6. Scritta 'ARGUS' elegante in basso
    try:
        font = ImageFont.truetype("arialbd.ttf", 44)
        text = "ARGUS"
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((size - w) // 2, size - 100), text, fill=(0, 245, 212, 255), font=font)
    except Exception:
        pass
        
    # Salvataggio ICO multi-risoluzione
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(output_path, format="ICO", sizes=icon_sizes)
    print(f"[OK] Icona Occhio di Argus generata con successo in: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    generate_argus_icon()
