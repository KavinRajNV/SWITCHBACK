import os
from pathlib import Path
from PIL import Image, ImageOps

ROOT_DIR = Path(__file__).resolve().parent
ASSETS_SRC = ROOT_DIR / "Assets"
ASSETS_DEST = ROOT_DIR / "frontend" / "src" / "assets"
ASSETS_DEST.mkdir(parents=True, exist_ok=True)

def optimize_images():
    print("======================================================================")
    print("ASSET OPTIMIZATION: CONVERTING PNGs TO WEBP & UNIFORM SQUARES")
    print("======================================================================")

    converted_stats = []

    for file_path in ASSETS_SRC.glob("*.png"):
        filename = file_path.name
        src_size_kb = file_path.stat().st_size / 1024.0

        with Image.open(file_path) as img:
            # 1. Square difficulty marks cropping/padding
            if filename in ["green circle.png", "blue square.png", "black sqare.png"]:
                # Create uniform 128x128 canvas
                img_rgba = img.convert("RGBA")
                
                # Fit image maintaining aspect ratio into 128x128 canvas
                img_rgba.thumbnail((110, 110), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
                
                # Center paste
                offset = ((128 - img_rgba.width) // 2, (128 - img_rgba.height) // 2)
                canvas.paste(img_rgba, offset, img_rgba)

                clean_name = filename.replace(" ", "_").replace(".png", ".webp")
                dest_path = ASSETS_DEST / clean_name
                canvas.save(dest_path, "WEBP", quality=90)
                dest_size_kb = dest_path.stat().st_size / 1024.0
                converted_stats.append((filename, src_size_kb, dest_size_kb))
                print(f"  [Square Mark] {filename:<40} ({src_size_kb:.1f} KB -> {dest_size_kb:.1f} KB)")
                continue

            # 2. General WebP conversion & resize for heavy backgrounds
            clean_name = filename.replace(" ", "_").replace(".png", ".webp")
            dest_path = ASSETS_DEST / clean_name

            # Also keep original PNG name formatted cleanly for fallbacks
            clean_png_name = filename.replace(" ", "_")
            dest_png_path = ASSETS_DEST / clean_png_name

            img_rgba = img.convert("RGBA")
            
            # Resize giant 3000px backgrounds if width > 1920
            if img_rgba.width > 1920:
                new_h = int(img_rgba.height * (1920 / img_rgba.width))
                img_rgba = img_rgba.resize((1920, new_h), Image.Resampling.LANCZOS)

            img_rgba.save(dest_path, "WEBP", quality=82)
            dest_size_kb = dest_path.stat().st_size / 1024.0

            converted_stats.append((filename, src_size_kb, dest_size_kb))
            print(f"  [WebP] {filename:<45} ({src_size_kb:.1f} KB -> {dest_size_kb:.1f} KB)")

    print("======================================================================")
    print("TOP 5 HEAVIEST BEFORE/AFTER OPTIMIZATION RESULTS:")
    converted_stats.sort(key=lambda x: x[1], reverse=True)
    for rank, (name, src_k, dst_k) in enumerate(converted_stats[:5], 1):
        reduction = (1.0 - (dst_k / src_k)) * 100.0
        print(f"  {rank}. {name:<42} : {src_k:.1f} KB -> {dst_k:.1f} KB ({reduction:.1f}% reduction)")
    print("======================================================================")

if __name__ == "__main__":
    optimize_images()
