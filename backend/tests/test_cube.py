from io import StringIO

import numpy as np
import pytest

from app.cube import write_cube


def test_identity_red_fastest_and_headers():
    b, g, r = np.meshgrid(*([np.linspace(0, 1, 33)] * 3), indexing="ij")
    data = np.stack([r, g, b], axis=-1).reshape(-1, 3)
    text = write_cube(data)
    lines = text.splitlines()
    assert lines[:4] == ['TITLE "GradeMatch Look"', 'LUT_3D_SIZE 33',
                         'DOMAIN_MIN 0.0 0.0 0.0', 'DOMAIN_MAX 1.0 1.0 1.0']
    assert len(lines[4:]) == 35937
    parsed = np.loadtxt(StringIO(text), skiprows=4, dtype=np.float32)
    np.testing.assert_array_equal(parsed[1], [1/32, 0, 0])
    np.testing.assert_array_equal(parsed[33], [0, 1/32, 0])
    np.testing.assert_array_equal(parsed[1089], [0, 0, 1/32])
    np.testing.assert_array_equal(parsed, data.astype(np.float32))


def test_nontrivial_samples_round_trip_float32_exactly():
    data = np.random.default_rng(19).random((35937, 3), dtype=np.float32)
    data[0] = [0, 1, np.nextafter(np.float32(0), np.float32(1))]
    data[1] = [np.finfo(np.float32).tiny, .0000000123, .99999994]
    parsed = np.loadtxt(StringIO(write_cube(data.ravel())), skiprows=4, dtype=np.float32)
    np.testing.assert_array_equal(parsed, data)


@pytest.mark.parametrize('data,size', [
    (np.zeros((35937, 3)), 17), (np.zeros(107810), 33),
    (np.full(107811, np.nan), 33), (np.full(107811, np.inf), 33),
    (np.full(107811, -1e-10), 33), (np.full(107811, 1.000000001), 33),
    (np.full(107811, 'x'), 33), (np.zeros((33, 33, 33, 3)), 33),
])
def test_reject_invalid_data(data, size):
    with pytest.raises(ValueError):
        write_cube(data, size=size)
