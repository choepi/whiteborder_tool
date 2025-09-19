import os, math
from PIL import Image, ImageDraw, ImageFont
import exifread
from fractions import Fraction

# ===== TUNABLES =====
BOX_W_FRAC = 0.16
BOX_H_FRAC = 0.18
PADDING_RATIO = 0.06

MIN_FONT_PX = 20
MAX_FONT_PX = 30
LOCK_FONT_PX = 24
STRICT_LOCK = True

LINE_GAP_RATIO = 0.12
MIN_LINE_GAP_PX = 1
OVERLAY_ALPHA = 255
DEBUG = True

TEXT_COLOR = (0, 0, 0)
TREAT_SLASH_N_AS_NEWLINE = True  # turns 'n/' into newline (without touching '1/250s')
OUTPUT_SIDE = 2160  # pick 1080 or 2160; must be same for all outputs

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
            S_raw = max(w, h)

            # normalize to fixed output side
            S = OUTPUT_SIDE  # use this S for ALL subsequent math
            scale = S / float(S_raw)
            nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))

            img_resized = img.resize((nw, nh), Image.LANCZOS)

            # square canvas + center (normalized space)
            square = Image.new("RGB", (S, S), (255, 255, 255))
            px, py = (S - nw) // 2, (S - nh) // 2
            square.paste(img_resized, (px, py))

            # white borders
            b_left = px
            b_bottom = S - (py + h)

            # target box dims
            tgt_w = max(1, int(round(S * BOX_W_FRAC)))
            tgt_h = max(1, int(round(S * BOX_H_FRAC)))

            # metadata text (with hard newlines)
            meta = extract_metadata(fp)
            text = normalize_newlines(format_metadata(meta))

            # locked font
            base_px = (
                clamp(int(LOCK_FONT_PX), MIN_FONT_PX, MAX_FONT_PX)
                if LOCK_FONT_PX
                else MIN_FONT_PX
            )
            font = ImageFont.truetype(font_path, base_px)

            # find a bottom-left rect that fits THIS font by stretching along free axis
            rect, mode = choose_rect_strict(
                text, font, S, b_left, b_bottom, tgt_w, tgt_h, PADDING_RATIO
            )

            draw = ImageDraw.Draw(square)
            if mode == "overlay":
                draw_overlay_rect(square, rect, OVERLAY_ALPHA)
                draw = ImageDraw.Draw(square)

            # final inner box with SAME padding math
            x0, y0, x1, y1 = rect
            box_w, box_h = x1 - x0, y1 - y0
            pad_x = max(4, int(round(box_w * PADDING_RATIO)))
            pad_y = max(4, int(round(box_h * PADDING_RATIO)))
            inner = (x0 + pad_x, y0 + pad_y, x1 - pad_x, y1 - pad_y)
            inner_w = max(1, inner[2] - inner[0])
            inner_h = max(1, inner[3] - inner[1])

            # layout with uniform line height
            lines = wrap_text_preserve_newlines(text, font, inner_w)
            lh = uniform_line_height(font)
            total_h = lh * len(lines)
            if DEBUG:
                print(
                    f"\n[{fn}] mode={mode} S={S} bL={b_left} bB={b_bottom} "
                    f"rect=({x0},{y0},{x1},{y1}) box=({box_w}x{box_h}) "
                    f"inner=({inner_w}x{inner_h}) font={font.size} lines={len(lines)}"
                )
            if total_h > inner_h:
                if STRICT_LOCK:
                    # if somehow still overflowing (should be rare), expand overlay taller to keep font
                    if mode != "overlay":
                        # switch to overlay sized to fit
                        need_h = total_h + 2 * max(
                            4, int(round((total_h + 2) * PADDING_RATIO))
                        )
                        need_h = min(S, int(math.ceil(need_h)))
                        rect = (0, S - need_h, max(tgt_w, box_w), S)
                        draw_overlay_rect(square, rect, OVERLAY_ALPHA)
                        draw = ImageDraw.Draw(square)
                        # recompute inner
                        x0, y0, x1, y1 = rect
                        box_w, box_h = x1 - x0, y1 - y0
                        pad_x = max(4, int(round(box_w * PADDING_RATIO)))
                        pad_y = max(4, int(round(box_h * PADDING_RATIO)))
                        inner = (x0 + pad_x, y0 + pad_y, x1 - pad_x, y1 - pad_y)
                        inner_w = max(1, inner[2] - inner[0])
                        inner_h = max(1, inner[3] - inner[1])
                        lines = wrap_text_preserve_newlines(text, font, inner_w)
                        lh = uniform_line_height(font)
                        total_h = lh * len(lines)
                else:
                    # softly step down, but only if not strict
                    while total_h > inner_h and font.size > MIN_FONT_PX:
                        font = ImageFont.truetype(font_path, font.size - 1)
                        lines = wrap_text_preserve_newlines(text, font, inner_w)
                        lh = uniform_line_height(font)
                        total_h = lh * len(lines)

            # draw bottom-left inside inner
            start_x = inner[0]
            start_y = inner[3] - total_h
            y = start_y
            for ln in lines:
                draw.text((start_x, y), ln, fill=TEXT_COLOR, font=font)
                y += lh

            if DEBUG:
                print(
                    f"\n[{fn}] mode={mode} S={S} bL={b_left} bB={b_bottom} "
                    f"rect=({x0},{y0},{x1},{y1}) box=({box_w}x{box_h}) "
                    f"inner=({inner_w}x{inner_h}) font={font.size} lines={len(lines)}"
                )

            out = os.path.join(output_folder, f"{os.path.splitext(fn)[0]}_insta.jpg")
            square.save(out, quality=100, subsampling=0)
            print(f"Processed and saved: {out}")


