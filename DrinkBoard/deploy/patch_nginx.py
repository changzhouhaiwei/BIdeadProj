#!/usr/bin/env python3
"""把 DrinkBoard 的 include 写进现有 Nginx 站点，只写一次。"""

from __future__ import annotations

import sys
from pathlib import Path

INCLUDE = "include /etc/nginx/snippets/drinkboard.conf;"
MARKER = "snippets/drinkboard.conf"


def iter_confs(root: Path):
    if not root.exists():
        return
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name == "drinkboard.conf":
            continue
        if path.suffix == ".conf" or path.name in {"default", "nginx.conf"}:
            yield path


def patch_nginx_tree(root: Path) -> tuple[str, str]:
    confs = list(iter_confs(root))
    for path in confs:
        text = path.read_text(encoding="utf-8", errors="replace")
        if MARKER in text:
            return "already", str(path)
    target = None
    for path in confs:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "/var/www/fvxpcue" in text:
            target = path
            break
    if target is None:
        return "missing", ""
    original = target.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    insert_at = None
    for index, line in enumerate(lines):
        if "root" in line and "/var/www/fvxpcue" in line:
            insert_at = index + 1
            break
    if insert_at is None:
        for index, line in enumerate(lines):
            if "server" in line and "{" in line:
                insert_at = index + 1
                break
    if insert_at is None:
        return "missing", ""
    backup = Path(str(target) + ".bak-drinkboard")
    backup.write_text(original, encoding="utf-8")
    lines.insert(insert_at, f"    {INCLUDE}\n")
    target.write_text("".join(lines), encoding="utf-8")
    return "patched", str(target)


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/etc/nginx")
    status, path = patch_nginx_tree(root)
    print(f"{status} {path}".rstrip())
    sys.exit(0 if status in {"patched", "already"} else 2)


if __name__ == "__main__":
    main()
