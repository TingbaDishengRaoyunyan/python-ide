from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import BaseModel, Field
from pathlib import Path
import hashlib, hmac, os, secrets, shutil, sqlite3, subprocess, time
from typing import List, Optional

DATA_ROOT = Path(os.getenv("DATA_ROOT", "/data")).resolve()
DB_PATH = DATA_ROOT / "users.sqlite3"
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "Yun_Yan+baili20130209")
ADMIN_AUTO_PROMOTE = os.getenv("ADMIN_USERNAME_AUTO_PROMOTE", "false").lower() == "true"
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me")
serializer = URLSafeTimedSerializer(SESSION_SECRET, salt="python-ide-session")
app = FastAPI(title="Python IDE API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=256)
class SaveFileRequest(BaseModel): path: str; content: str
class RunRequest(BaseModel): path: str; args: List[str] = []
class InstallRequest(BaseModel): packages: List[str]
class CreateRequest(BaseModel): path: str; kind: str = "file"
class DeleteRequest(BaseModel): path: str
class RoleRequest(BaseModel): role: str


def db():
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    conn.commit(); return conn

def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16); digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    return f"pbkdf2$310000${salt.hex()}${digest.hex()}"

def password_ok(password, encoded):
    try:
        _, rounds, salt, digest = encoded.split("$"); actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(actual.hex(), digest)
    except (ValueError, TypeError): return False

def workspace_for(username):
    path = DATA_ROOT / "workspaces" / hashlib.sha256(username.encode()).hexdigest(); path.mkdir(parents=True, exist_ok=True); return path

def issue_token(username): return serializer.dumps({"username": username})

def current_user(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(401, "Authentication required")
    try: payload = serializer.loads(authorization[7:], max_age=60 * 60 * 24 * 7)
    except BadSignature as exc: raise HTTPException(401, "Invalid or expired session") from exc
    with db() as conn: row = conn.execute("SELECT username, role, created_at FROM users WHERE username=?", (payload.get("username"),)).fetchone()
    if not row: raise HTTPException(401, "User no longer exists")
    return dict(row)

def admin_user(user=Depends(current_user)):
    if user["role"] != "admin": raise HTTPException(403, "Administrator permission required")
    return user

def auth_workspace(user):
    root = workspace_for(user["username"]); venv = root / ".venv"
    if not venv.exists(): subprocess.run(["python", "-m", "venv", str(venv)], check=True, timeout=120)
    return root, venv, venv / "bin/python"

def resolve_path(root, raw):
    if not raw: raise HTTPException(400, "Missing path")
    target = (root / raw).resolve()
    try: target.relative_to(root)
    except ValueError as exc: raise HTTPException(400, "Path escapes workspace") from exc
    return target

@app.get("/api/health")
def health(): return {"status": "ok", "time": int(time.time())}

@app.post("/api/auth/register")
def register(c: Credentials):
    username = c.username.strip(); role = "admin" if ADMIN_AUTO_PROMOTE and username == ADMIN_USERNAME else "user"
    with db() as conn:
        if conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone(): raise HTTPException(409, "Username already registered")
        conn.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)", (username, password_hash(c.password), role)); conn.commit()
    workspace_for(username); return {"token": issue_token(username), "user": {"username": username, "role": role}}

@app.post("/api/auth/login")
def login(c: Credentials):
    with db() as conn: row = conn.execute("SELECT username,password_hash,role FROM users WHERE username=?", (c.username.strip(),)).fetchone()
    if not row or not password_ok(c.password, row["password_hash"]): raise HTTPException(401, "Invalid username or password")
    return {"token": issue_token(row["username"]), "user": {"username": row["username"], "role": row["role"]}}

@app.get("/api/auth/me")
def me(user=Depends(current_user)): return {"user": user}

@app.get("/api/admin/overview")
def overview(_: dict = Depends(admin_user)):
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]; admins = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
    return {"users": total, "admins": admins, "workspaces": len(list((DATA_ROOT / "workspaces").glob("*"))) if (DATA_ROOT / "workspaces").exists() else 0}

