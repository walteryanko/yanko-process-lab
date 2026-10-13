"""Atomic, closed-handle writes work on Windows; no untrusted arbitrary paths."""
import json
import os
import re
import tempfile
from pathlib import Path
from .schema import canonical


def atomic_json(path,data):
    payload=json.dumps(data,ensure_ascii=False,allow_nan=False,indent=2).encode("utf-8")
    atomic_bytes(path,payload)


def atomic_bytes(path,payload):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=".processlab-",suffix=".tmp",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as stream:
            stream.write(payload);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


class Storage:
    def __init__(self,directory=None):
        base=Path(os.environ.get("APPDATA",Path.home()/".local"/"share"))
        self.root=Path(directory) if directory else base/"YCS ProcessLab Studio"
        self.root.mkdir(parents=True,exist_ok=True)

    def path(self,id):
        if not isinstance(id,str) or not re.fullmatch(r"[\w-]{1,80}",id):raise ValueError("Invalid project identifier")
        return self.root/f"{id}.processlab.json"

    def save(self,project):
        p=canonical(project);path=self.path(p["id"])
        if path.exists():
            try:atomic_json(path.with_suffix(".bak"),json.loads(path.read_text("utf-8")))
            except (ValueError,OSError):pass
        atomic_json(path,p);return {"id":p["id"],"path":str(path)}

    def load(self,id):
        path=self.path(id)
        if path.stat().st_size>2_000_000:raise ValueError("Project exceeds 2 MB limit")
        return canonical(json.loads(path.read_text("utf-8")))

    def list(self):
        out=[]
        for path in sorted(self.root.glob("*.processlab.json")):
            try:
                p=json.loads(path.read_text("utf-8"));out.append({"id":p["id"],"name":p["name"]})
            except (ValueError,OSError,KeyError):continue
        return out
