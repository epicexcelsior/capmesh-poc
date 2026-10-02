import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile

import pytest


def load_exporter():
    path = Path(__file__).resolve().parents[1] / "scripts/export_judge_demo.py"
    spec = importlib.util.spec_from_file_location("judge_export", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_judge_package_contains_only_public_assets_and_works_under_a_url_prefix(tmp_path, monkeypatch):
    module = load_exporter()
    root = tmp_path / "source"
    for relative in module.ASSETS.values():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("public fixture")
    (root / "docs/proof.html").write_text('<main><a href="/">Back to dispatch desk</a></main><script src="/proof.js"></script>')
    (root / "secret.keypair.json").write_text("PRIVATE FIXTURE")
    monkeypatch.setattr(module, "ROOT", root)
    output = tmp_path / "site"
    archive = module.export(output)
    assert './proof.js' in (output / "index.html").read_text()
    assert 'href="./index.html"' in (output / "index.html").read_text()
    with ZipFile(archive) as bundle:
        assert set(bundle.namelist()) == {*module.ASSETS, "index.html", "README.txt", "manifest.json"}
        assert all(b"PRIVATE FIXTURE" not in bundle.read(name) for name in bundle.namelist())
    manifest = json.loads((output / "manifest.json").read_text())
    assert set(manifest) == {*module.ASSETS, "index.html", "README.txt"}
    with pytest.raises(ValueError, match="already exists"):
        module.export(output)


def test_existing_archive_preserves_both_paths(tmp_path):
    module = load_exporter()
    output = tmp_path / "site"
    archive = tmp_path / "site.zip"
    archive.write_bytes(b"existing package")
    with pytest.raises(ValueError, match="already exists"):
        module.export(output)
    assert not output.exists()
    assert archive.read_bytes() == b"existing package"
