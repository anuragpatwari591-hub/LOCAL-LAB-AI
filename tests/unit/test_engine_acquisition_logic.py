"""Tests for engine/acquire_engine.py logic that don't require network
access: tag parsing and platform/asset-name handling."""

import acquire_engine


def test_latest_build_tag_picks_highest_number(monkeypatch):
    fake_output = (
        "abc\trefs/tags/b100\n"
        "def\trefs/tags/b9999\n"
        "ghi\trefs/tags/b250\n"
        "jkl\trefs/tags/v0.1.0\n"
    )

    class FakeResult:
        stdout = fake_output
        returncode = 0

    def fake_run(*args, **kwargs):
        return FakeResult()

    monkeypatch.setattr(acquire_engine.subprocess, "run", fake_run)
    assert acquire_engine._latest_build_tag() == "b9999"


def test_unsupported_platform_raises():
    import pytest

    with pytest.raises(acquire_engine.EngineAcquisitionError):
        acquire_engine.acquire_engine(project_root=__import__("pathlib").Path("/tmp"), platform_name="MSDOS")


def test_asset_candidates_defined_for_windows_and_linux():
    assert "Linux" in acquire_engine._ASSET_CANDIDATES
    assert "Windows" in acquire_engine._ASSET_CANDIDATES
    for candidates in acquire_engine._ASSET_CANDIDATES.values():
        assert all("{tag}" in c for c in candidates)


def test_no_gpu_asset_names_are_preferred_first():
    for platform_name, candidates in acquire_engine._ASSET_CANDIDATES.items():
        first = candidates[0].lower()
        assert "cuda" not in first and "vulkan" not in first and "rocm" not in first