# ===== FITTING GEOMETRY (strict, consistent padding) =====
def choose_rect_strict(text, font, S, b_left, b_bottom, tgt_w, tgt_h, pad_ratio):
    """
    Try LEFT-border mode (width <= b_left, grow height) and BOTTOM-border mode
    (height <= b_bottom, grow width) with EXACT same padding math used later.
    Pick the first that fits; prefer BOTTOM if both fit (usually cleaner). If neither border exists -> overlay.
    """
    candidates = []

    # LEFT mode: clamp width to min(tgt_w, b_left). grow height until text fits.
    if b_left > 0:
        w = min(tgt_w, b_left)
        rect = grow_height_to_fit_consistent(text, font, S, w, tgt_h, pad_ratio)
        if rect is not None:
            candidates.append(("left", rect))

    # BOTTOM mode: clamp height to min(tgt_h, b_bottom). grow width until text fits.
    if b_bottom > 0:
        h = min(tgt_h, b_bottom)
        rect = grow_width_to_fit_consistent(text, font, S, tgt_w, h, pad_ratio)
        if rect is not None:
            candidates.append(("bottom", rect))

    if not candidates:
        # no border: overlay sized minimally to fit at locked font
        rect = minimal_overlay_to_fit(text, font, S, tgt_w, tgt_h, pad_ratio)
        return rect, "overlay"

    # prefer bottom if both fit; else pick the one that fits
    if (
        len(candidates) == 2
        and candidates[0][0] != "bottom"
        and candidates[1][0] == "bottom"
    ):
        return candidates[1][1], "bottom"
    return candidates[0][1], candidates[0][0]


def grow_height_to_fit_consistent(text, font, S, box_w, min_h, pad_ratio):
    # padding uses final box size (consistent)
    # we increase box_h until inner_h >= total_h
    box_h = max(1, min_h)
    while True:
        pad_x = max(4, int(round(box_w * pad_ratio)))
        pad_y = max(4, int(round(box_h * pad_ratio)))
        inner_w = max(1, box_w - 2 * pad_x)
        inner_h = max(1, box_h - 2 * pad_y)
        lines = wrap_text_preserve_newlines(text, font, inner_w)
        total_h = uniform_line_height(font) * len(lines)
        if total_h <= inner_h:  # fits!
            break
        new_h = min(S, int(math.ceil(total_h + 2 * pad_y)))
        if new_h == box_h:  # cannot grow further
            return None
        box_h = new_h
        if box_h >= S:
            # one last pass with S
            pad_y = max(4, int(round(box_h * pad_ratio)))
            inner_h = max(1, box_h - 2 * pad_y)
            if total_h <= inner_h:
                break
            return None
    x0, y0 = 0, S - box_h
    return (x0, y0, x0 + box_w, y0 + box_h)


def grow_width_to_fit_consistent(text, font, S, min_w, box_h, pad_ratio):
    # binary search width until inner_w makes lines fit within fixed inner_h
    lo = max(1, min_w)
    hi = S
    ok = None
    while lo <= hi:
        mid = (lo + hi) // 2
        pad_x = max(4, int(round(mid * pad_ratio)))
        pad_y = max(4, int(round(box_h * pad_ratio)))
        inner_w = max(1, mid - 2 * pad_x)
        inner_h = max(1, box_h - 2 * pad_y)
        lines = wrap_text_preserve_newlines(text, font, inner_w)
        total_h = uniform_line_height(font) * len(lines)
        if total_h <= inner_h:
            ok = mid
            hi = mid - 1
        else:
            lo = mid + 1
    if ok is None:
        return None
    x0, y0 = 0, S - box_h
    return (x0, y0, x0 + ok, y0 + box_h)


