"""Container-only process groups; the container is the final cleanup boundary."""
import os
import signal
import subprocess
import threading


class LinuxProcessTree:
    def __init__(self):
        self.process = None
        self.lock = threading.Lock()

    def launch(self, args, **options):
        with self.lock:
            self.process = subprocess.Popen(args, start_new_session=True, **options)
            return self.process

    def close(self):
        with self.lock:
            if self.process:
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def browser_status(self):
        # A process-group observation is not a per-browser observation.
        return 'unavailable'

    def release_observations(self):
        pass
