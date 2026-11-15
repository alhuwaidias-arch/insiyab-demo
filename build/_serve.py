# -*- coding: utf-8 -*-
"""خادم معاينة محلي يدعم Range (لأن python -m http.server لا يدعمه ⇒ مشغّل الفيديو لا يقلع).
الاستخدام: python _serve.py [port]   (الجذر = مجلد demo)"""
import os, re, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.basename(ROOT) == 'build':
    ROOT = os.path.dirname(ROOT)


class H(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    extensions_map = dict(SimpleHTTPRequestHandler.extensions_map,
                          **{'.mp4': 'video/mp4', '.json': 'application/json; charset=utf-8',
                             '.js': 'text/javascript; charset=utf-8'})

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def send_head(self):
        rng = self.headers.get('Range')
        if not rng:
            return super().send_head()
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return super().send_head()
        size = os.path.getsize(path)
        m = re.match(r'bytes=(\d*)-(\d*)$', rng.strip())
        if not m:
            return super().send_head()
        a, b = m.group(1), m.group(2)
        start = int(a) if a else max(0, size - int(b or 0))
        end = int(b) if (a and b) else size - 1
        if start >= size:
            self.send_error(416)
            return None
        end = min(end, size - 1)
        n = end - start + 1
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404)
            return None
        f.seek(start)
        self.send_response(206)
        ctype = self.guess_type(path)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, size))
        self.send_header('Content-Length', str(n))
        self.end_headers()
        return _Slice(f, n)


class _Slice:
    def __init__(self, f, n):
        self.f, self.n = f, n

    def read(self, k=-1):
        if self.n <= 0:
            return b''
        k = self.n if k < 0 else min(k, self.n)
        b = self.f.read(k)
        self.n -= len(b)
        return b

    def close(self):
        self.f.close()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8848
    print('serving %s on http://127.0.0.1:%d' % (ROOT, port), flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()
