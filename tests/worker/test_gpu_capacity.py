"""`detect_gpu_capacity_bytes` (T063): the real GPU's own free memory when one is
visible, `None` (falling back to `DEFAULT_CAPACITY_BYTES`) otherwise -- proven with
`subprocess.run` and `torch` both faked, never a real GPU (FR-033, R-10).
"""

from __future__ import annotations

import subprocess

import pytest

from modelmora.worker import residency as residency_module
from modelmora.worker.residency import detect_gpu_capacity_bytes


def test_capacity_comes_from_nvidia_smi_total_minus_used(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="24564, 541\n")

    monkeypatch.setattr(residency_module.subprocess, "run", fake_run)

    assert detect_gpu_capacity_bytes() == (24564 - 541) * 1024 * 1024


def test_no_nvidia_smi_and_no_torch_reports_no_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("nvidia-smi not found")

    monkeypatch.setattr(residency_module.subprocess, "run", fake_run)

    assert detect_gpu_capacity_bytes() is None
