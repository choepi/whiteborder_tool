# White Border Tool by Choepi

## Overview

The **White Border Tool** preprocesses images by:

1. Adding a white square canvas.
2. Fitting the photo to the square without adding extra metadata space.
3. Placing model-only EXIF metadata and the brand mark only in natural white borders.
4. Using left/right borders for vertical images and the lower border for horizontal images.
5. Adding a normalized black brand mark for Canon, Nikon, Sony, Fujifilm, and Samsung.

Processed images are read from `insta/01_pre` and saved to `insta/02_post`.

---

## Requirements

- Windows operating system if you use the bundled `.exe`.
- The `insta` folder must be in the same directory as the `.exe` file.
- The Python script requires Pillow. It can use ExifRead when installed, but falls back to Pillow EXIF parsing.

### Folder Structure

Ensure this structure exists alongside the `.exe`:

```text
downloaded folder/
|-- README.md
|-- insta_preprocess.exe
|-- insta/
    |-- 01_pre/          # Input images
    |-- 02_post/         # Processed output images
    |-- brand_marks/     # Black PNG brand marks
    |-- font/
        |-- <font>.ttf
```

---

## Usage

1. Place `.jpg`, `.jpeg`, or `.png` files in `insta/01_pre`.
2. Run `insta_preprocess.exe`, or run `insta_preprocess.py` with Python.
3. Processed square images are saved in `insta/02_post`.

### Logo Toggle

Set `SHOW_BRAND_MARK = False` near the top of `insta_preprocess.py` to hide brand logos while keeping the metadata.

---

## Troubleshooting

1. **Font Error**
   - Ensure `insta/font` contains the expected `.ttf` file.

2. **Input Folder Not Found**
   - Ensure `insta/01_pre` exists and contains images.

3. **Output Folder Issues**
   - If `insta/02_post` does not exist, the app creates it.

4. **EXIF Metadata Missing**
   - Missing fields are shown as `Unknown`.
   - If a camera brand cannot be recognized, no brand mark is drawn.

---

## Notes

- The original files in `insta/01_pre` are not modified.
- Square or near-square images with no usable natural border are left without metadata instead of drawing over the photo.
- Brand mark PNGs are original logo-derived assets normalized to the same canvas size for consistent bottom-right placement.
- If a recognized brand mark file is missing, the script raises an error instead of generating a replacement.

---

## Credits

Developed by **Choepi**.