def minimal_overlay_to_fit(text, font, S, tgt_w, tgt_h, pad_ratio):
    # prefer target height, grow width first; if still not, grow height
    rect = grow_width_to_fit_consistent(text, font, S, tgt_w, tgt_h, pad_ratio)
    if rect is not None:
        return rect
    return grow_height_to_fit_consistent(text, font, S, tgt_w, tgt_h, pad_ratio) or (
        0,
        S - tgt_h,
        S,
        S,
    )


# ===== TEXT LAYOUT =====
def normalize_newlines(text: str) -> str:
    t = text.replace("\r\n", "\n").replace("\r", "\n").replace("\\n", "\n")
    if TREAT_SLASH_N_AS_NEWLINE:
        t = t.replace(" n/ ", "\n").replace(" n/", "\n").replace("n/ ", "\n")
        if t.endswith("n/"):
            t = t[:-2] + "\n"
    return t


def wrap_text_preserve_newlines(text, font, max_w, max_lines=None):
    out, used = [], 0
    for para in text.split("\n"):
        if max_lines and used >= max_lines:
            break
        if para == "":
            out.append("")
            used += 1
            continue
        words, cur = para.split(" "), ""
        for w in words:
            test = w if not cur else cur + " " + w
            width = font.getbbox(test)[2] - font.getbbox(test)[0]
            if width <= max_w:
                cur = test
            else:
                if cur:
                    out.append(cur)
                    used += 1
                    if max_lines and used >= max_lines:
                        cur = ""
                        break
                cur = w
        if cur and (not max_lines or used < max_lines):
            out.append(cur)
            used += 1
    return out


def uniform_line_height(font):
    ascent, descent = font.getmetrics()
    gap = max(MIN_LINE_GAP_PX, int(round(font.size * LINE_GAP_RATIO)))
    return ascent + descent + gap


# ===== EXIF + FORMAT =====
def extract_metadata(image_path):
    md = {}
    with open(image_path, "rb") as f:
        tags = exifread.process_file(f, stop_tag="UNDEF", details=False)
    make = str(tags.get("Image Make", "Unknown")).strip()
    model = str(tags.get("Image Model", "Unknown")).strip()
    md["Camera"] = f"{make} {model}".strip()
    iso = (
        tags.get("EXIF ISOSpeedRatings")
        or tags.get("EXIF PhotographicSensitivity")
        or "Unknown"
    )
    md["ISO"] = str(iso)
    ap = tags.get("EXIF FNumber")
    if ap:
        try:
            md["Aperture"] = f"ƒ/{round(float(Fraction(str(ap))), 1)}"
        except Exception:
            md["Aperture"] = "Unknown"
    else:
        md["Aperture"] = "Unknown"
    sh = tags.get("EXIF ExposureTime")
    if sh:
        try:
            val = float(Fraction(str(sh)))
            md["Shutter Speed"] = (
                f"{round(val,1)}s" if val >= 1 else f"1/{int(round(1/val))}s"
            )
        except Exception:
            md["Shutter Speed"] = f"{str(sh)}s"
    else:
        md["Shutter Speed"] = "Unknown"
    fl = tags.get("EXIF FocalLength")
    if fl:
        try:
            v = float(Fraction(str(fl)))
            md["Focal Length"] = (
                f"{int(round(v))}mm" if abs(v - round(v)) < 0.1 else f"{round(v,1)}mm"
            )
        except Exception:
            md["Focal Length"] = "Unknown"
    else:
        md["Focal Length"] = "Unknown"
    return md


def format_metadata(md):
    return (
        f"Camera: {md['Camera']}\n"
        f"ISO: {md['ISO']}\n"
        f"Aperture: {md['Aperture']}\n"
        f"Shutter Speed: {md['Shutter Speed']}\n"
        f"Focal Length: {md['Focal Length']}"
    )


# ===== utils =====
def clamp(v, lo, hi):
    return max(lo, min(v, hi))


def draw_overlay_rect(img, rect, alpha):
    if img.mode != "RGBA":
        base = img.convert("RGBA")
    else:
        base = img.copy()
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle(rect, fill=(255, 255, 255, alpha))
    composed = Image.alpha_composite(base, overlay).convert("RGB")
    img.paste(composed)


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
