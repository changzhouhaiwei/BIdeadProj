from __future__ import annotations

import io

import segno


def render_qr_svg(text: str) -> str:
    code = segno.make(text, error="m")
    buffer = io.BytesIO()
    code.save(buffer, kind="svg", scale=6, border=2, xmldecl=False)
    return buffer.getvalue().decode("utf-8")
