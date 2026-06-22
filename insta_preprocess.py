import os
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# ===== TUNABLES =====
OUTPUT_SIDE = 2160  # pick 1080 or 2160; must be same for all outputs

EDGE_PADDING_FRAC = 0.025
TEXT_LOGO_GAP_FRAC = 0.035
LANDSCAPE_BRAND_REGION_FRAC = 0.32
MIN_METADATA_BORDER_PX = 96

MIN_FONT_PX = 14
MAX_FONT_PX = 28

LINE_GAP_RATIO = 0.12
MIN_LINE_GAP_PX = 1
TEXT_COLOR = (0, 0, 0)
TREAT_SLASH_N_AS_NEWLINE = True  # turns 'n/' into newline (without touching '1/250s')
DEBUG = True

BRAND_MARK_DIR = Path("insta") / "brand_marks"
BRAND_MARK_CANVAS = (600, 180)
SUPPORTED_BRANDS = {
    "canon": ("CANON", ("canon", "eos")),
    "nikon": ("NIKON", ("nikon", "nikkor")),
    "sony": ("SONY", ("sony", "ilce", "dslr-a", "zv-")),
    "fujifilm": ("FUJIFILM", ("fujifilm", "fuji", "x-t", "x-pro", "x100", "gfx")),
    "samsung": ("SAMSUNG", ("samsung", "galaxy")),
}

try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE_LANCZOS = Image.LANCZOS


