from __future__ import annotations

import io

import segno


def render_qr_svg(text: str) -> str:
    code = segno.make(text, error="m")
    buffer = io.StringIO()
    code.save(buffer, kind="svg", scale=6, border=2, xmldecl=False)
    return buffer.getvalue()
