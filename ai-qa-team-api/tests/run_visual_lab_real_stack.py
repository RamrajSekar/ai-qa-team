"""Opt-in Windows, task-owned TLS Mongo/API/UI stack; no configured .env or existing services."""
import argparse
from datetime import datetime, timedelta, timezone
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from cryptography.x509.oid import ExtendedKeyUsageOID

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', required=True)
    parser.add_argument('--playwright', required=True)
    parser.add_argument('--api-tools', required=True, help='Task-only uvicorn target directory; existing API venv stays unchanged')
    parser.add_argument('--chrome', help='Optional explicitly configured CfT comparison binary')
    args = parser.parse_args()
    work = ROOT / 'tmp' / ('m1a-real-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    work.mkdir()
    for port in (27119, 8817, 3317):
        with socket.socket() as probe: probe.bind(('127.0.0.1', port))
    # Task-owned localhost certificate; never disable TLS validation.
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'M1A development localhost')])
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(datetime.now(timezone.utc)-timedelta(minutes=5))
            .not_valid_after(datetime.now(timezone.utc)+timedelta(days=2))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'), x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
            .sign(key, hashes.SHA256()))
    ca = work / 'ca.pem'
    ca.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_cert = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')]))
        .issuer_name(name).public_key(server_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc)-timedelta(minutes=5)).not_valid_after(datetime.now(timezone.utc)+timedelta(days=2))
        .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),critical=False).sign(key,hashes.SHA256()))
    pem = work / 'mongo.pem'
    pem.write_bytes(server_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()) + server_cert.public_bytes(serialization.Encoding.PEM))
    (work / 'db').mkdir()
    clean_env = {k: v for k, v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','USERPROFILE','LOCALAPPDATA','APPDATA','PROGRAMFILES','PROGRAMFILES(X86)','COMSPEC'}}
    install = Path(args.install).resolve()
    env = {**clean_env, 'PYTHONUTF8': '1', 'PYTHONPATH': str(Path(args.api_tools).resolve()) + os.pathsep + str(ROOT / 'ai-qa-team-api'),
           'MONGO_URI': 'mongodb://127.0.0.1:27119/?serverSelectionTimeoutMS=5000',
           'MONGO_DB': 'm1a_stabilization', 'MONGO_TLS_CA_FILE': str(ca),
           'REDIS_HOST':'127.0.0.1', 'REDIS_PORT':'6399', 'REDIS_USERNAME':'', 'REDIS_PASSWORD':'',
           'SESSION_SECRET_KEY': secrets.token_urlsafe(32), 'JWT_SECRET_KEY': secrets.token_urlsafe(32),
           'APP_ENV':'development', 'OPENAI_API_KEY':'', 'LLM_SECRET_MASTER_KEY':'',
           'FEATURES__VISUAL_RUNNER_LAB':'true', 'FEATURES__NATIVE_EXECUTION':'false',
           'VISUAL_RUNNER_PYTHON': str(install / '.venv/Scripts/python.exe'),
           'VISUAL_RUNNER_CHROME': args.chrome or str(install / 'binaries/146.0.7680.31/chrome-win64/chrome.exe'),
           'VISUAL_RUNNER_DRIVER': str(install / 'binaries/146.0.7680.31/chromedriver-win64/chromedriver.exe')}
    env['M1A_FIXTURE_STOP_FILE'] = str(work/'stop-api')
    children = []
    files = []
    def launch(command, environment, cwd, log):
        handle = open(work / log, 'ab')
        files.append(handle)
        process = subprocess.Popen(command, env=environment, cwd=cwd, stdout=handle, stderr=handle, creationflags=subprocess.CREATE_NO_WINDOW)
        children.append(process)
        return process
    api = None
    def start_api():
        (work/'stop-api').unlink(missing_ok=True)
        return launch([sys.executable, str(ROOT/'ai-qa-team-api/tests/serve_visual_lab_fixture.py')], env, work, 'api-private.log')
    def wait_http(url, process):
        until = time.monotonic()+90
        while time.monotonic()<until:
            if process.poll() is not None: raise RuntimeError('Task service exited: '+url)
            try:
                if httpx.get(url, timeout=2, trust_env=False).status_code == 200: return
            except httpx.TransportError: pass
            time.sleep(.2)
        raise RuntimeError('Task service readiness timed out: '+url)
    try:
        launch([r'C:\Program Files\mongodb\bin\mongod.exe','--dbpath',str(work/'db'),'--port','27119',
                '--bind_ip','127.0.0.1','--tlsMode','requireTLS','--tlsCertificateKeyFile',str(pem),
                '--tlsCAFile',str(ca),'--tlsAllowConnectionsWithoutCertificates'], clean_env, work, 'mongo-private.log')
        api = start_api()
        wait_http('http://127.0.0.1:8817/features', api)
        node = r'C:\Program Files\nodejs\node.exe'
        ui = launch([node,str(ROOT/'ai-qa-team-ui/node_modules/next/dist/bin/next'),'dev','--webpack','--hostname','127.0.0.1','--port','3317'],
                    {**clean_env,'NEXT_PUBLIC_API_URL':'/api','API_BACKEND_URL':'http://127.0.0.1:8817'}, ROOT/'ai-qa-team-ui', 'ui-private.log')
        wait_http('http://127.0.0.1:3317/', ui)
        test = launch([node,str(ROOT/'ai-qa-team-ui/tests/visual-lab.real.cjs')],
                      {**clean_env,'PLAYWRIGHT_MODULE_PATH':args.playwright,'M1A_REAL_WORK':str(work),'M1A_REAL_URL':'http://127.0.0.1:3317'},
                      ROOT/'ai-qa-team-ui','test-private.log')
        seen = None
        while test.poll() is None:
            command_path = work/'command.json'
            if command_path.exists():
                command = json.loads(command_path.read_text())
                if command['id'] != seen:
                    seen = command['id']
                    if command['action'] not in {'restart','interrupt','disable','enable'}: raise RuntimeError('Invalid fixture control')
                    if command['action'] == 'interrupt':
                        api.kill()
                    else:
                        (work/'stop-api').touch()
                    api.wait(25)
                    if command['action'] == 'interrupt': time.sleep(16)
                    env['FEATURES__VISUAL_RUNNER_LAB'] = 'false' if command['action']=='disable' else 'true'
                    api = start_api()
                    wait_http('http://127.0.0.1:8817/features',api)
                    (work/'ack.json').write_text(json.dumps({'id':seen}))
            time.sleep(.2)
        report = work/'report.json'
        if report.exists(): print(report.read_text(), flush=True)
        else: print(json.dumps({'result':'NOT_COMPLETED', 'evidence_directory':work.name}),flush=True)
        # Direct real-Mongo corroboration. Never print user/password/cookie documents.
        from pymongo import MongoClient
        with MongoClient(env['MONGO_URI'], tls=True, tlsCAFile=str(ca)) as client:
            db = client['m1a_stabilization']
            summary = {'real_mongo_run_count':db.visual_lab_runs.count_documents({}),
                       'active_records':db.visual_lab_runs.count_documents({'state':{'$in':['starting','running','stopping']}}),
                       'held_leases':db.visual_lab_locks.count_documents({'run_id':{'$ne':None}}),
                       'unexpired_leases':db.visual_lab_locks.count_documents({'run_id':{'$ne':None},'expires_at':{'$gte':datetime.now(timezone.utc)}})}
            ids = [d['run_id'] for d in db.visual_lab_runs.find({}, {'run_id':1})]
            if ids:
                # All IDs are generated hex, never user commands; return only a count, not command lines.
                import re
                if not all(re.fullmatch('[0-9a-f]{32}', value) for value in ids): raise RuntimeError('Invalid fixture run ID')
                pattern = '|'.join(ids)
                command = f"@(Get-CimInstance Win32_Process | Where-Object {{ $_.ProcessId -ne $PID -and $_.CommandLine -match '{pattern}' }}).Count"
                observation = subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True,timeout=15)
                summary['remaining_run_profile_processes_observed'] = int(observation.stdout.strip()) if observation.returncode==0 and observation.stdout.strip().isdigit() else 'UNVERIFIED'
            (work/'mongo-summary.json').write_text(json.dumps(summary,indent=2))
            print(json.dumps(summary),flush=True)
        raise SystemExit(test.returncode)
    finally:
        # Only processes created here are stopped; the browser has heartbeat supervision.
        for process in reversed(children):
            if process.poll() is None:
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'], stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                process.wait(10)
        for handle in files: handle.close()


if __name__ == '__main__': main()
