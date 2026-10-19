import base64
import binascii
from io import BytesIO
import warnings

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from .errors import ApiError
from .models import new_id
from .schemas import LutSettings, StyleParams

MAX_BYTES = 15 * 1024 * 1024
FORMATS = {"JPEG", "PNG", "WEBP"}


def decode_image(data: bytes) -> Image.Image:
    if not data:
        raise ApiError(422, "Image is empty or unreadable.")
    supported = data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG\r\n\x1a\n") or (
        data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    )
    if not supported:
        raise ApiError(415, "Use JPEG, PNG or WebP.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in FORMATS:
                    raise ApiError(415, "Use JPEG, PNG or WebP.")
                image.load()
                return ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ApiError(422, "Image is corrupt or cannot be decoded.") from None


def normalize_thumbnail(value: str) -> str:
    if not value:
        return ""
    prefix = "data:image/jpeg;base64,"
    if not value.startswith(prefix) or len(value) > 2 * MAX_BYTES:
        raise ApiError(422, "Thumbnail must be a JPEG data URL.")
    try:
        data = base64.b64decode(value[len(prefix):], validate=True)
    except (binascii.Error, ValueError):
        raise ApiError(422, "Invalid thumbnail data.") from None
    if not data.startswith(b"\xff\xd8\xff"):
        raise ApiError(422, "Thumbnail must be JPEG.")
    try:
        image = decode_image(data)
    except ApiError:
        raise ApiError(422, "Invalid thumbnail image.") from None
    image.thumbnail((256, 256))
    output = BytesIO()
    image.save(output, format="JPEG", quality=85)
    return prefix + base64.b64encode(output.getvalue()).decode("ascii")


def analyze(data: bytes) -> StyleParams:
    image = decode_image(data)
    image.thumbnail((1024, 1024))
    pixels = np.asarray(image, dtype=np.float64).reshape(-1, 3) / 255
    luminance = pixels @ np.array([0.2126, 0.7152, 0.0722])
    low, high = np.quantile(luminance, [0.25, 0.75])
    shadows = pixels[luminance <= low].mean(axis=0)
    highlights = pixels[luminance >= high].mean(axis=0)
    # Estimate relative channel balance, rather than using absolute brightness as tint.
    shadows = np.clip(0.5 + shadows - shadows.mean(), 0, 1)
    highlights = np.clip(0.5 + highlights - highlights.mean(), 0, 1)
    chroma = np.mean(pixels.max(axis=1) - pixels.min(axis=1))
    return StyleParams(id=new_id(), shadowTint=shadows.tolist(), highlightTint=highlights.tolist(),
                       baseSaturation=float(np.clip(0.8 + chroma, 0.8, 1.5)))


def build_lut(settings: LutSettings) -> np.ndarray:
    style, adj = settings.style_params, settings.adjustments
    # Mesh axes are B,G,R, so flattened cube rows change R fastest.
    b, g, r = np.meshgrid(*([np.linspace(0, 1, 33)] * 3), indexing="ij")
    rgb = np.stack([r, g, b], axis=-1).reshape(-1, 3)
    k = adj.intensity / 100
    weights = np.array([0.2126, 0.7152, 0.0722])
    lum = (rgb @ weights)[:, None]
    rgb += (np.array(style.shadow_tint) - 0.5) * (1 - lum) * 0.25 * k
    rgb += (np.array(style.highlight_tint) - 0.5) * lum * 0.25 * k
    lum = (rgb @ weights)[:, None]
    sat = (style.base_saturation * k + 1 - k) * (1 + adj.saturation / 50)
    rgb = lum + (rgb - lum) * sat
    rgb = (rgb - 0.5) * (1 + adj.contrast / 50) + 0.5
    rgb += np.array([1, 0, -1]) * (adj.warmth / 50) * 0.08
    return np.clip(rgb, 0, 1).astype(np.float32)


def cube_text(settings: LutSettings) -> str:
    lut = build_lut(settings)
    header = 'TITLE "GradeMatch Look"\nLUT_3D_SIZE 33\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n'
    return header + "\n".join(" ".join(format(float(v), ".9g") for v in row) for row in lut) + "\n"
