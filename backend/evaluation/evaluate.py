"""Run from backend: uv run python evaluation/evaluate.py. Bundled photos only.

Generated evaluation artifacts are fixtures, not retained user uploads.
"""
import json
import platform
import sys
from io import BytesIO
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image, ImageDraw, ImageOps

from app.color import decode_image, build_lut
from app.extraction import extract_style
from app.schemas import LutSettings, StyleParams

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ADJ = {"intensity": 100, "contrast": 0, "saturation": 0, "warmth": 0}


def lut_for(style):
    return build_lut(LutSettings(styleParams=style, adjustments=ADJ))


def apply(image, lut):
    # Pillow's trilinear 3D LUT uses the same red-fastest layout as the browser.
    from PIL.ImageFilter import Color3DLUT
    return image.filter(Color3DLUT(33, lut.ravel().tolist()))


def stats(image):
    rgb = np.asarray(image, dtype=float).reshape(-1, 3) / 255
    lum = rgb @ np.array([.2126, .7152, .0722])
    lo, hi = np.quantile(lum, [.25, .75])
    def cast(mask):
        mean = rgb[mask].mean(axis=0)
        return (mean - mean.mean()).round(4).tolist()
    return {"shadow_balance": cast(lum <= lo), "highlight_balance": cast(lum >= hi),
            "chroma": float(np.ptp(rgb, axis=1).mean()),
            "contrast_p90_p10": float(np.quantile(lum, .9) - np.quantile(lum, .1))}


def main():
    images = {}
    for scene, name in [("portrait", "portrait"), ("landscape", "lake"), ("indoor", "cafe")]:
        with Image.open(ROOT / f"frontend/src/assets/sample-{name}.jpg") as im:
            images[scene] = im.convert("RGB")
    looks = {
        "split": ([.1, .5, .9], [.9, .65, .2], 1.15),
        "muted": ([.6, .5, .4], [.7, .55, .25], .55),
        "cool": ([.25, .5, .75], [.3, .5, .7], 1.0),
        "neutral": ([.5] * 3, [.5] * 3, 1.0),
    }
    results = []
    boards = []
    for index, (name, (shadow, highlight, saturation)) in enumerate(looks.items()):
        source = images[list(images)[index % 3]]
        known = StyleParams(id=name, shadowTint=shadow, highlightTint=highlight, baseSaturation=saturation)
        reference = apply(source, lut_for(known))
        reference.save(OUT / f"reference-{name}.jpg", quality=90)
        baseline = extract_style(reference, neutral_anchors=False)
        improved = extract_style(reference)
        calibrated = extract_style(reference, calibrated=True)
        board = Image.new("RGB", (1800, 3 * 260), "white")
        draw = ImageDraw.Draw(board)
        headers = ["Reference", "Target before", "v1 mean estimate", "v2 neutral anchors", "v3 calibrated", "Known grade (control)"]
        for col, header in enumerate(headers):
            draw.text((col * 300 + 5, 5), header, fill="black")
        for row, (scene, target) in enumerate(images.items()):
            before = stats(target)
            after1 = apply(target, lut_for(baseline))
            after2 = apply(target, lut_for(improved))
            after3 = apply(target, lut_for(calibrated))
            expected = apply(target, lut_for(known))
            a = np.asarray(after2, dtype=float)
            e = np.asarray(expected, dtype=float)
            results.append({"reference": name, "reference_scene": list(images)[index % 3], "target": scene,
                            "before": before, "v1": stats(after1), "v2": stats(after2), "expected": stats(expected),
                            "v3": stats(after3),
                            "v2_expected_mae_255": float(np.abs(a-e).mean()),
                            "v3_expected_mae_255": float(np.abs(np.asarray(after3, dtype=float)-e).mean()),
                            "calibrated_estimate": calibrated.model_dump(by_alias=True),
                            "estimate": improved.model_dump(by_alias=True)})
            for col, im in enumerate([reference, target, after1, after2, after3, expected]):
                thumb = ImageOps.contain(im, (290, 220))
                board.paste(thumb, (col * 300 + 5, row * 260 + 30))
            draw.text((5, row * 260 + 250), f"{name} reference -> {scene}", fill="black")
        board.save(OUT / f"comparison-{name}.jpg", quality=92)
        boards.append(board)
    large = images['landscape'].resize((4000, 3000))
    stream = BytesIO()
    large.save(stream, format="JPEG", quality=95)
    raw = stream.getvalue()
    assert len(raw) < 15 * 1024 * 1024
    raw += b'\0' * (15 * 1024 * 1024 - len(raw))
    timings = []
    for _ in range(5):
        start = perf_counter()
        with decode_image(raw) as decoded:
            style = extract_style(decoded, calibrated=True)
        lut = lut_for(style)
        timings.append((perf_counter() - start) * 1000)
    start = perf_counter()
    apply(large, lut)
    full_ms = (perf_counter() - start) * 1000
    report = {"host": platform.platform(), "python": platform.python_version(),
              "cpu": next((line.strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')), 'unknown'),
              "generation_input": {"dimensions": [4000, 3000], "bytes": len(raw)},
              "generation_with_lut_ms": timings, "python_full_resolution_ms": full_ms, "pairs": results}
    (OUT / "results.json").write_text(json.dumps(report, indent=2) + '\n')
    (OUT / "browser-lut.json").write_text(json.dumps({"size": 33, "data": lut.ravel().tolist()}))
    print(json.dumps({k:v for k,v in report.items() if k != 'pairs'}, indent=2))

if __name__ == '__main__':
    main()