@app.get("/api/admin/users")
def list_users(_: dict = Depends(admin_user)):
    with db() as conn: rows = conn.execute("SELECT username,role,created_at FROM users ORDER BY created_at").fetchall()
    return {"users": [dict(row) for row in rows]}

@app.patch("/api/admin/users/{username}/role")
def change_role(username: str, payload: RoleRequest, user=Depends(admin_user)):
    if payload.role not in {"user", "admin"}: raise HTTPException(400, "Role must be user or admin")
    if username == user["username"] and payload.role != "admin": raise HTTPException(400, "Cannot demote yourself")
    with db() as conn: cur = conn.execute("UPDATE users SET role=? WHERE username=?", (payload.role, username)); conn.commit()
    if not cur.rowcount: raise HTTPException(404, "User not found")
    return {"status": "ok"}

@app.delete("/api/admin/users/{username}")
def delete_user(username: str, user=Depends(admin_user)):
    if username == user["username"]: raise HTTPException(400, "Cannot delete current account")
    with db() as conn: conn.execute("DELETE FROM users WHERE username=?", (username,)); conn.commit()
    path = workspace_for(username)
    if path.exists(): shutil.rmtree(path)
    return {"status": "ok"}

@app.get("/api/files")
def files(path: str = "", user=Depends(current_user)):
    root, _, _ = auth_workspace(user); base = root if not path else resolve_path(root, path)
    if not base.is_dir(): raise HTTPException(404, "Directory not found")
    entries = [{"name": p.name, "path": p.relative_to(root).as_posix(), "type": "directory" if p.is_dir() else "file"} for p in sorted(base.iterdir(), key=lambda x:(not x.is_dir(), x.name.lower())) if p.name != ".venv"]
    return {"path": base.relative_to(root).as_posix() or "/", "entries": entries}

@app.get("/api/file")
def read_file(path: str, user=Depends(current_user)):
    root, _, _ = auth_workspace(user); target = resolve_path(root, path)
    if not target.is_file(): raise HTTPException(404, "File not found")
    return {"path": path, "content": target.read_text(encoding="utf-8")}

@app.post("/api/files/save")
def save_file(p: SaveFileRequest, user=Depends(current_user)):
    root, _, _ = auth_workspace(user); target = resolve_path(root, p.path); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(p.content, encoding="utf-8"); return {"status":"ok"}

@app.post("/api/files/create")
def create_file(p: CreateRequest, user=Depends(current_user)):
    root, _, _ = auth_workspace(user); target = resolve_path(root, p.path)
    if target.exists(): raise HTTPException(400, "Path already exists")
    if p.kind == "directory": target.mkdir(parents=True)
    else: target.parent.mkdir(parents=True, exist_ok=True); target.write_text("", encoding="utf-8")
    return {"status":"ok"}

@app.post("/api/files/delete")
def delete_file(p: DeleteRequest, user=Depends(current_user)):
    root, _, _ = auth_workspace(user); target = resolve_path(root, p.path)
    if not target.exists(): raise HTTPException(404, "Item not found")
    shutil.rmtree(target) if target.is_dir() else target.unlink(); return {"status":"ok"}

@app.post("/api/run")
def run(p: RunRequest, user=Depends(current_user)):
    root, _, python = auth_workspace(user); script = resolve_path(root, p.path)
    if not script.is_file(): raise HTTPException(404, "Script not found")
    try: result = subprocess.run([str(python), str(script), *p.args], cwd=root, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired: raise HTTPException(408, "Execution timed out after 60 seconds")
    return {"exit_code": result.returncode, "stdout": result.stdout[-200000:], "stderr": result.stderr[-200000:]}

@app.post("/api/pip/install")
def pip_install(p: InstallRequest, user=Depends(current_user)):
    if not p.packages or len(p.packages) > 50: raise HTTPException(400, "Provide 1-50 packages")
    root, _, python = auth_workspace(user)
    try: result = subprocess.run([str(python), "-m", "pip", "install", *p.packages], cwd=root, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired: raise HTTPException(408, "pip install timed out")
    return {"exit_code": result.returncode, "stdout": result.stdout[-200000:], "stderr": result.stderr[-200000:]}
