#!/usr/bin/env python3
"""Minimal static server for Unity WebGL Brotli builds."""
from __future__ import annotations

import argparse
import mimetypes
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class UnityWebGLHandler(SimpleHTTPRequestHandler):
    def guess_type(self, path: str):
        # Serve .br with the uncompressed file's MIME type.
        if path.endswith(".br"):
            path = path[:-3]
        ext = os.path.splitext(path)[1].lower()
        mapping = {
            ".html": "text/html",
            ".js": "application/javascript",
            ".wasm": "application/wasm",
            ".data": "application/octet-stream",
            ".json": "application/json",
            ".css": "text/css",
            ".png": "image/png",
            ".ico": "image/x-icon",
        }
        if ext in mapping:
            return mapping[ext]
        guessed, _ = mimetypes.guess_type(path)
        return guessed or "application/octet-stream"

    def end_headers(self) -> None:
        path = self.translate_path(self.path.split("?", 1)[0].split("#", 1)[0])
        if path.endswith(".br"):
            self.send_header("Content-Encoding", "br")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="WebGL build directory")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    root = os.path.abspath(args.dir)
    os.chdir(root)
    server = ThreadingHTTPServer((args.host, args.port), UnityWebGLHandler)
    print(f"Serving Unity WebGL at http://{args.host}:{args.port}/")
    print(f"Root: {root}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
