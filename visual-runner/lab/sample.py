"""Server-owned loopback sample; no external resources, inputs or credentials."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlsplit

HTML = b'''<!doctype html><html lang="en"><meta charset="utf-8"><title>QA Lab sample</title>
<style>body{margin:0;background:#eef2ff;font:18px Arial;color:#172554}main{position:relative;width:800px;height:1100px;margin:0}h1{position:absolute;top:20px;left:40px}label{position:absolute;left:40px}input,select,button{position:absolute;left:40px;width:320px;height:44px;box-sizing:border-box;font:18px Arial}#name{top:130px}#qty{top:230px}#plan{top:330px}#total{position:absolute;top:410px;left:40px}button{top:900px;background:#4338ca;color:white;border:0}#confirmation{position:absolute;top:970px;left:40px}</style>
<main><h1>Controlled browser smoke check</h1><label style="top:100px" for="name">Synthetic name</label><input id="name" autocomplete="off">
<label style="top:200px" for="qty">Quantity</label><input id="qty" type="text" inputmode="numeric" value="1">
<label style="top:300px" for="plan">Plan</label><select id="plan"><option value="10">Basic ($10)</option><option value="20">Plus ($20)</option></select>
<p id="total">Total: $10</p><button id="confirm" type="button">Confirm synthetic order</button><p id="confirmation" aria-live="polite"></p></main>
<script>const n=document.getElementById('name'),q=document.getElementById('qty'),p=document.getElementById('plan');function total(){return Number(q.value)*Number(p.value)}function update(){document.getElementById('total').textContent='Total: $'+total()}q.oninput=update;p.onchange=update;document.getElementById('confirm').onclick=()=>{document.getElementById('confirmation').textContent='Confirmed: '+n.value+' / $'+total()}</script></html>'''


def serve():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            target = urlsplit(self.path)
            # Also serves as Chrome's mandatory deny-by-default forward proxy.
            # Only this process's own sample origin is accepted; never forwards traffic.
            if target.netloc and (target.scheme != 'http' or target.netloc != f'127.0.0.1:{self.server.server_port}'):
                self.send_error(403)
                return
            if target.path not in ('/', '/favicon.ico'):
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; form-action 'none'; connect-src 'none'; base-uri 'none'")
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(HTML if target.path == '/' else b'')

        def do_CONNECT(self):
            self.send_error(403)  # No HTTPS tunnels or external targets in M1A.

        def log_message(self, *_):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f'http://127.0.0.1:{server.server_port}/'
