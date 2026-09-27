
import common


def test_project_root_uses_env_var(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCAL_LAB_AI_ROOT", str(tmp_path))
    assert common.project_root() == tmp_path.resolve()


def test_manifest_roundtrip(tmp_path):
    data = {"engine": {"status": "installed"}, "model": {"status": "installed"}}
    common.save_manifest(tmp_path, data)
    loaded = common.load_manifest(tmp_path)
    assert loaded == data


def test_missing_manifest_returns_empty_dict(tmp_path):
    assert common.load_manifest(tmp_path) == {}


def test_sha256_of_file_is_correct(tmp_path):
    import hashlib

    f = tmp_path / "data.bin"
    f.write_bytes(b"hello world")
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert common.sha256_of_file(f) == expected
