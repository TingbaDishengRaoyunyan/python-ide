from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import BaseModel, Field
from pathlib import Path
import hashlib, hmac, httpx, json, os, secrets, shutil, sqlite3, time
from typing import List, Optional

DATA_ROOT = Path(os.getenv("DATA_ROOT", "/data")).resolve()
DB_PATH = DATA_ROOT / "users.sqlite3"
WORKER_URL = os.getenv("WORKER_URL", "http://worker:9000")
WORKER_TOKEN = os.getenv("WORKER_TOKEN", "replace-worker-token")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "Yun_Yan+baili20130209")
ADMIN_AUTO_PROMOTE = os.getenv("ADMIN_AUTO_PROMOTE", "false").lower() == "true"
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me")
serializer = URLSafeTimedSerializer(SESSION_SECRET, salt="python-ide-session")
app = FastAPI(title="Python IDE Control Plane")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DEFAULT_PERMISSIONS = {
    "ide": True,
    "run": True,
    "pip": True,
    "gpu": False,
    "manage_users": False,
    "manage_roles": False,
}

class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=256)

class SaveFileRequest(BaseModel):
    path: str
    content: str

class RunRequest(BaseModel):
    path: str
    args: List[str] = []

class InstallRequest(BaseModel):
    packages: List[str]

class CreateRequest(BaseModel):
    path: str
    kind: str = "file"

class DeleteRequest(BaseModel):
    path: str

class RoleRequest(BaseModel):
    role: str

class PermissionRequest(BaseModel):
    permission: str
    enabled: bool


def db():
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            permissions TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn


def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    return f"pbkdf2$310000${salt.hex()}${digest.hex()}"


