# White Border Tool

Add white borders and EXIF metadata overlays to photos for square Instagram exports.

- Fits photos into a square canvas using only the natural white space — no cropping
- Places camera metadata (model, ISO, aperture, shutter, focal length) in the border
- Optionally overlays brand marks (Canon, Nikon, Sony, Fujifilm, Samsung)
- Vertical photos use left/right borders; horizontal photos use the bottom border
- Square photos with no usable border are output without metadata overlay

---

## Download (no Python needed)

Grab the latest pre-built binary from the [Releases](../../releases) page:

| Platform | File |
|----------|------|
| Windows  | `whiteborder-windows.exe` |
| macOS — Apple Silicon (M1/M2/M3) | `whiteborder-macos-arm64` |
| macOS — Intel | `whiteborder-macos-intel` |
| Linux    | `whiteborder-linux` |

Place the binary in a folder alongside `input/` and `output/` directories, then run it.

> **macOS note:** The binary is unsigned. On first launch, macOS will block it.
> Fix: right-click the file → **Open** → **Open** in the dialog.
> Or run once in Terminal: `xattr -d com.apple.quarantine whiteborder-macos-*`
>
> On macOS/Linux, make it executable first: `chmod +x whiteborder-macos-*`

---

## Setup (Python)

**Python 3.8+ required.**

```bash
pip install -r requirements.txt
```

### Folder structure

```
whiteborder_tool/
├── whiteborder.py       # CLI script
├── whiteborder_gui.py   # GUI script
├── brand_marks/         # Brand mark PNGs (bundled)
├── font/                # Font (bundled)
├── input/               # Drop your photos here
└── output/              # Processed images appear here
```

---

## Usage

### GUI

```bash
python whiteborder_gui.py
```

Select input/output folders, pick which brand marks to show, choose output size, and hit **Process Images**.

### CLI

```bash
# Basic — reads input/, writes to output/
python whiteborder.py

# Custom folders
python whiteborder.py photos/ exports/

# 1080 px output, no brand marks
python whiteborder.py --size 1080 --no-brand

# Only show Canon and Sony marks
python whiteborder.py --brands canon sony

# All options
python whiteborder.py --help
```

---

## Notes

- Input files are never modified.
- Output files are saved as `<original-name>_insta.jpg` at quality 100.
- EXIF is read with `exifread` when available, falling back to Pillow's parser.
- Missing EXIF fields appear as `Unknown`.
- Brand mark assets must be present in `brand_marks/`; the script raises an error if one is missing.

---

## Credits

Developed by **Choepi**.
