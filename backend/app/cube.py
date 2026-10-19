"""Pure red-fastest .cube serialization; no image, HTTP or storage access."""
import numpy as np


def write_cube(data, *, size: int = 33) -> str:
    if type(size) is not int or size != 33:
        raise ValueError("LUT size must be 33")
    samples = np.asarray(data)
    if samples.shape not in ((33 ** 3, 3), (33 ** 3 * 3,)):
        raise ValueError("Expected 35937 interleaved RGB triples")
    if samples.dtype.kind not in "fiu" or not np.isfinite(samples).all():
        raise ValueError("LUT channels must be finite numbers")
    if np.any(samples < 0) or np.any(samples > 1):
        raise ValueError("LUT channels must be in 0..1")
    rows = samples.astype(np.float32).reshape(-1, 3)
    header = 'TITLE "GradeMatch Look"\nLUT_3D_SIZE 33\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n'
    return header + "\n".join(" ".join(format(float(v), ".9g") for v in row) for row in rows) + "\n"
