"""Temporary owner-authorized failure for the dev deployment CI gate (#138)."""


def test_controlled_ci_gate_blocks_failed_commit():
    assert False, "Intentional #138 CI-gate experiment; remove in recovery commit"
