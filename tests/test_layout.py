import sys
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import insta_preprocess as tool


FONT_PATH = ROOT / "insta" / "font" / "07558_CenturyGothic.ttf"


class LayoutTests(unittest.TestCase):
    def test_image_fit_uses_only_natural_square_borders(self):
        side = 2160

        cases = [
            ((4000, 6000), (360, 0, 1800, 2160)),
            ((6000, 4000), (0, 360, 2160, 1800)),
            ((4000, 4000), (0, 0, 2160, 2160)),
        ]
        for (width, height), expected in cases:
            with self.subTest(width=width, height=height):
                self.assertEqual(tool.fit_image_rect(width, height, side), expected)

    def test_vertical_images_use_left_and_right_borders(self):
        side = 2160
        image_rect = tool.fit_image_rect(4000, 6000, side)
        layout = tool.layout_metadata(
            self.sample_metadata_text(),
            str(FONT_PATH),
            side,
            image_rect,
            include_brand=True,
        )

        self.assertEqual(layout["placement"], "vertical-side-borders")
        self.assertLessEqual(layout["text_rect"][2], image_rect[0])
        self.assertGreaterEqual(layout["brand_rect"][0], image_rect[2])
        self.assertEqual(layout["brand_rect"][3], layout["text_rect"][3])

    def test_horizontal_images_use_lower_border(self):
        side = 2160
        image_rect = tool.fit_image_rect(6000, 4000, side)
        layout = tool.layout_metadata(
            self.sample_metadata_text(),
            str(FONT_PATH),
            side,
            image_rect,
            include_brand=True,
        )

        self.assertEqual(layout["placement"], "horizontal-bottom-border")
        self.assertGreaterEqual(layout["text_rect"][1], image_rect[3])
        self.assertGreaterEqual(layout["brand_rect"][1], image_rect[3])
        self.assertEqual(layout["brand_rect"][3], layout["text_rect"][3])

    def test_square_images_do_not_get_synthetic_metadata_border(self):
        side = 2160
        image_rect = tool.fit_image_rect(4000, 4000, side)

        self.assertIsNone(tool.natural_border_regions(side, image_rect, True))
        self.assertIsNone(
            tool.layout_metadata(
                self.sample_metadata_text(),
                str(FONT_PATH),
                side,
                image_rect,
                include_brand=True,
            )
        )

    def test_output_canvas_is_square(self):
        self.assertEqual(tool.OUTPUT_SIDE, 2160)
        self.assertEqual((tool.OUTPUT_SIDE, tool.OUTPUT_SIDE), (2160, 2160))

    def test_brand_scales_from_fitted_metadata_height(self):
        side = 2160
        image_rect = tool.fit_image_rect(6000, 4000, side)
        layout = tool.layout_metadata(
            self.sample_metadata_text(),
            str(FONT_PATH),
            side,
            image_rect,
            include_brand=True,
        )
        text_h = layout["line_h"] * len(layout["lines"])
        brand_h = layout["brand_rect"][3] - layout["brand_rect"][1]

        self.assertLessEqual(brand_h, text_h)
        self.assertLessEqual(
            layout["brand_rect"][2] - layout["brand_rect"][0],
            int(round(side * tool.MAX_BRAND_MARK_W_FRAC)),
        )
        self.assertLessEqual(brand_h, int(round(side * tool.MAX_BRAND_MARK_H_FRAC)))
        self.assertGreaterEqual(layout["font"].size, tool.MIN_FONT_PX)
        self.assertLessEqual(layout["font"].size, tool.MAX_FONT_PX)

    def test_brand_logo_toggle_removes_logo_region(self):
        side = 2160
        image_rect = tool.fit_image_rect(6000, 4000, side)
        with_brand = tool.layout_metadata(
            self.sample_metadata_text(),
            str(FONT_PATH),
            side,
            image_rect,
            include_brand=True,
        )
        without_brand = tool.layout_metadata(
            self.sample_metadata_text(),
            str(FONT_PATH),
            side,
            image_rect,
            include_brand=False,
        )

        self.assertTrue(tool.SHOW_BRAND_MARK)
        self.assertIsNotNone(with_brand["brand_rect"])
        self.assertIsNone(without_brand["brand_rect"])
        self.assertGreater(without_brand["text_rect"][2], with_brand["text_rect"][2])

    def test_brand_cap_matches_fujifilm_side_border_scale(self):
        side = 2160
        image_rect = tool.fit_image_rect(4000, 6000, side)
        layout = tool.layout_metadata(
            self.sample_metadata_text(),
            str(FONT_PATH),
            side,
            image_rect,
            include_brand=True,
        )
        brand_w = layout["brand_rect"][2] - layout["brand_rect"][0]
        brand_h = layout["brand_rect"][3] - layout["brand_rect"][1]

        self.assertLessEqual(brand_w, 253)
        self.assertLessEqual(brand_h, 76)

    @staticmethod
    def sample_metadata_text():
        return "\n".join(
            [
                "Model: ILCE-7RM5",
                "ISO 200",
                "f/2.8",
                "1/250s",
                "85mm",
            ]
        )

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
        self.assertIn("ISO 100\n", text)
        self.assertIn("f/2.8\n", text)
        self.assertIn("1/250s\n", text)
        self.assertTrue(text.endswith("50mm"))
        self.assertNotIn("Camera:", text)
        self.assertNotIn("Aperture:", text)
        self.assertNotIn("Shutter Speed:", text)
        self.assertNotIn("Focal Length:", text)
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

    def test_fit_text_shrinks_without_wrapping_metadata_lines(self):
        text = "Shutter Speed: 1/250s\nFocal Length: 200mm"
        font, lines, _ = tool.fit_text(text, str(FONT_PATH), (0, 0, 180, 500))

        self.assertEqual(lines, text.split("\n"))
        self.assertLess(font.size, tool.MAX_FONT_PX)

    def test_fit_text_truncates_instead_of_wrapping_when_too_narrow(self):
        text = "Model: THISISANUNUSUALLYLONGMODELNAMEWITHOUTSPACES\nISO 200"
        _, lines, _ = tool.fit_text(text, str(FONT_PATH), (0, 0, 90, 500))

        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].endswith("..."))

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
