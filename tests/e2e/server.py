"""
High-fidelity Cloudflare Edge Worker, D1 Database, and BROADCAST_KV emulator
for hermetic End-to-End (E2E) testing of ani-cli-arabic telemetry & backend.
"""

import http.server
import json
import os
import sqlite3
import sys
import threading
import time
import urllib.parse
from datetime import datetime, timezone
import hashlib

SALT = "anicliar_secure_salt_2026"
EXPECTED_HASH = "292f89492aaca8223bd07e55de97c1b843b1ef08999ee6f83c9b92ac0e5c979e"
TEST_ADMIN_PASSWORD = "anicli_admin_pass_2026"
SESSION_TTL = 7 * 24 * 3600


class EmulatorKV:
    """In-memory Cloudflare KV simulator with TTL support."""

    def __init__(self):
        self._lock = threading.Lock()
        self._store = {}  # key -> {"val": str, "exp": float or None}

    def get(self, key, as_json=False):
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            if item["exp"] is not None and time.time() > item["exp"]:
                del self._store[key]
                return None
            val = item["val"]
            if as_json:
                try:
                    return json.loads(val)
                except Exception:
                    return None
            return val

    def put(self, key, val, expiration_ttl=None):
        with self._lock:
            if isinstance(val, (dict, list)):
                val_str = json.dumps(val)
            else:
                val_str = str(val)
            exp = (time.time() + expiration_ttl) if expiration_ttl else None
            self._store[key] = {"val": val_str, "exp": exp}

    def delete(self, key):
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        with self._lock:
            self._store.clear()


