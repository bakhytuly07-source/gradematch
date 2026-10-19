from copy import deepcopy
from itertools import product

import numpy as np
import pytest
from pydantic import ValidationError

from app.color import build_lut
from app.schemas import Adjustments

SETTINGS = {"styleParams": {"id": "fixture", "shadowTint": [.3, .5, .7],
                          "highlightTint": [.8, .5, .2], "baseSaturation": 1.2},
            "adjustments": {"intensity": 80, "contrast": 0, "saturation": 0, "warmth": 0}}


def settings(**changes):
    result = deepcopy(SETTINGS)
    result['adjustments'].update(changes)
    return result


def test_defaults_and_identity():
    assert Adjustments.defaults().model_dump() == {'intensity': 80, 'contrast': 0, 'saturation': 0, 'warmth': 0}
    lut = build_lut(settings(intensity=0)).reshape(33, 33, 33, 3)
    for b,g,r in [(0,0,0), (32,32,32), (7,13,29)]:
        np.testing.assert_array_equal(lut[b,g,r], np.array([r,g,b])/32)


def test_controls_have_directional_effects():
    def point(**changes):
        return build_lut(settings(intensity=0, **changes)).reshape(33,33,33,3)[8,16,24]
    normal = point()
    warm, cool = point(warmth=50), point(warmth=-50)
    assert warm[0] > normal[0] > cool[0] and warm[2] < normal[2] < cool[2]
    assert np.ptp(point(saturation=50)) > np.ptp(normal) > np.ptp(point(saturation=-50))
    assert np.linalg.norm(point(contrast=25)-.5) > np.linalg.norm(normal-.5)
    assert np.linalg.norm(point(contrast=-25)-.5) < np.linalg.norm(normal-.5)
    identity = build_lut(settings(intensity=0))
    half = build_lut(settings(intensity=50))
    full = build_lut(settings(intensity=100))
    assert np.linalg.norm(full-identity) > np.linalg.norm(half-identity) > 0


@pytest.mark.parametrize('values', list(product([0,100],[-50,50],[-50,50],[-50,50])))
def test_combined_extremes_are_finite_bounded_deterministic(values):
    data = settings(**dict(zip(['intensity','contrast','saturation','warmth'],values)))
    lut = build_lut(data)
    assert lut.shape == (35937,3) and lut.dtype == np.float32
    assert np.isfinite(lut).all() and lut.min() >= 0 and lut.max() <= 1
    np.testing.assert_array_equal(lut, build_lut(data))


@pytest.mark.parametrize('field,value', [('intensity',101),('contrast',-51),('warmth',float('nan')),
    ('saturation',float('inf')),('warmth','5'),('intensity',True)])
def test_invalid_controls_rejected(field,value):
    with pytest.raises(ValidationError):
        build_lut(settings(**{field:value}))


def test_missing_or_extra_controls_rejected():
    for mutation in ['missing','extra']:
        data = settings()
        if mutation == 'missing':
            del data['adjustments']['warmth']
        else:
            data['adjustments']['tint'] = 0
        with pytest.raises(ValidationError):
            build_lut(data)


def test_unbounded_finite_base_saturation_does_not_overflow():
    data = settings(saturation=50)
    data['styleParams']['baseSaturation'] = 1.7e308
    lut = build_lut(data)
    assert np.isfinite(lut).all() and 0 <= lut.min() <= lut.max() <= 1
