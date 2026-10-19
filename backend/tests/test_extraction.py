import numpy as np
from PIL import Image

from app.extraction import extract_style
from app.color import build_lut
from app.schemas import LutSettings


def test_neutral_reference_has_no_generic_tint_or_desaturation():
    gray = np.tile(np.arange(256, dtype=np.uint8), (64, 1))
    style = extract_style(Image.fromarray(np.repeat(gray[..., None], 3, axis=2)))
    assert style.shadow_tint == [.5, .5, .5]
    assert style.highlight_tint == [.5, .5, .5]
    assert style.base_saturation == 1
    settings = LutSettings(styleParams=style, adjustments={"intensity": 80, "contrast": 0, "saturation": 0, "warmth": 0})
    lut = build_lut(settings).reshape(33, 33, 33, 3)
    np.testing.assert_array_equal(lut[0, 0, :, 0], np.linspace(0, 1, 33))


def test_extraction_is_deterministic_bounded_and_downscaled():
    image = Image.new("RGB", (2300, 1100), (40, 90, 160))
    first = extract_style(image)
    assert first == extract_style(image)
    assert max(image.size) == 2300  # caller's original is untouched
    assert all(0 <= x <= 1 for x in first.shadow_tint + first.highlight_tint)
    assert first.shadow_tint[2] > first.shadow_tint[0]
    settings = LutSettings(styleParams=first, adjustments={"intensity": 80, "contrast": 0, "saturation": 0, "warmth": 0})
    lut = build_lut(settings)
    assert lut.shape == (35937, 3) and np.isfinite(lut).all()
    assert lut.min() >= 0 and lut.max() <= 1


def test_analysis_cap_matches_an_explicit_1024_pixel_analysis_copy():
    rng = np.random.default_rng(7)
    image = Image.fromarray(rng.integers(0, 256, (1050, 1400, 3), dtype=np.uint8))
    copy = image.copy()
    copy.thumbnail((1024, 1024))
    assert max(copy.size) == 1024
    assert extract_style(image) == extract_style(copy)


def test_neutral_anchor_revision_reduces_highlight_subject_bias():
    pixels = np.full((64, 100, 3), 100, dtype=np.uint8)
    pixels[:, 20:, :] = [180, 60, 60]
    image = Image.fromarray(pixels)
    baseline = extract_style(image, neutral_anchors=False)
    anchored = extract_style(image)
    assert np.ptp(anchored.highlight_tint) < np.ptp(baseline.highlight_tint)
