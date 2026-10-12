"""Authenticated loopback collaborative review; bootstrap uses an interactive terminal."""
import argparse
import base64
import getpass
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from neurofusion.collaborative_review import Collaboration, ReviewConflict

PROJECT = Path(__file__).resolve().parents[1]
WEB = PROJECT / 'web' / 'collaboration'


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, status, value, kind='application/json'):
        body = json.dumps(value).encode() if isinstance(value, (dict, list)) else value
        self.send_response(status)
        for key, val in {'Content-Type': kind, 'Content-Length': str(len(body)),
                         'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                         'Content-Security-Policy': "default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
                         'Referrer-Policy': 'no-referrer'}.items():
            self.send_header(key, val)
        self.end_headers(); self.wfile.write(body)

    def dispatch(self, post=False):
        try:
            self.connection.settimeout(30)
            origin = 'http://127.0.0.1:' + str(self.server.server_port)
            if self.headers.get('Host') != origin[7:] or self.headers.get('Origin', origin) != origin:
                raise PermissionError('Use the local service address')
            if self.headers.get('Sec-Fetch-Site') == 'cross-site':
                raise PermissionError('Cross-site requests denied')
            parsed = urlparse(self.path); route = parsed.path
            query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            auth = self.headers.get('Authorization', '')
            token = auth[7:] if auth.startswith('Bearer ') else ''
            store = self.server.store
            if not post and route in ('/', '/app.js', '/style.css'):
                name, kind = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}[route]
                return self.send(200, (WEB/name).read_bytes(), kind)
            if post:
                if self.headers.get('Content-Type') != 'application/json' or self.headers.get('Transfer-Encoding'):
                    raise ValueError('JSON body required')
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 36*1024*1024: raise ValueError('Invalid body length')
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict): raise ValueError('Object required')
                if route == '/api/login': result = store.login(body['name'], body['password'])
                else:
                    with store.connection() as c: store.actor(c, token)
                    if route == '/api/logout': result = store.logout(token)
                    elif route == '/api/users': result = store.create_user(token, body['name'], body['password'], body['role'])
                    elif route == '/api/deactivate': result = store.deactivate(token, body['name'])
                    elif route == '/api/password': result = store.reset_password(token, body['name'], body['password'])
                    elif route == '/api/assign': result = store.assign(token, body['exam'], body['reviewers'])
                    elif route == '/api/select': result = store.import_selection(token,body['records'],body['protected_patients'],body['budget'],body['reviewers'],body.get('seed',42))
                    elif route == '/api/submit':
                        mask = base64.b64decode(body['mask'], validate=True) if body.get('mask') else None
                        result = store.submit(token, body['exam'], body, mask)
                    elif route == '/api/adjudicate': result = store.adjudicate(token, body['exam'], body['submission_ids'], body['decision'], body.get('chosen_id'), body['notes'])
                    elif route == '/api/export': result = store.export(token, body['exams'])
                    else: return self.send(404, {'error': 'Unknown route'})
                return self.send(200, result or {'ok': True})
            if route == '/api/dashboard': return self.send(200, store.dashboard(token))
            if route == '/api/audit': return self.send(200, store.audit(token))
            if route == '/api/selections': return self.send(200, store.selection_status(token))
            if route == '/api/details': return self.send(200, store.source_details(token, query['exam']))
            if route == '/api/source': return self.send(200, store.source_download(token, query['exam']), 'application/octet-stream')
            if route == '/api/slice': return self.send(200, store.source_slice(token, query['exam'], int(query['axis']), int(query['index']), query.get('overlay') == 'true'), 'image/png')
            if route == '/api/annotation-slice': return self.send(200, store.annotation_slice(token, int(query['id']), int(query['axis']), int(query['index'])), 'image/png')
            if route == '/api/annotation': return self.send(200, store.annotation(token, int(query['id']))[1], 'application/octet-stream')
            if route == '/api/export': return self.send(200, store.download_export(token, query['id']), 'application/zip')
            self.send(404, {'error': 'Unknown route'})
        except PermissionError as exc: self.send(403, {'error': str(exc)})
        except ReviewConflict as exc: self.send(409, {'error': str(exc)})
        except (ValueError, KeyError, TypeError, OSError, EOFError) as exc: self.send(400, {'error': str(exc)[:250]})
        except Exception: self.send(500, {'error': 'Request failed; check input and local storage'})

    def do_GET(self): self.dispatch()
    def do_POST(self): self.dispatch(True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acquisition', type=Path, default=PROJECT/'experiments/ucsf-acquisition-001')
    parser.add_argument('--storage', type=Path, default=PROJECT/'data/collaborative-review')
    parser.add_argument('--port', type=int, default=8780)
    parser.add_argument('--bootstrap', action='store_true')
    parser.add_argument('--development-partitions',type=Path,help='Trusted server-side training allowlist; omit for protected review cohorts')
    args = parser.parse_args(); store = Collaboration(args.acquisition, args.storage,args.development_partitions)
    if args.bootstrap:
        name = input('First administrator username: ').strip()
        password = getpass.getpass('Password (12–128 characters): ')
        if password != getpass.getpass('Repeat password: '): raise SystemExit('Passwords differ')
        store.bootstrap(name, password); print('Administrator created. Run again without --bootstrap.'); return
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler); server.store = store
    print(f'Collaborative review: http://127.0.0.1:{args.port}/', flush=True)
    server.serve_forever()


if __name__ == '__main__': main()