def password_ok(password: str, encoded: str) -> bool:
    try:
        _, _, salt_hex, digest_hex = encoded.split("$")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 310000)
        return hmac.compare_digest(actual.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def normalize_user(row: sqlite3.Row) -> dict:
    data = dict(row)
    permissions = DEFAULT_PERMISSIONS.copy()
    permissions.update(json.loads(data.get("permissions") or "{}"))
    data["permissions"] = permissions
    return data


def workspace_for(username: str) -> Path:
    safe = hashlib.sha256(username.encode()).hexdigest()
    root = DATA_ROOT / "workspaces" / safe
    root.mkdir(parents=True, exist_ok=True)
    return root


def issue_token(username: str) -> str:
    return serializer.dumps({"username": username})


def current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentication required")
    try:
        payload = serializer.loads(authorization[7:], max_age=60 * 60 * 24 * 7)
    except BadSignature as exc:
        raise HTTPException(401, "Invalid or expired session") from exc
    with db() as conn:
        row = conn.execute(
            "SELECT username, role, permissions, created_at FROM users WHERE username = ?",
            (payload.get("username"),),
        ).fetchone()
    if not row:
        raise HTTPException(401, "User no longer exists")
    user = normalize_user(row)
    if user["username"] == ADMIN_USERNAME:
        user["role"] = "owner"
        user["permissions"] = {k: True for k in DEFAULT_PERMISSIONS}
    return user


def require(permission: str):
    def dependency(user: dict = Depends(current_user)):
        if user["role"] in {"owner", "admin"}:
            return user
        if user["permissions"].get(permission, False):
            return user
        raise HTTPException(403, f"Permission required: {permission}")

    return dependency


def admin_user(user: dict = Depends(current_user)) -> dict:
    if user["role"] not in {"owner", "admin"}:
        raise HTTPException(403, "Administrator permission required")
    return user


def resolve_path(root: Path, raw_path: str) -> Path:
    if not raw_path:
        raise HTTPException(400, "Missing path")
    candidate = (root / raw_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(400, "Path escapes workspace") from exc
    return candidate


def worker_call(endpoint: str, payload: dict, timeout: float = 600) -> dict:
    try:
        response = httpx.post(
            f"{WORKER_URL}{endpoint}",
            json=payload,
            headers={"X-Worker-Token": WORKER_TOKEN},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(503, f"Execution worker unavailable: {exc}") from exc


@app.get("/api/health")
def health():
    return {"status": "ok", "time": int(time.time())}


@app.post("/api/auth/register")
def register(credentials: Credentials):
    username = credentials.username.strip()
    auto_owner = ADMIN_AUTO_PROMOTE and username == ADMIN_USERNAME
    role = "owner" if auto_owner else "user"
    permissions = DEFAULT_PERMISSIONS.copy()
    if role == "owner":
        permissions = {key: True for key in permissions}
    else:
        permissions["manage_users"] = False
        permissions["manage_roles"] = False

    with db() as conn:
        if conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            raise HTTPException(409, "Username already registered")
        conn.execute(
            "INSERT INTO users(username, password_hash, role, permissions) VALUES (?, ?, ?, ?)",
            (username, password_hash(credentials.password), role, json.dumps(permissions)),
        )
        conn.commit()
    workspace_for(username)
    return {"token": issue_token(username), "user": {"username": username, "role": role, "permissions": permissions}}


@app.post("/api/auth/login")
def login(credentials: Credentials):
    username = credentials.username.strip()
    with db() as conn:
        row = conn.execute(
            "SELECT username, password_hash, role, permissions, created_at FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if not row or not password_ok(credentials.password, row["password_hash"]):
        raise HTTPException(401, "Invalid username or password")
    user = normalize_user(row)
    if user["username"] == ADMIN_USERNAME:
        user["role"] = "owner"
        user["permissions"] = {k: True for k in DEFAULT_PERMISSIONS}
    return {"token": issue_token(row["username"]), "user": user}


@app.get("/api/auth/me")
def me(user: dict = Depends(current_user)):
    return {"user": user}


@app.get("/api/admin/overview")
def overview(_: dict = Depends(admin_user)):
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        admins = conn.execute("SELECT COUNT(*) FROM users WHERE role IN ('admin', 'owner')").fetchone()[0]
    workspaces = len(list((DATA_ROOT / "workspaces").glob("*"))) if (DATA_ROOT / "workspaces").exists() else 0
    return {"users": total, "admins": admins, "workspaces": workspaces, "worker": WORKER_URL}


@app.get("/api/admin/users")
def list_users(q: str = "", _: dict = Depends(admin_user)):
    q = f"%{q.strip()}%"
    with db() as conn:
        rows = conn.execute(
            "SELECT username, role, permissions, created_at FROM users WHERE username LIKE ? ORDER BY created_at",
            (q,),
        ).fetchall()
    return {"users": [normalize_user(row) for row in rows]}


@app.patch("/api/admin/users/{username}/role")
def change_role(username: str, payload: RoleRequest, user: dict = Depends(admin_user)):
    if payload.role not in {"user", "admin"}:
        raise HTTPException(400, "Role must be user or admin")
    if username == ADMIN_USERNAME:
        raise HTTPException(400, "Reserved owner role cannot be changed")
    if username == user["username"] and payload.role != "admin":
        raise HTTPException(400, "Cannot demote yourself")
    with db() as conn:
        result = conn.execute("UPDATE users SET role = ? WHERE username = ?", (payload.role, username))
        conn.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "User not found")
    return {"status": "ok"}


@app.patch("/api/admin/users/{username}/permission")
def change_permission(username: str, payload: PermissionRequest, user: dict = Depends(admin_user)):
    if payload.permission not in DEFAULT_PERMISSIONS:
        raise HTTPException(400, "Unknown permission")
    if username == ADMIN_USERNAME:
        raise HTTPException(400, "Owner permissions cannot be changed")
    with db() as conn:
        row = conn.execute("SELECT permissions FROM users WHERE username = ?", (username,)).fetchone()
        if not row:
            raise HTTPException(404, "User not found")
        permissions = DEFAULT_PERMISSIONS.copy()
        permissions.update(json.loads(row["permissions"] or "{}"))
        permissions[payload.permission] = payload.enabled
        conn.execute(
            "UPDATE users SET permissions = ? WHERE username = ?",
            (json.dumps(permissions), username),
        )
        conn.commit()
    return {"status": "ok", "permissions": permissions}


@app.delete("/api/admin/users/{username}")
def delete_user(username: str, user: dict = Depends(admin_user)):
    if username == user["username"] or username == ADMIN_USERNAME:
        raise HTTPException(400, "Cannot delete the current or reserved owner account")
    with db() as conn:
        conn.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
    return {"status": "ok"}


@app.get("/api/files")
def list_files(path: str = "", user: dict = Depends(require("ide"))):
    root = workspace_for(user["username"])
    base = root if not path else resolve_path(root, path)
    if not base.exists() or not base.is_dir():
        raise HTTPException(404, "Directory not found")
    entries = [
        {"name": p.name, "path": p.relative_to(root).as_posix(), "type": "directory" if p.is_dir() else "file"}
        for p in sorted(base.iterdir(), key=lambda child: (not child.is_dir(), child.name.lower()))
        if p.name != ".venv"
    ]
    return {"path": base.relative_to(root).as_posix() or "/", "entries": entries}


@app.get("/api/file")
def read_file(path: str, user: dict = Depends(require("ide"))):
    root = workspace_for(user["username"])
    target = resolve_path(root, path)
    if not target.exists() or target.is_dir():
        raise HTTPException(404, "File not found")
    return {"path": target.relative_to(root).as_posix(), "content": target.read_text(encoding="utf-8")}


@app.post("/api/files/save")
def save_file(payload: SaveFileRequest, user: dict = Depends(require("ide"))):
    root = workspace_for(user["username"])
    target = resolve_path(root, payload.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8")
    return {"status": "ok"}


@app.post("/api/files/create")
def create_item(payload: CreateRequest, user: dict = Depends(require("ide"))):
    root = workspace_for(user["username"])
    target = resolve_path(root, payload.path)
    if target.exists():
        raise HTTPException(400, "Path already exists")
    if payload.kind == "directory":
        target.mkdir(parents=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    return {"status": "ok"}


@app.post("/api/files/delete")
def delete_item(payload: DeleteRequest, user: dict = Depends(require("ide"))):
    root = workspace_for(user["username"])
    target = resolve_path(root, payload.path)
    if not target.exists():
        raise HTTPException(404, "Item not found")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"status": "ok"}


@app.post("/api/run")
def run_script(payload: RunRequest, user: dict = Depends(require("run"))):
    root = workspace_for(user["username"])
    script = resolve_path(root, payload.path)
    if not script.exists() or script.is_dir():
        raise HTTPException(404, "Script not found")
    result = worker_call(
        "/run",
        {
            "workspace": str(root),
            "path": str(script),
            "args": payload.args,
            "gpu": bool(user["permissions"].get("gpu", False)),
        },
        timeout=60,
    )
    return result


@app.post("/api/pip/install")
def pip_install(payload: InstallRequest, user: dict = Depends(require("pip"))):
    if not payload.packages or len(payload.packages) > 50:
        raise HTTPException(400, "Provide 1-50 packages")
    root = workspace_for(user["username"])
    return worker_call(
        "/pip",
        {"workspace": str(root), "packages": payload.packages},
        timeout=600,
    )
