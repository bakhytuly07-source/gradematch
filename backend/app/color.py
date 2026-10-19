import base64
import binascii
from io import BytesIO
import warnings

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from .cube import write_cube
from .errors import ApiError
from .extraction import extract_style
from .schemas import LutSettings, StyleParams

MAX_BYTES = 15 * 1024 * 1024
FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_PIXELS = 24_000_000


def decode_image(data: bytes) -> Image.Image:
    if len(data) > MAX_BYTES:
        raise ApiError(413, "Reference image exceeds 15 MB.")
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
                if image.width * image.height > MAX_PIXELS:
                    raise ApiError(422, "Decoded image exceeds 24 megapixels.")
                image.verify()
            with Image.open(BytesIO(data)) as image:
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
    # Evaluated conservative v2 estimate; #18 documents unresolved quality limits.
    with decode_image(data) as image:
        return extract_style(image)


def build_lut(settings: LutSettings | dict) -> np.ndarray:
    # Revalidate model instances too: callers may have mutated their fields.
    payload = settings.model_dump(by_alias=True) if isinstance(settings, LutSettings) else settings
    settings = LutSettings.model_validate(payload)
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
    # longdouble prevents intermediate overflow for the contract's unbounded,
    # finite baseSaturation. Saturation zero remains achromatic at any style.
    sat = (np.longdouble(style.base_saturation) * k + 1 - k) * (1 + adj.saturation / 50)
    rgb = lum.astype(np.longdouble) + (rgb - lum).astype(np.longdouble) * sat
    rgb = (rgb - 0.5) * (1 + adj.contrast / 50) + 0.5
    rgb += np.array([1, 0, -1]) * (adj.warmth / 50) * 0.08
    return np.clip(rgb, 0, 1).astype(np.float32)


def cube_text(settings: LutSettings) -> str:
    return write_cube(build_lut(settings))
