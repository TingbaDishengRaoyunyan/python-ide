from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import os, subprocess

app=FastAPI(title="Python IDE Execution Worker")
TOKEN=os.getenv("WORKER_TOKEN","replace-worker-token")
class Run(BaseModel): workspace:str; path:str; args:list[str]=[]; gpu:bool=False
class Pip(BaseModel): workspace:str; packages:list[str]
def auth(token):
    if token != TOKEN: raise HTTPException(401,"Invalid worker token")
def execute(cmd,cwd,timeout):
    try: r=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=timeout)
    except subprocess.TimeoutExpired: raise HTTPException(408,"Worker timeout")
    return {"exit_code":r.returncode,"stdout":r.stdout[-200000:],"stderr":r.stderr[-200000:]}
@app.get("/health")
def health(): return {"status":"ok"}
@app.post("/run")
def run(p:Run, x_worker_token:str=Header(default="")):
    auth(x_worker_token); return execute(["python",p.path,*p.args],p.workspace,60)
@app.post("/pip")
def pip(p:Pip,x_worker_token:str=Header(default="")):
    auth(x_worker_token); return execute(["python","-m","pip","install",*p.packages],p.workspace,600)
