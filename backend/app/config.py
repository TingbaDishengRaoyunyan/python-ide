import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "/workspace")).resolve()
VENV_PATH = WORKSPACE_ROOT / ".venv"
PYTHON_BIN = VENV_PATH / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

app = FastAPI(title="Python IDE API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def ensure_workspace():
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    if not VENV_PATH.exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV_PATH)], check=True)


def resolve_user_path(raw_path: str) -> Path:
    if not raw_path:
        raise HTTPException(status_code=400, detail="Missing path")
    candidate = (WORKSPACE_ROOT / raw_path).resolve()
    try:
        candidate.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Path escapes workspace") from exc
    return candidate


@app.on_event("startup")
def startup_event():
    ensure_workspace()


@app.get("/api/health")
def health():
    return {"status": "ok", "workspace": str(WORKSPACE_ROOT), "python": str(PYTHON_BIN)}


@app.get("/api/files")
def list_files(path: str = ""):
    ensure_workspace()
    base = resolve_user_path(path) if path else WORKSPACE_ROOT
    if not base.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    if not base.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    entries = []
    for child in sorted(base.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        entries.append(
            {
                "name": child.name,
                "path": child.relative_to(WORKSPACE_ROOT).as_posix(),
                "type": "directory" if child.is_dir() else "file",
            }
        )
    return {"path": base.relative_to(WORKSPACE_ROOT).as_posix() or "/", "entries": entries}


@app.post("/api/files/create")
def create_item(payload: CreateRequest):
    ensure_workspace()
    target = resolve_user_path(payload.path)
    if target.exists():
        raise HTTPException(status_code=400, detail="Path already exists")
    if payload.kind == "directory":
        target.mkdir(parents=True, exist_ok=False)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    return {"status": "ok", "path": target.relative_to(WORKSPACE_ROOT).as_posix()}


@app.post("/api/files/delete")
def delete_item(payload: DeleteRequest):
    ensure_workspace()
    target = resolve_user_path(payload.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Item not found")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"status": "ok"}


@app.get("/api/file")
def read_file(path: str):
    ensure_workspace()
    target = resolve_user_path(path)
    if not target.exists() or target.is_dir():
        raise HTTPException(status_code=404, detail="File not found")
    return {"path": target.relative_to(WORKSPACE_ROOT).as_posix(), "content": target.read_text(encoding="utf-8")}


@app.post("/api/files/save")
def save_file(payload: SaveFileRequest):
    ensure_workspace()
    target = resolve_user_path(payload.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8")
    return {"status": "ok", "path": target.relative_to(WORKSPACE_ROOT).as_posix()}


@app.post("/api/run")
def run_script(payload: RunRequest):
    ensure_workspace()
    script_path = resolve_user_path(payload.path)
    if not script_path.exists() or script_path.is_dir():
        raise HTTPException(status_code=404, detail="Script not found")

    command = [str(PYTHON_BIN), str(script_path)] + list(payload.args)
    completed = subprocess.run(command, cwd=str(WORKSPACE_ROOT), capture_output=True, text=True)
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


@app.post("/api/pip/install")
def pip_install(payload: InstallRequest):
    ensure_workspace()
    if not payload.packages:
        raise HTTPException(status_code=400, detail="No packages provided")
    command = [str(PYTHON_BIN), "-m", "pip", "install", *payload.packages]
    completed = subprocess.run(command, cwd=str(WORKSPACE_ROOT), capture_output=True, text=True)
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


@app.post("/api/pip/install-from-file")
def pip_install_from_file(payload: dict):
    ensure_workspace()
    requirements_path = payload.get("path", "requirements.txt")
    requirements_file = resolve_user_path(requirements_path)
    if not requirements_file.exists() or requirements_file.is_dir():
        raise HTTPException(status_code=404, detail="Requirements file not found")
    command = [str(PYTHON_BIN), "-m", "pip", "install", "-r", str(requirements_file)]
    completed = subprocess.run(command, cwd=str(WORKSPACE_ROOT), capture_output=True, text=True)
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


@app.get("/api/project")
def project_summary():
    ensure_workspace()
    files = []
    for root, _, filenames in os.walk(WORKSPACE_ROOT):
        for filename in filenames:
            full = Path(root) / filename
            try:
                rel = full.relative_to(WORKSPACE_ROOT).as_posix()
                if rel.startswith(".venv/"):
                    continue
                files.append(rel)
    return {"workspace": str(WORKSPACE_ROOT), "files": sorted(files)[:200]}
