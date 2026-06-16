import sys
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import insta_preprocess as tool


FONT_PATH = ROOT / "insta" / "font" / "07558_CenturyGothic.ttf"


class LayoutTests(unittest.TestCase):
    def test_image_fit_reserves_footer_for_common_orientations(self):
        side = 2160
        footer_h = tool.footer_height(side)
        footer_top = side - footer_h

        for width, height in [(6000, 4000), (4000, 6000), (4000, 4000)]:
            with self.subTest(width=width, height=height):
                rect = tool.fit_image_rect(width, height, side, footer_h)
                self.assertGreaterEqual(rect[0], 0)
                self.assertGreaterEqual(rect[1], 0)
                self.assertLessEqual(rect[2], side)
                self.assertLessEqual(rect[3], footer_top)

    def test_metadata_regions_are_bottom_left_and_bottom_right(self):
        side = 2160
        footer_h = tool.footer_height(side)
        footer_top = side - footer_h

        text_rect, brand_rect = tool.metadata_regions(side, footer_h, include_brand=True)

        self.assertGreaterEqual(text_rect[0], 0)
        self.assertGreaterEqual(text_rect[1], footer_top)
        self.assertEqual(text_rect[3], brand_rect[3])
        self.assertLess(text_rect[2], brand_rect[0])
        self.assertEqual(brand_rect[2], side - text_rect[0])

    def test_format_metadata_uses_model_only(self):
        text = tool.format_metadata(
            {
                "Make": "Canon",
                "Model": "EOS R5",
                "ISO": "100",
                "Aperture": "f/2.8",
                "Shutter Speed": "1/250s",
                "Focal Length": "50mm",
            }
        )

        self.assertTrue(text.startswith("Model: EOS R5\n"))
        self.assertNotIn("Camera:", text)
        self.assertNotIn("Canon EOS R5", text)

    def test_brand_resolution_uses_make_or_model(self):
        cases = [
            ("Canon", "EOS R5", "canon"),
            ("NIKON CORPORATION", "NIKON Z 8", "nikon"),
            ("", "ILCE-7RM5", "sony"),
            ("FUJIFILM", "X-T5", "fujifilm"),
            ("samsung", "Galaxy S24 Ultra", "samsung"),
            ("Unknown", "Unknown", None),
        ]

        for make, model, expected in cases:
            with self.subTest(make=make, model=model):
                self.assertEqual(tool.resolve_brand(make, model), expected)

    def test_pillow_exif_parser_extracts_model_and_exposure_fields(self):
        md = tool.metadata_from_pillow_exif(
            {
                271: "SONY",
                272: "ILCE-7RM5",
                34855: 200,
                33437: (28, 10),
                33434: (1, 250),
                37386: (85, 1),
            }
        )

        self.assertEqual(md["Make"], "SONY")
        self.assertEqual(md["Model"], "ILCE-7RM5")
        self.assertEqual(md["ISO"], "200")
        self.assertEqual(md["Aperture"], "f/2.8")
        self.assertEqual(md["Shutter Speed"], "1/250s")
        self.assertEqual(md["Focal Length"], "85mm")

    def test_pillow_exif_parser_reads_nested_exif_ifd(self):
        class FakeExif(dict):
            def get_ifd(self, tag):
                if tag != 34665:
                    raise KeyError(tag)
                return {
                    34855: 400,
                    33437: 4.0,
                    33434: 0.5,
                    37386: 35.0,
                }

        md = tool.metadata_from_pillow_exif(
            FakeExif(
                {
                    271: "FUJIFILM",
                    272: "X100T",
                    34665: 123,
                }
            )
        )

        self.assertEqual(md["ISO"], "400")
        self.assertEqual(md["Aperture"], "f/4.0")
        self.assertEqual(md["Shutter Speed"], "1/2s")
        self.assertEqual(md["Focal Length"], "35mm")

    def test_wrap_splits_long_tokens_to_region_width(self):
        font = tool.load_font(str(FONT_PATH), 24)
        lines = tool.wrap_text_preserve_newlines(
            "Model: THISISANUNUSUALLYLONGMODELNAMEWITHOUTSPACES",
            font,
            max_w=160,
        )

        self.assertGreater(len(lines), 1)
        for line in lines:
            self.assertLessEqual(tool.text_width(font, line), 160)

    def test_brand_mark_assets_are_black_transparent_pngs(self):
        for brand in tool.SUPPORTED_BRANDS:
            with self.subTest(brand=brand):
                path = ROOT / "insta" / "brand_marks" / f"{brand}.png"
                self.assertTrue(path.exists())
                with Image.open(path) as img:
                    self.assertEqual(img.size, tool.BRAND_MARK_CANVAS)
                    self.assertEqual(img.mode, "RGBA")
                    data = (
                        img.get_flattened_data()
                        if hasattr(img, "get_flattened_data")
                        else img.getdata()
                    )
                    pixels = list(data)

                transparent = [p for p in pixels if p[3] == 0]
                visible = [p for p in pixels if p[3] > 0]
                black = [p for p in visible if p[0] <= 5 and p[1] <= 5 and p[2] <= 5]

                self.assertGreater(len(transparent), 0)
                self.assertGreater(len(visible), 0)
                self.assertGreater(len(black), 0)
                self.assertGreater(len(black) / len(visible), 0.95)

    def test_missing_brand_mark_is_not_synthesized(self):
        self.assertFalse(hasattr(tool, "generate_brand_mark_image"))
        with self.assertRaises(FileNotFoundError):
            tool.load_brand_mark("canon", ROOT / "does-not-exist-brand-assets")


if __name__ == "__main__":
    unittest.main()
