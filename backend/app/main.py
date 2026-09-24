from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import BaseModel, Field
from pathlib import Path
import hashlib
import hmac
import os
import secrets
import shutil
import sqlite3
import subprocess
from typing import List

DATA_ROOT = Path(os.getenv("DATA_ROOT", "/data")).resolve()
DB_PATH = DATA_ROOT / "users.sqlite3"
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "Yun_Yan+baili20130209")
ADMIN_AUTO_PROMOTE = os.getenv("ADMIN_USERNAME_AUTO_PROMOTE", "true").lower() == "true"
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me")
serializer = URLSafeTimedSerializer(SESSION_SECRET, salt="python-ide-session")
app = FastAPI(title="Python IDE API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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


def db():
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, role TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    return conn


def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    return f"pbkdf2$310000${salt.hex()}${digest.hex()}"


def password_ok(password: str, encoded: str) -> bool:
    try:
        _, rounds, salt_hex, digest_hex = encoded.split("$")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(actual.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def normalize_username(username: str) -> str:
    return username.strip()


def workspace_for(username: str) -> Path:
    safe = hashlib.sha256(username.encode()).hexdigest()
    path = DATA_ROOT / "workspaces" / safe
    path.mkdir(parents=True, exist_ok=True)
    return path


def issue_token(username: str) -> str:
    return serializer.dumps({"username": username})


def current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentication required")
    try:
        payload = serializer.loads(authorization[7:], max_age=60 * 60 * 24 * 7)
    except BadSignature as exc:
        raise HTTPException(401, "Invalid or expired session") from exc
    with db() as conn:
        row = conn.execute("SELECT username, role FROM users WHERE username = ?", (payload.get("username"),)).fetchone()
    if not row:
        raise HTTPException(401, "User no longer exists")
    return dict(row)


def admin_user(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Administrator permission required")
    return user


def ensure_workspace(username: str) -> tuple[Path, Path]:
    root = workspace_for(username)
    venv = root / ".venv"
    if not venv.exists():
        subprocess.run(["python", "-m", "venv", str(venv)], check=True)
    return root, venv


def resolve_path(root: Path, raw_path: str) -> Path:
    if not raw_path:
        raise HTTPException(400, "Missing path")
    candidate = (root / raw_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(400, "Path escapes workspace") from exc
    return candidate


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/register")
def register(credentials: Credentials):
    username = normalize_username(credentials.username)
    role = "admin" if ADMIN_AUTO_PROMOTE and username == ADMIN_USERNAME else "user"
    with db() as conn:
        if conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            raise HTTPException(409, "Username already registered")
        conn.execute("INSERT INTO users(username, password_hash, role) VALUES (?, ?, ?)", (username, password_hash(credentials.password), role))
        conn.commit()
    workspace_for(username)
    return {"token": issue_token(username), "user": {"username": username, "role": role}}


@app.post("/api/auth/login")
def login(credentials: Credentials):
    username = normalize_username(credentials.username)
    with db() as conn:
        row = conn.execute("SELECT username, password_hash, role FROM users WHERE username = ?", (username,)).fetchone()
    if not row or not password_ok(credentials.password, row["password_hash"]):
        raise HTTPException(401, "Invalid username or password")
    return {"token": issue_token(row["username"]), "user": {"username": row["username"], "role": row["role"]}}


@app.get("/api/auth/me")
def me(user: dict = Depends(current_user)):
    return {"user": user}


@app.get("/api/admin/users")
def list_users(_: dict = Depends(admin_user)):
    with db() as conn:
        rows = conn.execute("SELECT username, role, created_at FROM users ORDER BY created_at").fetchall()
    return {"users": [dict(row) for row in rows]}


@app.delete("/api/admin/users/{username}")
def delete_user(username: str, user: dict = Depends(admin_user)):
    if username == user["username"]:
        raise HTTPException(400, "Admin cannot delete the current account")
    with db() as conn:
        conn.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
    workspace = workspace_for(username)
    if workspace.exists():
        shutil.rmtree(workspace)
    return {"status": "ok"}


def auth_workspace(user: dict) -> tuple[Path, Path, Path]:
    root, venv = ensure_workspace(user["username"])
    python_bin = venv / "bin/python"
    return root, venv, python_bin


@app.get("/api/files")
def list_files(path: str = "", user: dict = Depends(current_user)):
    root, _, _ = auth_workspace(user)
    base = root if not path else resolve_path(root, path)
    if not base.exists() or not base.is_dir(): raise HTTPException(404, "Directory not found")
    entries = [{"name": p.name, "path": p.relative_to(root).as_posix(), "type": "directory" if p.is_dir() else "file"} for p in sorted(base.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())) if p.name != ".venv"]
    return {"path": base.relative_to(root).as_posix() or "/", "entries": entries}

@app.get("/api/file")
def read_file(path: str, user: dict = Depends(current_user)):
    root, _, _ = auth_workspace(user); target = resolve_path(root, path)
    if not target.exists() or target.is_dir(): raise HTTPException(404, "File not found")
    return {"path": target.relative_to(root).as_posix(), "content": target.read_text(encoding="utf-8")}

@app.post("/api/files/save")
def save_file(payload: SaveFileRequest, user: dict = Depends(current_user)):
    root, _, _ = auth_workspace(user); target = resolve_path(root, payload.path)
    target.parent.mkdir(parents=True, exist_ok=True); target.write_text(payload.content, encoding="utf-8")
    return {"status": "ok"}

@app.post("/api/files/create")
def create_item(payload: CreateRequest, user: dict = Depends(current_user)):
    root, _, _ = auth_workspace(user); target = resolve_path(root, payload.path)
    if target.exists(): raise HTTPException(400, "Path already exists")
    if payload.kind == "directory": target.mkdir(parents=True)
    else: target.parent.mkdir(parents=True, exist_ok=True); target.write_text("", encoding="utf-8")
    return {"status": "ok"}

@app.post("/api/files/delete")
def delete_item(payload: DeleteRequest, user: dict = Depends(current_user)):
    root, _, _ = auth_workspace(user); target = resolve_path(root, payload.path)
    if not target.exists(): raise HTTPException(404, "Item not found")
    if target.is_dir(): shutil.rmtree(target)
    else: target.unlink()
    return {"status": "ok"}

@app.post("/api/run")
def run_script(payload: RunRequest, user: dict = Depends(current_user)):
    root, _, python_bin = auth_workspace(user); script = resolve_path(root, payload.path)
    if not script.exists() or script.is_dir(): raise HTTPException(404, "Script not found")
    completed = subprocess.run([str(python_bin), str(script), *payload.args], cwd=root, capture_output=True, text=True, timeout=60)
    return {"exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}

@app.post("/api/pip/install")
def pip_install(payload: InstallRequest, user: dict = Depends(current_user)):
    if not payload.packages: raise HTTPException(400, "No packages provided")
    root, _, python_bin = auth_workspace(user)
    completed = subprocess.run([str(python_bin), "-m", "pip", "install", *payload.packages], cwd=root, capture_output=True, text=True, timeout=600)
    return {"exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}
