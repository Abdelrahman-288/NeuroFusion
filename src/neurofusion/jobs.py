"""Persistent, single-worker local inference queue."""
import json
import sqlite3
import threading
import traceback
import uuid
import hashlib
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from neurofusion.input_quality import InputQualityError


def now():
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, root, predictor):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'jobs.sqlite3'
        self.predictor = predictor
        self.stop = threading.Event()
        self.wake = threading.Event()
        with self.connect() as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, task TEXT, filename TEXT, upload TEXT,
                status TEXT, created TEXT, updated TEXT, error TEXT)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS reviews (
                id TEXT PRIMARY KEY, job TEXT NOT NULL, created TEXT NOT NULL,
                reviewer TEXT NOT NULL, assessment TEXT NOT NULL, note TEXT NOT NULL,
                slice_index INTEGER, result_sha256 TEXT NOT NULL)''')
            conn.execute("UPDATE jobs SET status='interrupted', updated=?, error=? WHERE status='running'",
                         (now(), 'Server stopped during analysis. Submit the input again.'))
            # Preserve completed outputs from the earlier synchronous viewer.
            for path in (self.root / 'results').glob('*/result.json'):
                job = path.parent.name
                if len(job) != 32 or any(c not in '0123456789abcdef' for c in job):
                    continue
                try:
                    result = json.loads(path.read_text())
                    stamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
                    conn.execute('INSERT OR IGNORE INTO jobs VALUES (?,?,?,?,?,?,?,?)',
                                 (job, result['task'], 'Earlier local result', '', 'completed', stamp, stamp, None))
                except (ValueError, KeyError, OSError):
                    continue
        self.thread = None

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db, timeout=15)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def submit(self, body, task, filename, suffix):
        job = uuid.uuid4().hex
        upload = self.root / 'uploads' / (job + suffix)
        upload.parent.mkdir(exist_ok=True)
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            count = conn.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]
            if count >= 10:
                raise ValueError('Queue is full (10 active jobs). Try again after a job finishes.')
            upload.write_bytes(body)
            stamp = now()
            conn.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?)',
                         (job, task, filename.replace('\\', '/').split('/')[-1][:200], str(upload), 'queued', stamp, stamp, None))
        self.wake.set()
        return self.get(job)

    def get(self, job):
        with self.connect() as conn:
            row = conn.execute('SELECT id,task,filename,status,created,updated,error FROM jobs WHERE id=?', (job,)).fetchone()
        return dict(row) if row else None

    def history(self):
        with self.connect() as conn:
            return [dict(row) for row in conn.execute('SELECT id,task,filename,status,created,updated,error FROM jobs ORDER BY created DESC LIMIT 200')]

    def reviews(self, job):
        record = self.get(job)
        if not record or record['status'] != 'completed':
            raise ValueError('Reviews require a completed analysis')
        with self.connect() as conn:
            rows = conn.execute('SELECT * FROM reviews WHERE job=? ORDER BY rowid', (job,)).fetchall()
        return {'schema_version': 1, 'job': job, 'research_only': True,
                'reviewer_identity_verified': False, 'reviews': [dict(row) for row in rows]}

    def add_review(self, job, payload):
        self.reviews(job)
        if not isinstance(payload, dict):
            raise ValueError('Expected a review object')
        reviewer, note = payload.get('reviewer'), payload.get('note')
        assessment, index = payload.get('assessment'), payload.get('slice_index')
        if not isinstance(reviewer, str) or not 1 <= len(reviewer.strip()) <= 80:
            raise ValueError('Reviewer label must be 1 to 80 characters')
        if not isinstance(note, str) or not 1 <= len(note.strip()) <= 4000:
            raise ValueError('Note must be 1 to 4000 characters')
        if assessment not in ('reviewed', 'needs_attention', 'uncertain'):
            raise ValueError('Select a supported review assessment')
        raw = (self.root / 'results' / job / 'result.json').read_bytes()
        result = json.loads(raw)
        if index is not None and (type(index) is not int or not 0 <= index < len(result['views'])):
            raise ValueError('Slice must refer to an existing displayed image')
        entry = {'id': uuid.uuid4().hex, 'job': job, 'created': now(),
                 'reviewer': reviewer.strip(), 'assessment': assessment, 'note': note.strip(),
                 'slice_index': index, 'result_sha256': hashlib.sha256(raw).hexdigest()}
        with self.connect() as conn:
            conn.execute('INSERT INTO reviews VALUES (:id,:job,:created,:reviewer,:assessment,:note,:slice_index,:result_sha256)', entry)
        return entry

    def run_one(self):
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
            if row is None:
                return False
            conn.execute("UPDATE jobs SET status='running',updated=? WHERE id=?", (now(), row['id']))
        try:
            self.predictor.analyze(Path(row['upload']), row['task'], self.root / 'results' / row['id'])
            status, error = 'completed', None
        except InputQualityError as rejected:
            status, error = 'failed', str(rejected)
            quality = self.root / 'quality'
            quality.mkdir(exist_ok=True)
            (quality / (row['id'] + '.json')).write_text(json.dumps(rejected.report, indent=2), encoding='utf-8')
        except Exception:
            traceback.print_exc()
            status, error = 'failed', 'Analysis failed. Check the input format and local server log; submit again to retry.'
        with self.connect() as conn:
            conn.execute('UPDATE jobs SET status=?,updated=?,error=? WHERE id=?', (status, now(), error, row['id']))
        return True

    def start(self):
        def work():
            while not self.stop.is_set():
                self.wake.clear()
                if not self.run_one():
                    self.wake.wait(1)
        self.thread = threading.Thread(target=work, name='inference-worker', daemon=True)
        self.thread.start()

    def close(self):
        self.stop.set()
        self.wake.set()
        if self.thread:
            self.thread.join()
