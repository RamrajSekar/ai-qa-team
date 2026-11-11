"""Safe file protocol and a machine-wide kernel lock (released on process death)."""
import json
import os
from pathlib import Path


def runner_environment():
    """Match the API child's OS-only environment for standalone verification."""
    names = {'SYSTEMROOT', 'SYSTEMDRIVE', 'WINDIR', 'TEMP', 'TMP', 'LOCALAPPDATA', 'APPDATA',
             'PROGRAMDATA', 'COMSPEC', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMW6432', 'USERPROFILE', 'PATH'}
    return {**{k: v for k, v in os.environ.items() if k.upper() in names}, 'PYTHONUTF8': '1'}


def atomic_json(path: Path, value: dict):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value), encoding='utf-8')
    os.replace(temporary, path)


class BrowserLock:
    def __init__(self, path: Path):
        self.file = open(path, 'a+b')
        self.file.seek(0)
        self.file.write(b'0')
        self.file.flush()
        self.file.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise RuntimeError('BROWSER_BUSY') from None

    def close(self):
        self.file.close()


class WindowsProcessTree:
    """Kill-on-close Job Object. Driver starts suspended to avoid a child escape race."""
    def __init__(self):
        import ctypes as c
        from ctypes import wintypes as w
        self.c, self.w = c, w
        self.k = c.WinDLL('kernel32', use_last_error=True)
        class IO(c.Structure):
            _fields_ = [(name, c.c_ulonglong) for name in ('r','w','o','rb','wb','ob')]
        class Basic(c.Structure):
            _fields_ = [('process', c.c_longlong), ('job', c.c_longlong), ('flags', w.DWORD),
                        ('min', c.c_size_t), ('max', c.c_size_t), ('active', w.DWORD),
                        ('affinity', c.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
        class Extended(c.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('process_memory', c.c_size_t),
                        ('job_memory', c.c_size_t), ('peak_process', c.c_size_t), ('peak_job', c.c_size_t)]
        self.k.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
        self.k.CreateJobObjectW.restype = w.HANDLE
        self.k.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
        self.k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.k.CloseHandle.argtypes = [w.HANDLE]
        self.handle = self.k.CreateJobObjectW(None, None)
        self.observed_browsers = {}
        limits = Extended()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not self.k.SetInformationJobObject(self.handle, 9, c.byref(limits), c.sizeof(limits)):
            self.close()
            raise RuntimeError('PROCESS_ISOLATION_FAILED')

    def launch(self, args, **options):
        import subprocess
        # Python Popen closes the initial thread handle. NtResumeProcess resumes after assignment.
        options.setdefault('stdout', subprocess.DEVNULL)
        options.setdefault('stderr', subprocess.DEVNULL)
        process = subprocess.Popen(args, creationflags=0x4 | 0x08000000, **options)
        if not self.k.AssignProcessToJobObject(self.handle, int(process._handle)):
            process.kill()
            process.wait()
            raise RuntimeError('PROCESS_ISOLATION_FAILED')
        ntdll = self.c.WinDLL('ntdll')
        ntdll.NtResumeProcess.argtypes = [self.w.HANDLE]
        ntdll.NtResumeProcess.restype = self.c.c_long
        if ntdll.NtResumeProcess(int(process._handle)) != 0:
            self.close()
            process.wait()
            raise RuntimeError('PROCESS_ISOLATION_FAILED')
        return process

    def close(self):
        if getattr(self, 'handle', None):
            self.k.CloseHandle(self.handle)
            self.handle = None

    def browser_status(self):
        """Observe only processes in our Job Object; never publish IDs or image paths."""
        c, w, k = self.c, self.w, self.k
        k.QueryInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.c_void_p]
        k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        k.OpenProcess.restype = w.HANDLE
        k.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, c.POINTER(w.DWORD)]
        k.GetExitCodeProcess.argtypes = [w.HANDLE, c.POINTER(w.DWORD)]
        class ProcessList(c.Structure):
            _fields_ = [('assigned', w.DWORD), ('count', w.DWORD), ('ids', c.c_size_t * 64)]
        failed = False
        if self.handle:
            processes = ProcessList()
            if k.QueryInformationJobObject(self.handle, 3, c.byref(processes), c.sizeof(processes), None):
                for pid in list(processes.ids)[:min(processes.count, 64)]:
                    if pid in self.observed_browsers or len(self.observed_browsers) >= 32:
                        continue
                    handle = k.OpenProcess(0x1000, False, pid)
                    if not handle:
                        failed = True
                        continue
                    size = w.DWORD(32768)
                    image = c.create_unicode_buffer(size.value)
                    if k.QueryFullProcessImageNameW(handle, 0, image, c.byref(size)) and Path(image.value).name.lower() == 'chrome.exe':
                        self.observed_browsers[pid] = handle
                    else:
                        k.CloseHandle(handle)
            else:
                failed = True
        codes = []
        for handle in self.observed_browsers.values():
            code = w.DWORD()
            if not k.GetExitCodeProcess(handle, c.byref(code)):
                return 'unavailable'
            codes.append(code.value)
        if 259 in codes:  # STILL_ACTIVE; not a browser exit code.
            return 'running'
        if codes:
            return 'exited'
        return 'unavailable' if failed else 'not_observed'

    def release_observations(self):
        for handle in self.observed_browsers.values():
            self.k.CloseHandle(handle)
        self.observed_browsers.clear()
