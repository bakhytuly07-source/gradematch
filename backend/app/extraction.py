"""Deterministic prototype: estimate low-chroma tonal anchors in SDR RGB.

A single finished photograph cannot identify the original grade. In particular,
colored illumination and a scene without neutral objects are ambiguous. This
module deliberately keeps estimates bounded rather than claiming grade recovery.
"""
import hashlib

import numpy as np
from PIL import Image

from .schemas import StyleParams

WEIGHTS = np.array([0.2126, 0.7152, 0.0722])


def extract_style(image: Image.Image, *, neutral_anchors: bool = True, calibrated: bool = False) -> StyleParams:
    analysis = image.convert("RGB")
    analysis.thumbnail((1024, 1024))
    pixels = np.asarray(analysis, dtype=np.float64).reshape(-1, 3) / 255
    lum = pixels @ WEIGHTS
    low, high = np.quantile(lum, [.25, .75])
    tints = []
    for mask in (lum <= low, lum >= high):
        band = pixels[mask]
        if neutral_anchors:
            # Reject strongly chromatic subject pixels before estimating a cast.
            chroma = np.ptp(band, axis=1)
            band = band[chroma <= np.quantile(chroma, .2)]
        balance = band.mean(axis=0)
        residual = balance - balance.mean()
        if calibrated:
            # Invert the prototype builder's 0.25 tint attenuation.
            residual *= 4
        tints.append(np.clip(.5 + residual, 0, 1).tolist())
    # Unlike the former 0.8+chroma rule, achromatic references remain neutral.
    # Chroma still depends on scene content: evaluate that limitation explicitly.
    chroma = np.mean(np.ptp(pixels, axis=1))
    saturation = float(np.clip(1 + (chroma - .2) * .5, .8, 1.2))
    if calibrated:
        saturation = float(np.clip(chroma / .16, .35, 1.5))
    if chroma < 1 / 255:
        saturation = 1.0
    identifier = hashlib.sha256(analysis.tobytes()).hexdigest()[:24]
    return StyleParams(id=identifier, shadowTint=tints[0], highlightTint=tints[1],
                       baseSaturation=saturation)
