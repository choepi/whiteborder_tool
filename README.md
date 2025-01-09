# White Border App by Choepi

## Overview
The **White Border App** is a Python-based tool designed to preprocess images by:
1. Adding a white border to make them square.
2. Overlaying metadata (camera, ISO, aperture, etc.) extracted from the image's EXIF data.

This tool processes all images in a specified input folder (`insta/01_pre`) and saves the processed images in an output folder (`insta/02_post`).

---

## Requirements
- Windows operating system (the `.exe` is built for Windows).
- The `insta` folder must be in the same directory as the `.exe` file.

### Folder Structure
Ensure the following folder structure exists alongside the `.exe`:

your_app/
├── README.md            # The README file
├── insta_preprocess.exe # The executable
└── insta/
    ├── 01_pre/          # Input folder for images (add images here)
    ├── 02_post/         # Output folder for processed images
    └── font/            # Folder containing font files
        └── <font>.ttf   # Example font file



---

## Usage

1. **Prepare Input Files:**
   - Place all images you want to process in the `insta/01_pre` folder.
   - Supported formats: `.jpg`, `.jpeg`, `.png`.

2. **Run the Tool:**
   - Double-click `insta_preprocess.exe` to start processing.
   - A console window will show the progress of each file.

3. **View Results:**
   - Processed images with white borders and metadata will be saved in `insta/02_post`.

---

## Troubleshooting

1. **Font Error**:
   - Ensure the `font` folder contains at least one `.ttf` file.
   - If the font file is missing or corrupt, the app will throw an error.

2. **Input Folder Not Found**:
   - Ensure the `01_pre` folder exists inside the `insta` directory.
   - If the folder is missing, create it and add your images.

3. **Output Folder Issues**:
   - If the `02_post` folder does not exist, the app will create it automatically.
   - Check the console for saved file paths.

4. **EXIF Metadata Missing**:
   - If some metadata fields (e.g., ISO, aperture) are missing, the app will use "Unknown" as a placeholder.

---

## Notes
- Large images may take longer to process.
- This app does not modify the original files in the `01_pre` folder.
- If you encounter unexpected issues, ensure your input images have proper EXIF data or contact the developer.

---

## Credits
Developed by **Choepi**.