class EmulatorDB:
    """Thread-safe SQLite simulator for Cloudflare D1 with schema identical to production."""

    def __init__(self, db_path=":memory:"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            cursor = self._conn.cursor()
            # 1. v2_watch_history
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS v2_watch_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT NOT NULL,
                    anime_title TEXT NOT NULL,
                    episode TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    duration INTEGER DEFAULT 0,
                    os_name TEXT NOT NULL,
                    distro TEXT,
                    base TEXT,
                    os_version TEXT,
                    client_version TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_v2_watch_fingerprint ON v2_watch_history(fingerprint);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_v2_watch_created_at ON v2_watch_history(created_at);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_v2_watch_anime_title ON v2_watch_history(anime_title);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_v2_watch_provider ON v2_watch_history(provider);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_v2_watch_mode ON v2_watch_history(mode);")

            # 2. v2_launches
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS v2_launches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT NOT NULL,
                    os_name TEXT NOT NULL,
                    distro TEXT,
                    base TEXT,
                    os_version TEXT,
                    python_version TEXT NOT NULL,
                    client_version TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_v2_launches_fingerprint ON v2_launches(fingerprint);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_v2_launches_created_at ON v2_launches(created_at);")

            # 3. v2_crashes
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS v2_crashes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    message TEXT,
                    traceback TEXT NOT NULL,
                    os_name TEXT NOT NULL,
                    distro TEXT,
                    base TEXT,
                    os_version TEXT,
                    client_version TEXT NOT NULL,
                    command_args TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_v2_crashes_fingerprint ON v2_crashes(fingerprint);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_v2_crashes_created_at ON v2_crashes(created_at);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_v2_crashes_error_type ON v2_crashes(error_type);")

            # 4. legacy monitoring_events
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS monitoring_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fingerprint ON monitoring_events(fingerprint);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_action ON monitoring_events(action);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_action_created ON monitoring_events(action, created_at);")

            self._conn.commit()

    def execute(self, sql, params=()):
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            self._conn.commit()
            return cur

    def fetchall(self, sql, params=()):
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def fetchone(self, sql, params=()):
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def close(self):
        with self._lock:
            self._conn.close()


class EdgeWorkerEmulatorHandler(http.server.BaseHTTPRequestHandler):
    """HTTP Request Handler implementing all Edge Worker API contracts."""

    # Shared class-level database & KV emulator instances
    db: EmulatorDB = None
    kv: EmulatorKV = None
    d1_quota_exhausted: bool = False
    d1_circuit_breaker: bool = False

    def log_message(self, format, *args):
        # Silence default request logging to keep runner output clean
        pass

    def _send_cors_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Auth-Key, User-Agent")
        if content_type:
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")

    def _extract_token(self):
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:].strip()
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("anicli_session="):
                return part[len("anicli_session="):].strip()
        return None

    def _is_authenticated(self):
        token = self._extract_token()
        if not token:
            return False
        session = self.kv.get(f"session:{token}", as_json=True)
        return session is not None

    def do_OPTIONS(self):
        self._send_cors_headers(204, content_type=None)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. /health
        if path == "/health" or path == "/api/health":
            self._send_cors_headers(200)
            self.end_headers()
            resp = {
                "status": "ok",
                "version": "2.0.0",
                "d1": "limited" if self.d1_quota_exhausted else "operational",
                "kv": "operational",
                "worker": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        # 2. /broadcast.json & /api/public/broadcast
        if path in ("/broadcast.json", "/api/public/broadcast"):
            data = self.kv.get("active_broadcast", as_json=True) or {
                "id": "broadcast-v2-live",
                "active": False,
                "type": "popup",
                "title": "",
                "message": "",
                "link": "",
                "style": "green"
            }
            # Content negotiation based on User-Agent
            ua = self.headers.get("User-Agent", "")
            is_legacy = "2.0" not in ua
            out = dict(data)
            if data.get("type") == "both":
                out["type"] = "banner" if is_legacy else "popup"
            elif is_legacy and data.get("type") == "popup":
                # For pure legacy clients, popup converts to banner
                out["type"] = "banner"

            self._send_cors_headers(200)
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0")
            self.end_headers()
            self.wfile.write(json.dumps(out, indent=2).encode("utf-8"))
            return

        # 3. /changelog.json & /api/public/changelog
        if path in ("/changelog.json", "/api/public/changelog"):
            data = self.kv.get("active_changelog", as_json=True) or {
                "active": False,
                "title": "What's New in {version}",
                "body": "",
                "outdated_notice": "YOUR VERSION {version} IS OUTDATED! PLEASE UPDATE TO {latest_version}.",
                "latest_version": "2.0.0"
            }
            self._send_cors_headers(200)
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0")
            self.end_headers()
            self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))
            return

        # 4. /api/auth/session
        if path == "/api/auth/session":
            is_auth = self._is_authenticated()
            self._send_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps({"authenticated": is_auth}).encode("utf-8"))
            return

        # 5. /api/broadcast (Admin GET)
        if path == "/api/broadcast":
            data = self.kv.get("active_broadcast", as_json=True)
            self._send_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # 6. /api/changelog (Admin GET)
        if path == "/api/changelog":
            data = self.kv.get("active_changelog", as_json=True)
            self._send_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # 7. /api/stats (Guarded by 15-min KV cache & D1 quota guard)
        if path == "/api/stats":
            range_val = query.get("range", ["all"])[0]
            period_val = query.get("launchesPeriod", ["all"])[0]
            cache_key = f"stats_cache:{range_val}:{period_val}"

            # Check KV Cache first
            cached = self.kv.get(cache_key, as_json=True)
            if cached and not self.d1_quota_exhausted:
                self._send_cors_headers(200)
                self.send_header("X-Cache", "HIT")
                self.end_headers()
                self.wfile.write(json.dumps(cached).encode("utf-8"))
                return

            # If D1 quota exhausted, return emergency snapshot
            if self.d1_quota_exhausted or self.d1_circuit_breaker:
                snap = self.kv.get("d1_last_real_snapshot", as_json=True) or {
                    "kpis": {"totalUsers": 12, "newToday": 1, "dau": 4, "appLaunches": 45, "totalStreams": 30, "totalHours": 14.5},
                    "growth": [],
                    "providers": [],
                    "versions": [],
                    "topAnime": [],
                    "osDistribution": []
                }
                snap["d1_limited"] = True
                snap["is_snapshot"] = True
                snap["message"] = "Cloudflare D1 daily free tier read limit reached (5M rows/day). Displaying verified real database snapshot."
                self._send_cors_headers(200)
                self.send_header("X-Cache", "SNAPSHOT")
                self.end_headers()
                self.wfile.write(json.dumps(snap).encode("utf-8"))
                return

            # Compute stats from D1 SQLite
            try:
                total_launches = self.db.fetchone("SELECT COUNT(*) as c FROM v2_launches")["c"]
                total_watches = self.db.fetchone("SELECT COUNT(*) as c FROM v2_watch_history")["c"]
                legacy_streams = self.db.fetchone("SELECT COUNT(*) as c FROM monitoring_events WHERE action='video_play'")["c"]
                legacy_launches = self.db.fetchone("SELECT COUNT(*) as c FROM monitoring_events WHERE action='app_start'")["c"]
                total_streams = total_watches + legacy_streams

                # Total unique users across launches, watches, and legacy
                users_row = self.db.fetchone(
                    """
                    SELECT COUNT(DISTINCT fingerprint) as c FROM (
                        SELECT fingerprint FROM v2_launches
                        UNION
                        SELECT fingerprint FROM v2_watch_history
                        UNION
                        SELECT fingerprint FROM monitoring_events
                    )
                    """
                )
                total_users = users_row["c"] if users_row else 0

                # Duration sum
                dur_row = self.db.fetchone("SELECT SUM(duration) as s FROM v2_watch_history")
                total_hours = round((dur_row["s"] or 0) / 3600.0, 1)

                # Provider breakdown
                providers = self.db.fetchall(
                    """
                    SELECT provider, COUNT(*) as cnt FROM (
                        SELECT provider FROM v2_watch_history
                        UNION ALL
                        SELECT json_extract(details, '$.provider') as provider FROM monitoring_events WHERE action='video_play'
                    )
                    WHERE provider IS NOT NULL AND provider != ''
                    GROUP BY provider
                    ORDER BY cnt DESC
                    """
                )
                total_p = sum(p["cnt"] for p in providers) or 1
                prov_list = [{"name": p["provider"], "streams": p["cnt"], "share": round(p["cnt"] / total_p * 100, 1)} for p in providers]

                # Top anime
                top_anime_rows = self.db.fetchall(
                    """
                    SELECT anime_title, COUNT(*) as views FROM v2_watch_history
                    GROUP BY anime_title
                    ORDER BY views DESC
                    LIMIT 20
                    """
                )
                top_anime = [{"title": r["anime_title"], "views": r["views"], "share": round(r["views"] / (total_watches or 1) * 100, 1)} for r in top_anime_rows]

                # OS distribution
                os_rows = self.db.fetchall(
                    """
                    SELECT os_name, distro, base, COUNT(*) as cnt FROM v2_launches
                    GROUP BY os_name, distro
                    ORDER BY cnt DESC
                    """
                )
                total_os = sum(r["cnt"] for r in os_rows) or 1
                os_dist = [{"name": r["distro"] or r["os_name"], "base": r["base"], "count": r["cnt"], "share": round(r["cnt"] / total_os * 100, 1)} for r in os_rows]

                # Version breakdown
                ver_rows = self.db.fetchall(
                    """
                    SELECT client_version, COUNT(*) as cnt FROM v2_launches
                    GROUP BY client_version
                    ORDER BY cnt DESC
                    """
                )
                versions = [{"version": r["client_version"], "count": r["cnt"], "percentage": round(r["cnt"] / (total_launches or 1) * 100, 1)} for r in ver_rows]

                # Time series growth
                growth = [
                    {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "users": total_users, "streams": total_streams, "launches": total_launches + legacy_launches}
                ]

                stats_data = {
                    "d1_limited": False,
                    "kpis": {
                        "totalUsers": total_users,
                        "newToday": min(total_users, 2),
                        "dau": total_users,
                        "appLaunches": total_launches + legacy_launches,
                        "totalStreams": total_streams,
                        "totalHours": total_hours
                    },
                    "growth": growth,
                    "providers": prov_list,
                    "versions": versions,
                    "topAnime": top_anime,
                    "osDistribution": os_dist
                }

                # Save to 15-min KV Cache & persist emergency snapshot
                self.kv.put(cache_key, stats_data, expiration_ttl=900)
                self.kv.put("d1_last_real_snapshot", stats_data)

                self._send_cors_headers(200)
                self.send_header("X-Cache", "MISS")
                self.end_headers()
                self.wfile.write(json.dumps(stats_data).encode("utf-8"))
                return
            except Exception as e:
                self._send_cors_headers(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        # 8. /api/users (User Directory)
        if path == "/api/users":
            page = max(1, int(query.get("page", ["1"])[0]))
            limit = min(100, max(1, int(query.get("limit", ["50"])[0])))
            search = query.get("search", [""])[0].strip()
            distro_filter = query.get("distro", [""])[0].strip()
            offset = (page - 1) * limit

            where_clauses = ["1=1"]
            params = []
            if search:
                where_clauses.append("(fingerprint LIKE ?)")
                params.append(f"%{search}%")
            if distro_filter:
                where_clauses.append("(distro LIKE ?)")
                params.append(f"%{distro_filter}%")

            where_sql = " AND ".join(where_clauses)
            sql = f"""
                SELECT fingerprint, os_name, distro, base, os_version, client_version,
                       COUNT(*) as total_launches, MAX(created_at) as last_seen, MIN(created_at) as first_seen
                FROM v2_launches
                WHERE {where_sql}
                GROUP BY fingerprint
                ORDER BY last_seen DESC
                LIMIT ? OFFSET ?
            """
            rows = self.db.fetchall(sql, params + [limit, offset])

            count_sql = f"SELECT COUNT(DISTINCT fingerprint) as c FROM v2_launches WHERE {where_sql}"
            total = self.db.fetchone(count_sql, params)["c"]

            self._send_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps({
                "users": rows,
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit if limit else 1
            }).encode("utf-8"))
            return

        # 9. /api/user (Full User Dossier)
        if path == "/api/user":
            fp = query.get("fingerprint", [""])[0].strip()
            if not fp:
                self._send_cors_headers(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Fingerprint required"}).encode("utf-8"))
                return

            if self.d1_quota_exhausted:
                self._send_cors_headers(200)
                self.end_headers()
                self.wfile.write(json.dumps({
                    "d1_limited": True,
                    "message": "Database queries paused by Cloudflare quota guard.",
                    "fingerprint": fp,
                    "summary": None,
                    "history": [],
                    "crashes": []
                }).encode("utf-8"))
                return

            summary = self.db.fetchone(
                """
                SELECT fingerprint, os_name, distro, base, os_version, client_version,
                       COUNT(*) as total_launches, MIN(created_at) as first_seen, MAX(created_at) as last_seen
                FROM v2_launches
                WHERE fingerprint = ?
                """,
                (fp,)
            )
            if summary and not summary.get("fingerprint"):
                summary = None

            history = self.db.fetchall(
                """
                SELECT anime_title, episode, provider, mode, duration, created_at
                FROM v2_watch_history
                WHERE fingerprint = ?
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (fp,)
            )

            crashes = self.db.fetchall(
                """
                SELECT error_type, message, traceback, created_at
                FROM v2_crashes
                WHERE fingerprint = ?
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (fp,)
            )

            self._send_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps({
                "d1_limited": False,
                "fingerprint": fp,
                "summary": summary,
                "history": history,
                "crashes": crashes
            }).encode("utf-8"))
            return

        # 10. /api/crashes (Crash Diagnostics Feed)
        if path == "/api/crashes":
            page = max(1, int(query.get("page", ["1"])[0]))
            limit = min(100, max(1, int(query.get("limit", ["50"])[0])))
            type_filter = query.get("type", [""])[0].strip()
            search = query.get("search", [""])[0].strip()
            offset = (page - 1) * limit

            if self.d1_quota_exhausted:
                # Fallback to KV recent_crashes
                recent = self.kv.get("recent_crashes", as_json=True) or []
                filtered = [c for c in recent if (not type_filter or c.get("error_type") == type_filter)]
                paginated = filtered[offset: offset + limit]
                self._send_cors_headers(200)
                self.end_headers()
                self.wfile.write(json.dumps({
                    "crashes": paginated,
                    "total": len(filtered),
                    "page": page,
                    "pages": (len(filtered) + limit - 1) // limit if limit else 1,
                    "d1_limited": True,
                    "source": "kv_buffer"
                }).encode("utf-8"))
                return

            where_clauses = ["1=1"]
            params = []
            if type_filter:
                where_clauses.append("error_type = ?")
                params.append(type_filter)
            if search:
                where_clauses.append("(message LIKE ? OR traceback LIKE ? OR fingerprint LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

            where_sql = " AND ".join(where_clauses)
            crashes = self.db.fetchall(
                f"""
                SELECT id, fingerprint, error_type, message, traceback, os_name, distro, base,
                       os_version, client_version, command_args, created_at
                FROM v2_crashes
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset]
            )
            total = self.db.fetchone(f"SELECT COUNT(*) as c FROM v2_crashes WHERE {where_sql}", params)["c"]

            self._send_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps({
                "crashes": crashes,
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit if limit else 1
            }).encode("utf-8"))
            return

        # 11. /api/events (Unified Telemetry Feed)
        if path == "/api/events":
            page = max(1, int(query.get("page", ["1"])[0]))
            limit = min(100, max(1, int(query.get("limit", ["50"])[0])))
            action_filter = query.get("action", [""])[0].strip()
            offset = (page - 1) * limit

            where_sql = "WHERE action = ?" if action_filter else ""
            params = [action_filter] if action_filter else []

            rows = self.db.fetchall(
                f"""
                SELECT id, fingerprint, timestamp, action, details, created_at
                FROM monitoring_events
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset]
            )
            total = self.db.fetchone(f"SELECT COUNT(*) as c FROM monitoring_events {where_sql}", params)["c"]

            self._send_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps({
                "events": rows,
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit if limit else 1
            }).encode("utf-8"))
            return

        # 12. /api/legacy (Legacy DB Explorer)
        if path == "/api/legacy":
            page = max(1, int(query.get("page", ["1"])[0]))
            limit = min(100, max(1, int(query.get("limit", ["50"])[0])))
            action_filter = query.get("action", [""])[0].strip()
            search = query.get("search", [""])[0].strip()
            offset = (page - 1) * limit

            where_clauses = ["1=1"]
            params = []
            if action_filter:
                where_clauses.append("action = ?")
                params.append(action_filter)
            if search:
                where_clauses.append("(fingerprint LIKE ? OR details LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%"])

            where_sql = " AND ".join(where_clauses)
            rows = self.db.fetchall(
                f"""
                SELECT id, fingerprint, timestamp, action, details, created_at
                FROM monitoring_events
                WHERE {where_sql}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset]
            )
            total = self.db.fetchone(f"SELECT COUNT(*) as c FROM monitoring_events WHERE {where_sql}", params)["c"]

            self._send_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps({
                "rows": rows,
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit if limit else 1
            }).encode("utf-8"))
            return

        # 13. Test Control Endpoints
        if path == "/test/set_quota_limit":
            enabled = query.get("enabled", ["1"])[0] in ("1", "true")
            EdgeWorkerEmulatorHandler.d1_quota_exhausted = enabled
            EdgeWorkerEmulatorHandler.d1_circuit_breaker = enabled
            self._send_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "d1_quota_exhausted": enabled}).encode("utf-8"))
            return

        if path == "/test/reset":
            EdgeWorkerEmulatorHandler.d1_quota_exhausted = False
            EdgeWorkerEmulatorHandler.d1_circuit_breaker = False
            self.kv.clear()
            self.db.execute("DELETE FROM v2_watch_history")
            self.db.execute("DELETE FROM v2_launches")
            self.db.execute("DELETE FROM v2_crashes")
            self._send_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            return

        # 404 Fallback
        self._send_cors_headers(404)
        self.end_headers()
        self.wfile.write(json.dumps({"error": f"Endpoint not found: {path}"}).encode("utf-8"))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b""

        try:
            body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception as e:
            self._send_cors_headers(400)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Malformed JSON syntax", "details": str(e)}).encode("utf-8"))
            return

        # 1. /api/v2/telemetry (Launch and Watch Events)
        if path == "/api/v2/telemetry":
            event_type = body.get("event_type")
            fingerprint = body.get("fingerprint")

            if not fingerprint:
                self._send_cors_headers(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing required field: fingerprint"}).encode("utf-8"))
                return

            if event_type == "launch":
                self.db.execute(
                    """
                    INSERT INTO v2_launches (fingerprint, os_name, distro, base, os_version, python_version, client_version, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fingerprint,
                        body.get("os_name", "Unknown"),
                        body.get("distro", "Unknown"),
                        body.get("base", "Unknown"),
                        body.get("os_version", "Unknown"),
                        body.get("python_version", "Unknown"),
                        body.get("client_version", "v2.0.0"),
                        body.get("created_at", datetime.now(timezone.utc).isoformat())
                    )
                )
                self._send_cors_headers(200)
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "event": "launch"}).encode("utf-8"))
                return

            elif event_type == "watch":
                anime_title = body.get("anime_title")
                if not anime_title:
                    self._send_cors_headers(400)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Missing required field: anime_title"}).encode("utf-8"))
                    return

                self.db.execute(
                    """
                    INSERT INTO v2_watch_history (fingerprint, anime_title, episode, provider, mode, duration, os_name, distro, base, os_version, client_version, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fingerprint,
                        anime_title,
                        str(body.get("episode", "1")),
                        body.get("provider", "Animeify"),
                        body.get("mode", "stream"),
                        int(body.get("duration", 0)),
                        body.get("os_name", "Unknown"),
                        body.get("distro", "Unknown"),
                        body.get("base", "Unknown"),
                        body.get("os_version", "Unknown"),
                        body.get("client_version", "v2.0.0"),
                        body.get("created_at", datetime.now(timezone.utc).isoformat())
                    )
                )
                self._send_cors_headers(200)
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "event": "watch"}).encode("utf-8"))
                return

            else:
                self._send_cors_headers(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid or missing event_type: {event_type}"}).encode("utf-8"))
                return

        # 2. /api/v2/crash (Structured Crash Diagnostics Ingestion)
        if path == "/api/v2/crash":
            fingerprint = body.get("fingerprint")
            error_type = body.get("error_type")
            traceback_str = body.get("traceback")

            if not fingerprint or not error_type or not traceback_str:
                self._send_cors_headers(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing required fields (fingerprint, error_type, traceback)"}).encode("utf-8"))
                return

            cmd_args = body.get("command_args")
            cmd_args_str = json.dumps(cmd_args) if isinstance(cmd_args, (list, dict)) else str(cmd_args or "")
            ts = body.get("created_at", datetime.now(timezone.utc).isoformat())

            # Insert into D1
            cur = self.db.execute(
                """
                INSERT INTO v2_crashes (fingerprint, error_type, message, traceback, os_name, distro, base, os_version, client_version, command_args, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fingerprint,
                    error_type,
                    body.get("message", ""),
                    traceback_str,
                    body.get("os_name", "Unknown"),
                    body.get("distro", "Unknown"),
                    body.get("base", "Unknown"),
                    body.get("os_version", "Unknown"),
                    body.get("client_version", "v2.0.0"),
                    cmd_args_str,
                    ts
                )
            )
            insert_id = cur.lastrowid

            # Prepend to KV recent_crashes (capped at 50)
            recent = self.kv.get("recent_crashes", as_json=True) or []
            recent.insert(0, {
                "id": insert_id,
                "timestamp": ts,
                "fingerprint": fingerprint,
                "error_type": error_type,
                "message": body.get("message", ""),
                "traceback": traceback_str,
                "os_name": body.get("os_name", "Unknown"),
                "distro": body.get("distro", "Unknown"),
                "client_version": body.get("client_version", "v2.0.0"),
                "command_args": cmd_args
            })
            if len(recent) > 50:
                recent = recent[:50]
            self.kv.put("recent_crashes", recent)

            self._send_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "id": insert_id}).encode("utf-8"))
            return

        # 3. /monitor (Legacy Ingestion Fallback)
        if path == "/monitor":
            fingerprint = (body.get("fingerprint") or body.get("client_id") or body.get("user_id") or "").strip()
            action = body.get("action", "video_play")
            ts = body.get("timestamp", datetime.now(timezone.utc).isoformat())

            if not fingerprint:
                self._send_cors_headers(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing required fingerprint or client_id"}).encode("utf-8"))
                return

            det_obj = body.get("details", {})
            if not isinstance(det_obj, dict):
                det_obj = {}

            # Backward compatibility rules
            if action == "video_play" and not det_obj.get("provider"):
                det_obj["provider"] = "Animeify"
            if det_obj.get("os") == "Darwin":
                det_obj["os"] = "macOS"

            det_str = json.dumps(det_obj)
            # Insert into legacy monitoring_events
            self.db.execute(
                "INSERT INTO monitoring_events (fingerprint, timestamp, action, details) VALUES (?, ?, ?, ?)",
                (fingerprint, ts, action, det_str)
            )

            # Map legacy to v2 tables
            if action == "app_start":
                self.db.execute(
                    """
                    INSERT INTO v2_launches (fingerprint, os_name, distro, base, os_version, python_version, client_version, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (fingerprint, det_obj.get("os", "Linux"), det_obj.get("os", "Linux"), "Legacy", "unknown", "unknown", det_obj.get("version", "v1.8"), ts)
                )
            elif action == "video_play":
                self.db.execute(
                    """
                    INSERT INTO v2_watch_history (fingerprint, anime_title, episode, provider, mode, duration, os_name, distro, base, os_version, client_version, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (fingerprint, det_obj.get("anime", "Unknown"), str(det_obj.get("episode", "1")), det_obj.get("provider", "Animeify"), det_obj.get("mode", "stream"), int(det_obj.get("duration", 0)), det_obj.get("os", "Linux"), "Unknown", "Legacy", "unknown", det_obj.get("version", "v1.8"), ts)
                )
            elif action in ("error_crash", "crash"):
                self.db.execute(
                    """
                    INSERT INTO v2_crashes (fingerprint, error_type, message, traceback, os_name, distro, base, os_version, client_version, command_args, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (fingerprint, det_obj.get("error_type", "Exception"), det_obj.get("message", ""), det_obj.get("traceback", ""), det_obj.get("os", "Linux"), "Unknown", "Legacy", "unknown", det_obj.get("version", "v1.8"), json.dumps(det_obj.get("args", [])), ts)
                )

            self._send_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            return

        # 4. /watch (Legacy v1.7/v1.8 Runtime Optimizer Ingestion)
        if path == "/watch":
            user_id = body.get("user_id")
            anime_title = body.get("anime_title", "Unknown Anime")
            episode_num = str(body.get("episode_num", "1"))
            ts = datetime.now(timezone.utc).isoformat()

            if user_id:
                fp = user_id[:16]
                det_str = json.dumps({
                    "anime": anime_title,
                    "episode": episode_num,
                    "mode": "stream",
                    "provider": "Animeify"
                })
                self.db.execute(
                    "INSERT INTO monitoring_events (fingerprint, timestamp, action, details) VALUES (?, ?, ?, ?)",
                    (fp, ts, "video_play", det_str)
                )
                self.db.execute(
                    """
                    INSERT INTO v2_watch_history (fingerprint, anime_title, episode, provider, mode, duration, os_name, distro, base, os_version, client_version, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (fp, anime_title, episode_num, "Animeify", "stream", 0, "Linux", "Unknown", "Legacy", "unknown", "v1.8", ts)
                )

            self._send_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            return

        # 5. /api/auth/login
        if path == "/api/auth/login":
            pwd = (body.get("password") or "").strip()
            h = hashlib.sha256((SALT + pwd).encode("utf-8")).hexdigest()

            # Accept if hash matches EXPECTED_HASH or matches test password
            if h == EXPECTED_HASH or pwd == TEST_ADMIN_PASSWORD or pwd == "admin":
                token = hashlib.sha256(f"{pwd}:{time.time()}:{os.urandom(16)}".encode("utf-8")).hexdigest()
                self.kv.put(f"session:{token}", {"created_at": time.time()}, expiration_ttl=SESSION_TTL)

                self._send_cors_headers(200)
                self.send_header("Set-Cookie", f"anicli_session={token}; Path=/; Max-Age={SESSION_TTL}; SameSite=Lax; Secure")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "token": token}).encode("utf-8"))
                return
            else:
                self._send_cors_headers(401)
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Incorrect security credentials."}).encode("utf-8"))
                return

        # 6. /api/auth/logout
        if path == "/api/auth/logout":
            token = self._extract_token()
            if token:
                self.kv.delete(f"session:{token}")
            self._send_cors_headers(200)
            self.send_header("Set-Cookie", "anicli_session=; Path=/; Max-Age=0; SameSite=Lax; Secure")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            return

        # 7. /api/broadcast (Admin POST)
        if path == "/api/broadcast":
            if not self._is_authenticated():
                self._send_cors_headers(401)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Unauthorized"}).encode("utf-8"))
                return

            body["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.kv.put("active_broadcast", body)
            self._send_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "broadcast": body}).encode("utf-8"))
            return

        # 8. /api/changelog (Admin POST)
        if path == "/api/changelog":
            if not self._is_authenticated():
                self._send_cors_headers(401)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Unauthorized"}).encode("utf-8"))
                return

            body["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.kv.put("active_changelog", body)
            self._send_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "changelog": body}).encode("utf-8"))
            return

        # 404 Fallback
        self._send_cors_headers(404)
        self.end_headers()
        self.wfile.write(json.dumps({"error": f"Endpoint not found: {path}"}).encode("utf-8"))


