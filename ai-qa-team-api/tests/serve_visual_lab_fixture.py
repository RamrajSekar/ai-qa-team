"""Normal Uvicorn/FastAPI server with task-local graceful-stop IPC, not an HTTP test backdoor."""
import os
from pathlib import Path
import threading
import time
import uvicorn

server = uvicorn.Server(uvicorn.Config('app.main:app', host='127.0.0.1', port=8817))
stop = Path(os.environ['M1A_FIXTURE_STOP_FILE'])


def watch():
    while not server.should_exit:
        if stop.exists():
            server.should_exit = True
            return
        time.sleep(.1)


threading.Thread(target=watch, daemon=True).start()
server.run()
