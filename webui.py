#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拼豆图纸 - 网页版界面（本地服务器，浏览器打开）。

用法：
  双击 拼豆图纸网页版.bat          -> 自动打开浏览器
  或命令行: python webui.py [--port 8765] [--no-browser]

复用 main.py 的转换逻辑（进程内调用），零额外依赖（仅需 numpy + Pillow）。
"""
import argparse
import contextlib
import io
import json
import mimetypes
import os
import shutil
import sys
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE, "web")
OUT_DIR = os.path.join(BASE, "output")
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "bead_pattern_web_uploads")
HOST = "127.0.0.1"
DEFAULT_PORT = 8765

os.chdir(BASE)  # 固定工作目录，保证 output/ 相对路径正确
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

PALETTES = ["mard", "perler", "artkal", "hama"]
LABELS = ["brand", "letter", "number"]

PALETTE_NOTE = {
    "mard": "MARD 291色（国内拼豆，色号如 H5 / F11）",
    "perler": "Perler 95色（经典）",
    "artkal": "Artkal 30色（A01-A30）",
    "hama": "Hama 28色（H01-H28）",
}


# ---------------------------------------------------------------------------
# 参数 -> main.py 参数
# ---------------------------------------------------------------------------
def build_args(p):
    a = [
        "--palette", p["palette"],
        "--label-style", p["label"],
        "--max-colors", str(p["max_colors"]),
        "--cell", str(p["cell"]),
        "--size", str(p["size"]),
        "--lang", "zh",  # 图例名称始终中文
    ]
    if p["coords"]:
        a.append("--coords")
    if not p["grid"]:
        a.append("--no-grid-lines")
    if p["bead"]:
        a.append("--bead-look")
    if p["dither"]:
        a.append("--dither")
    if p["title"]:
        a += ["--title", p["title"]]
    if p["width"]:
        a += ["--width", str(p["width"])]
    if p["height"]:
        a += ["--height", str(p["height"])]
    return a


def _params_from_fields(fields):
    def s(key, default=""):
        v = fields.get(key)
        return v if v is not None else default

    def b(key):
        return s(key, "0") == "1"

    def i(key, default=0):
        try:
            return int(s(key, str(default)))
        except (TypeError, ValueError):
            return default

    p = {
        "palette": s("palette", "mard"),
        "label": s("label", "brand"),
        "max_colors": i("max_colors", 24),
        "cell": i("cell", 30),
        "size": i("size", 200),
        "coords": b("coords"),
        "grid": b("grid"),
        "bead": b("bead"),
        "dither": b("dither"),
        "title": s("title", ""),
        "width": i("width", 0),
        "height": i("height", 0),
    }
    if p["palette"] not in PALETTES:
        p["palette"] = "mard"
    if p["label"] not in LABELS:
        p["label"] = "brand"
    if p["max_colors"] < 0:
        p["max_colors"] = 0
    if p["cell"] < 8:
        p["cell"] = 8
    if p["cell"] > 80:
        p["cell"] = 80
    if p["size"] <= 0:
        p["size"] = 200
    if p["width"] < 0:
        p["width"] = 0
    if p["height"] < 0:
        p["height"] = 0
    return p


# ---------------------------------------------------------------------------
# 转换（进程内调用 main.py，逐文件）
# ---------------------------------------------------------------------------
def _newest_matching_dir(base):
    """base 可能带 (1)(2)... 后缀，返回实际存在且最新的那个目录。"""
    parent = os.path.dirname(base)
    name = os.path.basename(base)
    if not os.path.isdir(parent):
        return base
    matches = [os.path.join(parent, x) for x in os.listdir(parent)
               if os.path.isdir(os.path.join(parent, x))
               and (x == name or x.startswith(name + " ("))]
    return max(matches, key=os.path.getmtime) if matches else base


def convert_one(image_path, p):
    stem = os.path.splitext(os.path.basename(image_path))[0]
    base = os.path.join(OUT_DIR, "%s_%s_%s" % (stem, p["palette"], p["max_colors"]))

    # 与 main.py 相同的“同名文件夹自动 + (1)(2)...”逻辑，预先确定输出目录
    # （必须先于 main() 计算，否则 main 创建完目录后再循环会误跳到下一编号）
    out_dir = base
    n = 0
    while os.path.isdir(out_dir):
        n += 1
        out_dir = "%s (%d)" % (base, n)

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = main_mod.main([image_path] + build_args(p))
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 1
    except Exception as e:  # noqa: BLE001
        buf.write("\n[内部错误] %s\n" % e)
        rc = 1
    log = buf.getvalue()
    if rc != 0:
        raise RuntimeError("转换失败（退出码 %s）：\n%s" % (rc, log.strip()))

    # 实际落盘目录（理论上 == out_dir；不一致时以实际存在者为准）
    real = out_dir if os.path.isdir(out_dir) else _newest_matching_dir(base)

    def latest(suffix):
        if not os.path.isdir(real):
            return None
        cands = [os.path.join(real, f) for f in os.listdir(real) if f.endswith(suffix)]
        return max(cands, key=os.path.getmtime) if cands else None

    def to_url(path):
        return "/output/" + os.path.relpath(path, OUT_DIR).replace("\\", "/")

    pattern = latest("_pattern.png")
    colors = latest("_colors.csv")
    grid = latest("_grid.csv")
    return {
        "input": os.path.basename(image_path),
        "outputs": {
            "pattern": to_url(pattern) if pattern else None,
            "colors_csv": to_url(colors) if colors else None,
            "grid_csv": to_url(grid) if grid else None,
            "dir": to_url(real) if os.path.isdir(real) else None,
            "dir_abs": real,
        },
        "log": log.strip(),
        "size": _image_size(pattern) if pattern else None,
    }


def _image_size(path):
    try:
        from PIL import Image
        with Image.open(path) as im:
            return "%d x %d px" % im.size
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# HTTP 服务器
# ---------------------------------------------------------------------------
def _safe_join(root, rel):
    root = os.path.abspath(root)
    p = os.path.abspath(os.path.join(root, rel))
    if p != root and not os.path.normcase(p).startswith(os.path.normcase(root) + os.sep):
        return None
    return p


class Handler(BaseHTTPRequestHandler):
    server_version = "BeadWebUI/1.0"

    def log_message(self, fmt, *args):  # 精简日志
        sys.stderr.write("[webui] %s\n" % (fmt % args))

    # -- 工具 -------------------------------------------------------------
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def _serve_file(self, path, ctype=None):
        if not path or not os.path.isfile(path):
            self._json(404, {"ok": False, "error": "文件不存在"})
            return
        ctype = ctype or (mimetypes.guess_type(path)[0] or "application/octet-stream")
        with open(path, "rb") as fh:
            data = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        return json.loads(raw) if raw else {}

    # -- GET --------------------------------------------------------------
    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path in ("/", "/index.html"):
            return self._serve_file(os.path.join(WEB_DIR, "index.html"),
                                    "text/html; charset=utf-8")
        if path.startswith("/output/"):
            target = _safe_join(OUT_DIR, path[len("/output/"):])
            if target and os.path.isdir(target):
                files = sorted(os.listdir(target))
                rows = "".join(
                    '<li><a href="%s">%s</a></li>' % (
                        "/output/" + os.path.relpath(os.path.join(target, f), OUT_DIR).replace("\\", "/"),
                        f,
                    )
                    for f in files
                )
                body = '<meta charset="utf-8"><h2>输出目录</h2><ul>%s</ul>' % rows
                return self._send(200, body, "text/html; charset=utf-8")
            return self._serve_file(target)
        if path == "/api/health":
            return self._json(200, {"ok": True})
        self._json(404, {"ok": False, "error": "not found"})

    # -- POST -------------------------------------------------------------
    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/convert":
            return self._handle_convert()
        if path == "/api/open":
            return self._handle_open()
        self._json(404, {"ok": False, "error": "not found"})

    def _handle_convert(self):
        try:
            fields, files = self._parse_multipart()
        except Exception as e:  # noqa: BLE001
            return self._json(400, {"ok": False, "error": "请求解析失败：%s" % e})
        if not files:
            return self._json(400, {"ok": False, "error": "没有上传任何图片"})
        p = _params_from_fields(fields)

        token = "%d_%d" % (int(time.time()), os.getpid())
        workdir = os.path.join(UPLOAD_DIR, token)
        os.makedirs(workdir, exist_ok=True)
        results, errors = [], []
        try:
            for f in files:
                fname = os.path.basename(f["name"]) or "image.png"
                dst = os.path.join(workdir, fname)
                n = 1
                stem, ext = os.path.splitext(fname)
                while os.path.exists(dst):
                    dst = os.path.join(workdir, "%s (%d)%s" % (stem, n, ext))
                    n += 1
                with open(dst, "wb") as fh:
                    fh.write(f["data"])
                try:
                    results.append(convert_one(dst, p))
                except Exception as e:  # noqa: BLE001
                    errors.append({"input": fname, "error": str(e)})
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

        return self._json(200, {"ok": True, "results": results, "errors": errors,
                                "params": {"palette": p["palette"], "max_colors": p["max_colors"]}})

    def _parse_multipart(self):
        from email import policy
        from email.parser import BytesParser

        ctype = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ctype:
            raise ValueError("需要 multipart/form-data 请求")
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        # email 解析依赖头里的 Content-Type（含 boundary），需拼回 body 才能识别为 multipart
        msg = BytesParser(policy=policy.default).parsebytes(
            b"Content-Type: " + ctype.encode("utf-8") + b"\r\n\r\n" + body
        )
        fields, files = {}, []
        for part in msg.iter_parts():
            if not part.get("Content-Disposition"):
                continue
            payload = part.get_payload(decode=True) or b""
            filename = part.get_filename()
            if filename:
                files.append({"name": filename, "data": payload})
            else:
                name = part.get_param("name", header="content-disposition")
                if name:
                    fields[name] = payload.decode("utf-8", "replace")
        return fields, files

    def _handle_open(self):
        try:
            data = self._read_json_body()
        except Exception:  # noqa: BLE001
            data = {}
        raw = (data.get("dir") or "").strip()
        # 兼容三种形式：URL 路径(/output/xxx) / 绝对路径 / 相对 OUT_DIR 的路径
        if raw.startswith("/output/"):
            target = _safe_join(OUT_DIR, raw[len("/output/"):])
        elif os.path.isabs(raw):
            target = os.path.abspath(raw)
            if target != OUT_DIR and not os.path.normcase(target).startswith(
                    os.path.normcase(OUT_DIR) + os.sep):
                target = None
        else:
            target = _safe_join(OUT_DIR, raw)
        if not target or not os.path.isdir(target):
            return self._json(400, {"ok": False, "error": "目录不存在"})
        if os.name == "nt":
            os.startfile(target)
        return self._json(200, {"ok": True})


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def main():
    global main_mod
    ap = argparse.ArgumentParser(description="拼豆图纸网页版")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT, help="端口（默认 %d）" % DEFAULT_PORT)
    ap.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = ap.parse_args()

    try:
        import main as main_mod  # 复用现有转换逻辑（需 numpy + Pillow）
    except Exception as e:  # noqa: BLE001
        print("无法导入转换模块：%s" % e)
        print("请先安装依赖: pip install -r requirements.txt")
        return 1

    httpd = None
    port = args.port
    for _ in range(20):
        try:
            httpd = ThreadingHTTPServer((HOST, port), Handler)
            break
        except OSError:
            port += 1
    if httpd is None:
        print("无法启动服务器（端口被占用）。")
        return 1

    url = "http://%s:%d/" % (HOST, port)
    print("=" * 52)
    print("  拼豆图纸 - 网页版已启动")
    print("  浏览器访问: %s" % url)
    print("  关闭本窗口或按 Ctrl+C 退出服务")
    print("=" * 52)
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
