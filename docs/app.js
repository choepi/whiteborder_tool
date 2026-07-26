/*
 * White Border Tool — client-side engine.
 * Ports the geometry/text-fit/brand-fit algorithm from whiteborder.py 1:1
 * (see ../tests/test_layout.py for the reference behaviour) onto <canvas>.
 * Everything runs locally in the browser — no image ever leaves the device.
 */
(() => {
  "use strict";

  // ── constants (mirrors whiteborder.py) ────────────────────────────────
  const EDGE_PADDING_FRAC = 0.025;
  const TEXT_LOGO_GAP_FRAC = 0.035;
  const LANDSCAPE_BRAND_REGION_FRAC = 0.32;
  const MIN_METADATA_BORDER_PX = 96;
  const MAX_BRAND_MARK_W_FRAC = 0.117;
  const MAX_BRAND_MARK_H_FRAC = 0.035;
  const MIN_FONT_PX = 14;
  const MAX_FONT_PX = 28;
  const LINE_GAP_RATIO = 0.12;
  const MIN_LINE_GAP_PX = 1;
  const BRAND_MARK_CANVAS = [600, 180];
  const FONT_FAMILY = "WBFont";

  const SUPPORTED_BRANDS = {
    apple: ["APPLE", ["apple", "iphone", "ipad"]],
    canon: ["CANON", ["canon", "eos"]],
    dji: ["DJI", ["dji", "mavic", "osmo", "phantom", "air 2", "mini 2"]],
    fujifilm: ["FUJIFILM", ["fujifilm", "fuji", "x-t", "x-pro", "x100", "gfx"]],
    google: ["GOOGLE", ["google", "pixel"]],
    gopro: ["GOPRO", ["gopro", "hero"]],
    hasselblad: ["HASSELBLAD", ["hasselblad"]],
    leica: ["LEICA", ["leica"]],
    nikon: ["NIKON", ["nikon", "nikkor"]],
    olympus: ["OLYMPUS", ["olympus", "om-system", "om system", "e-m", "omd"]],
    panasonic: ["PANASONIC", ["panasonic", "lumix", "dc-s", "dc-g", "dc-gh"]],
    ricoh: ["RICOH", ["ricoh", "pentax", "gr iii", "gr3"]],
    samsung: ["SAMSUNG", ["samsung", "galaxy"]],
    sony: ["SONY", ["sony", "ilce", "dslr-a", "zv-", "ilx"]],
  };

  // ── geometry ────────────────────────────────────────────────────────
  function fitImageRect(width, height, side) {
    const scale = side / Math.max(width, height);
    const newW = Math.max(1, Math.round(width * scale));
    const newH = Math.max(1, Math.round(height * scale));
    const x0 = Math.floor((side - newW) / 2);
    const y0 = Math.floor((side - newH) / 2);
    return [x0, y0, x0 + newW, y0 + newH];
  }

  function insetRect(rect, pad) {
    const [x0, y0, x1, y1] = rect;
    const w = x1 - x0;
    const h = y1 - y0;
    const safe = Math.min(pad, Math.max(0, Math.floor((w - 1) / 2)), Math.max(0, Math.floor((h - 1) / 2)));
    return [x0 + safe, y0 + safe, x1 - safe, y1 - safe];
  }

  function naturalBorderRegions(side, imageRect, includeBrand) {
    const [x0, y0, x1, y1] = imageRect;
    const leftW = x0;
    const rightW = side - x1;
    const bottomH = side - y1;
    const pad = Math.max(10, Math.round(side * EDGE_PADDING_FRAC));
    const gap = Math.max(12, Math.round(side * TEXT_LOGO_GAP_FRAC));

    if (leftW >= MIN_METADATA_BORDER_PX && rightW >= MIN_METADATA_BORDER_PX) {
      const textRect = insetRect([0, 0, x0, side], pad);
      const brandRect = includeBrand ? insetRect([x1, 0, side, side], pad) : null;
      return { placement: "vertical-side-borders", textRect, brandContainer: brandRect };
    }

    if (bottomH >= MIN_METADATA_BORDER_PX) {
      const inner = insetRect([0, y1, side, side], pad);
      let brandRect = null;
      let textRect = inner;
      if (includeBrand) {
        const brandW = Math.max(1, Math.round(side * LANDSCAPE_BRAND_REGION_FRAC));
        const brandLeft = Math.max(inner[0] + 1, inner[2] - brandW);
        const textRight = Math.max(inner[0] + 1, brandLeft - gap);
        brandRect = [brandLeft, inner[1], inner[2], inner[3]];
        textRect = [inner[0], inner[1], textRight, inner[3]];
      }
      return { placement: "horizontal-bottom-border", textRect, brandContainer: brandRect };
    }

    return null;
  }

  function fitBrandRect(container, targetH) {
    const [x0, y0, x1, y1] = container;
    const side = Math.max(x1, y1);
    const maxW = Math.max(1, Math.min(x1 - x0, Math.round(side * MAX_BRAND_MARK_W_FRAC)));
    const maxH = Math.max(1, Math.min(y1 - y0, targetH, Math.round(side * MAX_BRAND_MARK_H_FRAC)));
    const aspect = BRAND_MARK_CANVAS[0] / BRAND_MARK_CANVAS[1];
    let markW, markH;
    if (maxW / maxH < aspect) {
      markW = maxW;
      markH = Math.max(1, Math.round(markW / aspect));
    } else {
      markH = maxH;
      markW = Math.max(1, Math.round(markH * aspect));
    }
    return [x1 - markW, y1 - markH, x1, y1];
  }

  // ── text fitting ────────────────────────────────────────────────────
  function textWidth(ctx, size, text) {
    ctx.font = `${size}px ${FONT_FAMILY}`;
    return ctx.measureText(text).width;
  }

  function fontMetrics(ctx, size) {
    ctx.font = `${size}px ${FONT_FAMILY}`;
    const m = ctx.measureText("Ag");
    const ascent = m.fontBoundingBoxAscent !== undefined ? m.fontBoundingBoxAscent : size * 0.8;
    const descent = m.fontBoundingBoxDescent !== undefined ? m.fontBoundingBoxDescent : size * 0.2;
    return { ascent, descent };
  }

  function lineHeight(ctx, size) {
    const { ascent, descent } = fontMetrics(ctx, size);
    const gap = Math.max(MIN_LINE_GAP_PX, Math.round(size * LINE_GAP_RATIO));
    return Math.round(ascent + descent) + gap;
  }

  function truncateToWidth(ctx, size, text, maxW) {
    if (textWidth(ctx, size, text) <= maxW) return text;
    const suffix = "...";
    if (textWidth(ctx, size, suffix) > maxW) return "";
    let out = text;
    while (out.length && textWidth(ctx, size, out + suffix) > maxW) out = out.slice(0, -1);
    return out + suffix;
  }

  function fitText(ctx, text, rect) {
    const innerW = Math.max(1, rect[2] - rect[0]);
    const innerH = Math.max(1, rect[3] - rect[1]);
    const rawLines = text.split("\n");

    for (let size = MAX_FONT_PX; size >= MIN_FONT_PX; size--) {
      const lh = lineHeight(ctx, size);
      if (lh * rawLines.length <= innerH && rawLines.every((ln) => textWidth(ctx, size, ln) <= innerW)) {
        return { size, lines: rawLines, lineH: lh };
      }
    }

    const size = MIN_FONT_PX;
    const lh = lineHeight(ctx, size);
    const maxLines = Math.max(1, Math.floor(innerH / lh));
    const lines = rawLines.slice(0, maxLines).map((ln) => truncateToWidth(ctx, size, ln, innerW));
    return { size, lines, lineH: lh };
  }

  function layoutMetadata(ctx, text, side, imageRect, includeBrand) {
    const regions = naturalBorderRegions(side, imageRect, includeBrand);
    if (!regions) return null;

    const { size, lines, lineH } = fitText(ctx, text, regions.textRect);
    let brandRect = null;
    if (includeBrand && regions.brandContainer) {
      brandRect = fitBrandRect(regions.brandContainer, lineH * lines.length);
    }
    return { placement: regions.placement, textRect: regions.textRect, brandRect, size, lines, lineH };
  }

  function drawTextBottomLeft(ctx, rect, lines, size, lh) {
    ctx.font = `${size}px ${FONT_FAMILY}`;
    ctx.fillStyle = "rgb(0, 0, 0)";
    const { ascent } = fontMetrics(ctx, size);
    const totalH = lh * lines.length;
    const x = rect[0];
    let y = rect[3] - totalH;
    for (const line of lines) {
      ctx.fillText(line, x, y + ascent);
      y += lh;
    }
  }

  // ── EXIF ────────────────────────────────────────────────────────────
  function round1(v) {
    return Math.round(v * 10) / 10;
  }

  function formatShutterSpeed(val) {
    if (!(val > 0)) return "Unknown";
    return val >= 1 ? `${round1(val)}s` : `1/${Math.round(1 / val)}s`;
  }

  function formatFocalLength(val) {
    return Math.abs(val - Math.round(val)) < 0.1 ? `${Math.round(val)}mm` : `${round1(val)}mm`;
  }

  async function extractMetadata(file) {
    const md = {
      Make: "Unknown",
      Model: "Unknown",
      ISO: "Unknown",
      Aperture: "Unknown",
      "Shutter Speed": "Unknown",
      "Focal Length": "Unknown",
    };
    let tags = null;
    try {
      tags = await window.exifr.parse(file, {
        pick: ["Make", "Model", "ISO", "FNumber", "ExposureTime", "FocalLength"],
      });
    } catch (e) {
      tags = null;
    }
    if (!tags) return md;

    if (tags.Make) md.Make = String(tags.Make).trim() || "Unknown";
    if (tags.Model) md.Model = String(tags.Model).trim() || "Unknown";
    if (tags.ISO !== undefined && tags.ISO !== null) md.ISO = String(tags.ISO);
    if (tags.FNumber !== undefined && tags.FNumber !== null) md.Aperture = `f/${round1(tags.FNumber)}`;
    if (tags.ExposureTime !== undefined && tags.ExposureTime !== null) {
      md["Shutter Speed"] = formatShutterSpeed(tags.ExposureTime);
    }
    if (tags.FocalLength !== undefined && tags.FocalLength !== null) {
      md["Focal Length"] = formatFocalLength(tags.FocalLength);
    }
    return md;
  }

  function formatMetadata(md) {
    return [`Model: ${md.Model}`, `ISO ${md.ISO}`, md.Aperture, md["Shutter Speed"], md["Focal Length"]].join("\n");
  }

  function resolveBrand(make, model) {
    const haystack = `${make || ""} ${model || ""}`.toLowerCase();
    for (const [brand, [, needles]] of Object.entries(SUPPORTED_BRANDS)) {
      if (needles.some((n) => haystack.includes(n))) return brand;
    }
    return null;
  }

  // ── brand marks ─────────────────────────────────────────────────────
  const brandImageCache = new Map();
  function loadBrandImage(brand) {
    if (brandImageCache.has(brand)) return brandImageCache.get(brand);
    const p = new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = `assets/brand_marks/${brand}.png`;
    });
    brandImageCache.set(brand, p);
    return p;
  }

  async function drawBrandMark(ctx, brand, rect) {
    const img = await loadBrandImage(brand);
    ctx.drawImage(img, rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]);
  }

  // ── image loading (no EXIF auto-rotate, to match Pillow's raw pixels) ─
  async function loadSourceImage(file) {
    if ("createImageBitmap" in window) {
      try {
        const bmp = await createImageBitmap(file, { imageOrientation: "none" });
        return { width: bmp.width, height: bmp.height, drawable: bmp, close: () => bmp.close() };
      } catch (e) {
        /* fall through to <img> path */
      }
    }
    const url = URL.createObjectURL(file);
    const img = new Image();
    await new Promise((resolve, reject) => {
      img.onload = resolve;
      img.onerror = reject;
      img.src = url;
    });
    return { width: img.naturalWidth, height: img.naturalHeight, drawable: img, close: () => URL.revokeObjectURL(url) };
  }

  // ── font loading ────────────────────────────────────────────────────
  let fontReady = null;
  function ensureFont() {
    if (!fontReady) {
      const face = new FontFace(FONT_FAMILY, "url(assets/font/07558_CenturyGothic.ttf)");
      fontReady = face.load().then((loaded) => {
        document.fonts.add(loaded);
      });
    }
    return fontReady;
  }

  // ── per-file processing ─────────────────────────────────────────────
  async function processFile(file, opts) {
    await ensureFont();
    const side = opts.outputSide;
    const src = await loadSourceImage(file);
    try {
      const imageRect = fitImageRect(src.width, src.height, side);

      const canvas = document.createElement("canvas");
      canvas.width = side;
      canvas.height = side;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, side, side);
      ctx.drawImage(
        src.drawable,
        0, 0, src.width, src.height,
        imageRect[0], imageRect[1], imageRect[2] - imageRect[0], imageRect[3] - imageRect[1]
      );

      const meta = await extractMetadata(file);
      const text = formatMetadata(meta);

      let brand = null;
      if (opts.showBrand) {
        const resolved = resolveBrand(meta.Make, meta.Model);
        if (resolved && (!opts.enabledBrands || opts.enabledBrands.has(resolved))) brand = resolved;
      }

      const layout = layoutMetadata(ctx, text, side, imageRect, !!brand);
      let placement = "no border";
      if (layout) {
        drawTextBottomLeft(ctx, layout.textRect, layout.lines, layout.size, layout.lineH);
        placement = layout.placement;
        if (brand && layout.brandRect) {
          await drawBrandMark(ctx, brand, layout.brandRect);
        }
      }

      const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 1.0));
      return { blob, placement, brand, canvas, meta };
    } finally {
      src.close();
    }
  }

  window.WhiteBorder = {
    SUPPORTED_BRANDS,
    processFile,
    ensureFont,
  };
})();