# ===== CORE =====
def make_square_and_add_metadata(folder_path, output_folder, font_path, DEBUG=DEBUG):
    os.makedirs(output_folder, exist_ok=True)

    files = [
        f
        for f in os.listdir(folder_path)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    print(f"Total files to process: {len(files)}")

    for i, fn in enumerate(files, 1):
        print(f"Processing file {i}/{len(files)}", end="\r")
        fp = os.path.join(folder_path, fn)

        with Image.open(fp) as img:
            img = img.convert("RGB")
            w, h = img.size
            image_rect = fit_image_rect(w, h, OUTPUT_SIDE)

            square = Image.new("RGB", (OUTPUT_SIDE, OUTPUT_SIDE), (255, 255, 255))
            resized = img.resize(
                (image_rect[2] - image_rect[0], image_rect[3] - image_rect[1]),
                RESAMPLE_LANCZOS,
            )
            square.paste(resized, image_rect[:2])

            meta = extract_metadata(fp)
            text = normalize_newlines(format_metadata(meta))
            brand = resolve_brand(meta.get("Make"), meta.get("Model"))
            layout = layout_metadata(
                text,
                font_path,
                OUTPUT_SIDE,
                image_rect,
                bool(brand),
            )

            draw = ImageDraw.Draw(square)
            if layout:
                draw_text_bottom_left(
                    draw,
                    layout["text_rect"],
                    layout["lines"],
                    layout["font"],
                    layout["line_h"],
                )
                if brand and layout["brand_rect"]:
                    draw_brand_mark(square, brand, layout["brand_rect"])

            if DEBUG:
                placement = layout["placement"] if layout else "none"
                text_rect = layout["text_rect"] if layout else None
                brand_rect = layout["brand_rect"] if layout else None
                font_size = getattr(layout["font"], "size", None) if layout else None
                line_count = len(layout["lines"]) if layout else 0
                print(
                    f"\n[{fn}] S={OUTPUT_SIDE} placement={placement} "
                    f"image={image_rect} text={text_rect} brand={brand}:{brand_rect} "
                    f"font={font_size} lines={line_count}"
                )

            out = os.path.join(output_folder, f"{os.path.splitext(fn)[0]}_insta.jpg")
            square.save(out, quality=100, subsampling=0)
            print(f"Processed and saved: {out}")


# ===== GEOMETRY =====
def fit_image_rect(width, height, side):
    """
    Fit the source image into the square canvas without adding extra metadata
    space. The only white areas are the natural borders created by making the
    image square.
    """
    if width <= 0 or height <= 0:
        raise ValueError("image dimensions must be positive")

    scale = side / float(max(width, height))
    new_w = max(1, int(round(width * scale)))
    new_h = max(1, int(round(height * scale)))
    x0 = (side - new_w) // 2
    y0 = (side - new_h) // 2
    return (x0, y0, x0 + new_w, y0 + new_h)


def natural_border_regions(side, image_rect, include_brand):
    x0, y0, x1, y1 = image_rect
    left_w = x0
    right_w = side - x1
    top_h = y0
    bottom_h = side - y1
    pad = max(10, int(round(side * EDGE_PADDING_FRAC)))
    gap = max(12, int(round(side * TEXT_LOGO_GAP_FRAC)))

    if left_w >= MIN_METADATA_BORDER_PX and right_w >= MIN_METADATA_BORDER_PX:
        text_rect = inset_rect((0, 0, x0, side), pad)
        brand_rect = inset_rect((x1, 0, side, side), pad) if include_brand else None
        return {
            "placement": "vertical-side-borders",
            "text_rect": text_rect,
            "brand_container": brand_rect,
        }

    if bottom_h >= MIN_METADATA_BORDER_PX:
        bottom_rect = (0, y1, side, side)
        inner = inset_rect(bottom_rect, pad)
        if include_brand:
            brand_w = max(1, int(round(side * LANDSCAPE_BRAND_REGION_FRAC)))
            brand_left = max(inner[0] + 1, inner[2] - brand_w)
            text_right = max(inner[0] + 1, brand_left - gap)
            brand_rect = (brand_left, inner[1], inner[2], inner[3])
            text_rect = (inner[0], inner[1], text_right, inner[3])
        else:
            brand_rect = None
            text_rect = inner
        return {
            "placement": "horizontal-bottom-border",
            "text_rect": text_rect,
            "brand_container": brand_rect,
        }

    return None


def inset_rect(rect, pad):
    x0, y0, x1, y1 = rect
    width = x1 - x0
    height = y1 - y0
    safe_pad = min(pad, max(0, (width - 1) // 2), max(0, (height - 1) // 2))
    return (x0 + safe_pad, y0 + safe_pad, x1 - safe_pad, y1 - safe_pad)


# ===== TEXT LAYOUT =====
def layout_metadata(text, font_path, side, image_rect, include_brand):
    regions = natural_border_regions(side, image_rect, include_brand)
    if not regions:
        return None

    font, lines, line_h = fit_text(text, font_path, regions["text_rect"])
    text_block_h = line_h * len(lines)
    brand_rect = None
    if include_brand and regions["brand_container"]:
        brand_rect = fit_brand_rect(regions["brand_container"], text_block_h)

    return {
        "placement": regions["placement"],
        "text_rect": regions["text_rect"],
        "brand_rect": brand_rect,
        "font": font,
        "lines": lines,
        "line_h": line_h,
    }


def fit_text(text, font_path, rect):
    inner_w = max(1, rect[2] - rect[0])
    inner_h = max(1, rect[3] - rect[1])
    raw_lines = text.split("\n")

    for size in range(MAX_FONT_PX, MIN_FONT_PX - 1, -1):
        font = load_font(font_path, size)
        line_h = uniform_line_height(font)
        if (
            line_h * len(raw_lines) <= inner_h
            and all(text_width(font, line) <= inner_w for line in raw_lines)
        ):
            return font, raw_lines, line_h

    for size in range(MAX_FONT_PX, MIN_FONT_PX - 1, -1):
        font = load_font(font_path, size)
        lines = wrap_text_preserve_newlines(text, font, inner_w)
        line_h = uniform_line_height(font)
        if line_h * len(lines) <= inner_h:
            return font, lines, line_h

    font = load_font(font_path, MIN_FONT_PX)
    line_h = uniform_line_height(font)
    max_lines = max(1, inner_h // line_h)
    lines = wrap_text_preserve_newlines(text, font, inner_w, max_lines=max_lines)
    return font, lines, line_h


def fit_brand_rect(container, target_h):
    x0, y0, x1, y1 = container
    max_w = max(1, x1 - x0)
    max_h = max(1, min(y1 - y0, target_h))
    aspect = BRAND_MARK_CANVAS[0] / float(BRAND_MARK_CANVAS[1])

    if max_w / float(max_h) < aspect:
        mark_w = max_w
        mark_h = max(1, int(round(mark_w / aspect)))
    else:
        mark_h = max_h
        mark_w = max(1, int(round(mark_h * aspect)))

    return (x1 - mark_w, y1 - mark_h, x1, y1)


def draw_text_bottom_left(draw, rect, lines, font, line_h):
    total_h = line_h * len(lines)
    x = rect[0]
    y = rect[3] - total_h
    for line in lines:
        draw.text((x, y), line, fill=TEXT_COLOR, font=font)
        y += line_h


def normalize_newlines(text: str) -> str:
    t = text.replace("\r\n", "\n").replace("\r", "\n").replace("\\n", "\n")
    if TREAT_SLASH_N_AS_NEWLINE:
        t = t.replace(" n/ ", "\n").replace(" n/", "\n").replace("n/ ", "\n")
        if t.endswith("n/"):
            t = t[:-2] + "\n"
    return t


def wrap_text_preserve_newlines(text, font, max_w, max_lines=None):
    out = []
    for para in text.split("\n"):
        if max_lines and len(out) >= max_lines:
            break
        if para == "":
            out.append("")
            continue

        cur = ""
        for word in para.split(" "):
            pieces = split_token_to_width(word, font, max_w)
            for piece in pieces:
                candidate = piece if not cur else f"{cur} {piece}"
                if text_width(font, candidate) <= max_w:
                    cur = candidate
                    continue

                if cur:
                    out.append(cur)
                    if max_lines and len(out) >= max_lines:
                        return out
                cur = piece

        if cur:
            out.append(cur)

    return out[:max_lines] if max_lines else out


def split_token_to_width(token, font, max_w):
    if text_width(font, token) <= max_w:
        return [token]

    chunks = []
    cur = ""
    for char in token:
        candidate = cur + char
        if cur and text_width(font, candidate) > max_w:
            chunks.append(cur)
            cur = char
        else:
            cur = candidate
    if cur:
        chunks.append(cur)
    return chunks


def text_width(font, text):
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0]


def uniform_line_height(font):
    try:
        ascent, descent = font.getmetrics()
        size = font.size
    except AttributeError:
        bbox = font.getbbox("Ag")
        ascent, descent = bbox[3] - bbox[1], 0
        size = max(1, ascent)
    gap = max(MIN_LINE_GAP_PX, int(round(size * LINE_GAP_RATIO)))
    return ascent + descent + gap


def load_font(font_path, size):
    try:
        return ImageFont.truetype(font_path, size)
    except OSError:
        return ImageFont.load_default()


# ===== BRAND MARKS =====
def draw_brand_mark(square, brand, rect, asset_dir=BRAND_MARK_DIR):
    mark = load_brand_mark(brand, asset_dir)
    mark = mark.resize((rect[2] - rect[0], rect[3] - rect[1]), RESAMPLE_LANCZOS)
    square.paste(mark, rect[:2], mark)


def load_brand_mark(brand, asset_dir=BRAND_MARK_DIR):
    path = Path(asset_dir) / f"{brand}.png"
    if not path.exists():
        raise FileNotFoundError(f"Missing brand mark asset: {path}")
    return Image.open(path).convert("RGBA")


def resolve_brand(make, model):
    haystack = f"{make or ''} {model or ''}".lower()
    for brand, (_, needles) in SUPPORTED_BRANDS.items():
        if any(needle in haystack for needle in needles):
            return brand
    return None


# ===== EXIF + FORMAT =====
def unknown_metadata():
    return {
        "Make": "Unknown",
        "Model": "Unknown",
        "ISO": "Unknown",
        "Aperture": "Unknown",
        "Shutter Speed": "Unknown",
        "Focal Length": "Unknown",
    }


def extract_metadata(image_path):
    try:
        import exifread
    except ModuleNotFoundError:
        return extract_metadata_with_pillow(image_path)

    try:
        with open(image_path, "rb") as f:
            tags = exifread.process_file(f, stop_tag="UNDEF", details=False)
        return metadata_from_exifread_tags(tags)
    except Exception:
        return extract_metadata_with_pillow(image_path)


def metadata_from_exifread_tags(tags):
    md = unknown_metadata()
    md["Make"] = clean_metadata_value(tags.get("Image Make"))
    md["Model"] = clean_metadata_value(tags.get("Image Model"))

    iso = (
        tags.get("EXIF ISOSpeedRatings")
        or tags.get("EXIF PhotographicSensitivity")
        or "Unknown"
    )
    md["ISO"] = clean_metadata_value(iso)

    aperture = tags.get("EXIF FNumber")
    if aperture:
        md["Aperture"] = format_aperture(aperture)

    shutter = tags.get("EXIF ExposureTime")
    if shutter:
        md["Shutter Speed"] = format_shutter_speed(shutter)

    focal_length = tags.get("EXIF FocalLength")
    if focal_length:
        md["Focal Length"] = format_focal_length(focal_length)

    return md


def extract_metadata_with_pillow(image_path):
    with Image.open(image_path) as img:
        return metadata_from_pillow_exif(img.getexif())


def metadata_from_pillow_exif(exif):
    md = unknown_metadata()
    md["Make"] = clean_metadata_value(pillow_exif_value(exif, 271))
    md["Model"] = clean_metadata_value(pillow_exif_value(exif, 272))
    md["ISO"] = clean_metadata_value(pillow_exif_value(exif, 34855))
    md["Aperture"] = format_aperture(pillow_exif_value(exif, 33437))
    md["Shutter Speed"] = format_shutter_speed(pillow_exif_value(exif, 33434))
    md["Focal Length"] = format_focal_length(pillow_exif_value(exif, 37386))
    return md


def pillow_exif_value(exif, tag):
    value = exif.get(tag)
    if value is not None:
        return value

    get_ifd = getattr(exif, "get_ifd", None)
    if not get_ifd:
        return None

    try:
        return get_ifd(34665).get(tag)
    except Exception:
        return None


def clean_metadata_value(value):
    if value is None:
        return "Unknown"
    text = str(value).strip()
    return text if text else "Unknown"


def rational_float(value):
    if value is None:
        raise ValueError("missing value")
    if isinstance(value, tuple) and len(value) == 2:
        return float(value[0]) / float(value[1])
    try:
        return float(Fraction(str(value)))
    except Exception:
        return float(value)


def format_aperture(value):
    try:
        return f"f/{round(rational_float(value), 1)}"
    except Exception:
        return "Unknown"


def format_shutter_speed(value):
    try:
        val = rational_float(value)
        if val <= 0:
            return "Unknown"
        return f"{round(val, 1)}s" if val >= 1 else f"1/{int(round(1 / val))}s"
    except Exception:
        text = clean_metadata_value(value)
        return "Unknown" if text == "Unknown" else f"{text}s"


def format_focal_length(value):
    try:
        val = rational_float(value)
        return f"{int(round(val))}mm" if abs(val - round(val)) < 0.1 else f"{round(val, 1)}mm"
    except Exception:
        return "Unknown"


def format_metadata(md):
    return (
        f"Model: {md.get('Model', 'Unknown')}\n"
        f"ISO: {md.get('ISO', 'Unknown')}\n"
        f"Aperture: {md.get('Aperture', 'Unknown')}\n"
        f"Shutter Speed: {md.get('Shutter Speed', 'Unknown')}\n"
        f"Focal Length: {md.get('Focal Length', 'Unknown')}"
    )


# ===== utils =====
def clamp(v, lo, hi):
    return max(lo, min(v, hi))


# ===== CLI =====
if __name__ == "__main__":
    input_folder = "./insta/01_pre"
    output_folder = "./insta/02_post"
    font_file = "./insta/font/07558_CenturyGothic.ttf"
    os.makedirs(output_folder, exist_ok=True)
    for fn in os.listdir(output_folder):
        fp = os.path.join(output_folder, fn)
        if os.path.isfile(fp):
            os.remove(fp)
    make_square_and_add_metadata(input_folder, output_folder, font_file)