class EdgeWorkerEmulatorServer:
    """Server manager for running the Edge Worker emulator."""

    def __init__(self, host="127.0.0.1", port=0):
        self.host = host
        self.port = port
        self.db = EmulatorDB()
        self.kv = EmulatorKV()

        # Wire handlers
        EdgeWorkerEmulatorHandler.db = self.db
        EdgeWorkerEmulatorHandler.kv = self.kv
        EdgeWorkerEmulatorHandler.d1_quota_exhausted = False
        EdgeWorkerEmulatorHandler.d1_circuit_breaker = False

        self._seed_sample_data()

        # Threading HTTP server
        from http.server import ThreadingHTTPServer
        self.server = ThreadingHTTPServer((self.host, self.port), EdgeWorkerEmulatorHandler)
        self.actual_port = self.server.server_address[1]
        self.base_url = f"http://{self.host}:{self.actual_port}"
        self._thread = None

    def _seed_sample_data(self):
        """Seed baseline historical data in monitoring_events for realistic test queries."""
        for i in range(1, 21):
            ts = datetime.now(timezone.utc).isoformat()
            fp = f"legacy_user_{i:04d}"
            det = json.dumps({
                "anime": f"Legacy Anime {i}",
                "episode": str(i % 12 + 1),
                "mode": "stream",
                "provider": "Animeify",
                "os": "Linux (Arch)",
                "version": "1.8.4"
            })
            self.db.execute(
                "INSERT INTO monitoring_events (fingerprint, timestamp, action, details) VALUES (?, ?, ?, ?)",
                (fp, ts, "video_play" if i % 2 == 0 else "app_start", det)
            )

        # Seed initial broadcast & changelog
        self.kv.put("active_broadcast", {
            "id": "broadcast-seed",
            "active": True,
            "type": "both",
            "title": "Welcome to ani-cli-arabic v2",
            "message": "Enriched telemetry & speed improvements active.",
            "link": "https://github.com/np4abdou1/ani-cli-arabic",
            "style": "emerald"
        })
        self.kv.put("active_changelog", {
            "active": True,
            "title": "What's New in v2.0.0",
            "body": "- Deep OS detection\n- Cloudflare D1 integration\n- Zero latency caching",
            "outdated_notice": "Your client is outdated! Please update to v2.0.0.",
            "latest_version": "2.0.0"
        })

    def start(self):
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()
        time.sleep(0.1)  # small pause to ensure socket listening

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.db:
            self.db.close()


if __name__ == "__main__":
    server = EdgeWorkerEmulatorServer(port=8787)
    server.start()
    print(f"Edge Worker emulator running at {server.base_url} (Press Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        print("\nStopped.")
