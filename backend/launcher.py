from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import subprocess, sys, os, asyncio

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_proc: subprocess.Popen | None = None
_backend_dir = os.path.dirname(os.path.abspath(__file__))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/start")
async def start_backend():
    global _proc
    if _proc and _proc.poll() is None:
        return {"status": "already_running"}
    _proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        cwd=_backend_dir,
    )
    await asyncio.sleep(0.3)
    return {"status": "started", "pid": _proc.pid}


@app.post("/stop")
async def stop_backend():
    global _proc
    if _proc and _proc.poll() is None:
        _proc.terminate()
        _proc = None
        return {"status": "stopped"}
    return {"status": "not_running"}


if __name__ == "__main__":
    import uvicorn
    print("Launcher running on http://localhost:9999")
    uvicorn.run(app, host="127.0.0.1", port=9999)
