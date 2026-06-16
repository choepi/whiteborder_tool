# White Border Tool by Choepi

## Overview

The **White Border Tool** preprocesses images by:

1. Adding a white square canvas.
2. Fitting the photo above a reserved bottom metadata band, so text never covers the image.
3. Adding model-only EXIF metadata at the bottom-left.
4. Adding a normalized black brand mark at the bottom-right for Canon, Nikon, Sony, Fujifilm, and Samsung.

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
- Brand mark PNGs are normalized to the same canvas size for consistent bottom-right placement.
- If brand mark files are missing, the script can regenerate them from the configured font.

---

## Credits

Developed by **Choepi**.
