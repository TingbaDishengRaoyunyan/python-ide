from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import os, subprocess

app = FastAPI(title="Python IDE Execution Worker")
WORKER_TOKEN = os.getenv("WORKER_TOKEN", "replace-worker-token")

class RunRequest(BaseModel):
    workspace: str
    path: str
    args: list[str] = []
    gpu: bool = False

class PipRequest(BaseModel):
    workspace: str
    packages: list[str]


def require_token(token: str = Header(default="", alias="X-Worker-Token")):
    if token != WORKER_TOKEN:
        raise HTTPException(401, "Invalid worker token")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run")
def run_script(payload: RunRequest, _: None = Depends(require_token)):
    try:
        completed = subprocess.run(
            ["python", payload.path, *payload.args],
            cwd=payload.workspace,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "Execution timeout")
    return {"exit_code": completed.returncode, "stdout": completed.stdout[-200000:], "stderr": completed.stderr[-200000:]}


@app.post("/pip")
def pip_install(payload: PipRequest, _: None = Depends(require_token)):
    if not payload.packages:
        raise HTTPException(400, "No packages provided")
    try:
        completed = subprocess.run(
            ["python", "-m", "pip", "install", *payload.packages],
            cwd=payload.workspace,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "pip install timeout")
    return {"exit_code": completed.returncode, "stdout": completed.stdout[-200000:], "stderr": completed.stderr[-200000:]}
