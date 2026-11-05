import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

def create_mac_icon():
    base_dir = Path(__file__).resolve().parent
    iconset_dir = base_dir / "LocalWhisper.iconset"
    iconset_dir.mkdir(parents=True, exist_ok=True)

    logo_path = base_dir / "assets" / "logo.png"
    if not logo_path.exists():
        raise FileNotFoundError(f"Logo not found at {logo_path}")

    logo = Image.open(logo_path).convert("RGBA")

    # Master canvas size
    size = 1024
    margin = 100
    r = 185
    rect = [margin, margin, size - margin, size - margin]

    # 1. Drop Shadow for Squircle (Apple standard elevation)
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle([margin, margin + 22, size - margin, size - margin + 22], radius=r, fill=(0, 0, 0, 115))
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))

    # 2. Base Squircle with Deep Obsidian-Slate Gradient
    squircle = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(squircle)

    for y in range(margin, size - margin):
        factor = (y - margin) / (size - 2 * margin)
        # Deep space gradient from #12131C to #1D1F2D
        r_c = int(14 + factor * 14)
        g_c = int(16 + factor * 16)
        b_c = int(24 + factor * 22)
        draw.line([(margin, y), (size - margin, y)], fill=(r_c, g_c, b_c, 255))

    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(rect, radius=r, fill=255)

    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    base.paste(squircle, (0, 0), mask=mask)

    # 3. Ambient Mint-Emerald Glow behind Logo
    center_x = size // 2
    center_y = size // 2
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse([center_x - 260, center_y - 200, center_x + 260, center_y + 200], fill=(107, 231, 167, 85))
    glow = glow.filter(ImageFilter.GaussianBlur(55))
    glow_clipped = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_clipped.paste(glow, (0, 0), mask=mask)

    # 4. Glass Rim & Specular highlight
    rim = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rim_draw = ImageDraw.Draw(rim)
    rim_draw.rounded_rectangle(rect, radius=r, outline=(255, 255, 255, 45), width=3)
    rim_draw.rounded_rectangle([margin + 2, margin + 2, size - margin - 2, size - margin - 2], radius=r - 2, outline=(107, 231, 167, 65), width=2)
    # Top specular gleam
    rim_draw.line([(margin + 90, margin + 3), (size - margin - 90, margin + 3)], fill=(255, 255, 255, 140), width=4)

    # 5. Scale & Center Logo inside Squircle
    target_w = 660
    target_h = int(logo.height * (target_w / logo.width))
    logo_resized = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # Soft shadow behind the logo for physical depth
    logo_shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pos_x = (size - target_w) // 2
    pos_y = (size - target_h) // 2
    
    logo_alpha = logo_resized.split()[-1]
    black_logo = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 95))
    logo_shadow.paste(black_logo, (pos_x, pos_y + 12), mask=logo_alpha)
    logo_shadow = logo_shadow.filter(ImageFilter.GaussianBlur(16))
    logo_shadow_clipped = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    logo_shadow_clipped.paste(logo_shadow, (0, 0), mask=mask)

    logo_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    logo_layer.paste(logo_resized, (pos_x, pos_y), mask=logo_resized)

    # Composite all layers together
    final_icon = Image.alpha_composite(shadow, base)
    final_icon = Image.alpha_composite(final_icon, glow_clipped)
    final_icon = Image.alpha_composite(final_icon, rim)
    final_icon = Image.alpha_composite(final_icon, logo_shadow_clipped)
    final_icon = Image.alpha_composite(final_icon, logo_layer)

    # 6. Generate Apple standard icon sizes
    icon_sizes = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png")
    ]

    for px, name in icon_sizes:
        resized = final_icon.resize((px, px), Image.Resampling.LANCZOS)
        resized.save(iconset_dir / name)

    # 7. Compile into AppIcon.icns
    icns_path = base_dir / "AppIcon.icns"
    if icns_path.exists():
        icns_path.unlink()
    subprocess.run(["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)], check=True)
    print(f"[Icon Generator] Created {icns_path} successfully!")
    return icns_path

if __name__ == "__main__":
    create_mac_icon()
