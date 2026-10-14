import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_patcher():
    path = ROOT / "deploy" / "patch_nginx.py"
    spec = importlib.util.spec_from_file_location("patch_nginx", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_patch_inserts_include_once(tmp_path):
    conf_dir = tmp_path / "conf.d"
    conf_dir.mkdir()
    site = conf_dir / "fvxpcue.conf"
    site.write_text(
        "server {\n    listen 80;\n    root /var/www/fvxpcue;\n    location / { }\n}\n",
        encoding="utf-8",
    )
    patcher = load_patcher()
    status, path = patcher.patch_nginx_tree(tmp_path)
    assert status == "patched"
    assert path == str(site)
    text = site.read_text(encoding="utf-8")
    assert "include /etc/nginx/snippets/drinkboard.conf;" in text
    assert text.count("drinkboard.conf") == 1
    again, _ = patcher.patch_nginx_tree(tmp_path)
    assert again == "already"
    assert site.read_text(encoding="utf-8").count("drinkboard.conf") == 1


def test_patch_missing_site(tmp_path):
    (tmp_path / "nginx.conf").write_text("events {}\n", encoding="utf-8")
    patcher = load_patcher()
    status, path = patcher.patch_nginx_tree(tmp_path)
    assert status == "missing"
    assert path == ""
