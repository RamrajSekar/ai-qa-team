"""Opt-in real TLS Mongo + Podman + ASGI service path; authentication is a fixture double.

No configured database, normal memberships, .env, Redis, UI or model service is used.
"""
import argparse
import asyncio
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

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

ROOT = Path(__file__).resolve().parents[2]


def certificate(work):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Synthetic batch fixture')])
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(datetime.now(timezone.utc)-timedelta(minutes=5))
        .not_valid_after(datetime.now(timezone.utc)+timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'), x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
        .sign(key, hashes.SHA256()))
    ca = work / 'ca.pem'; pem = work / 'mongo.pem'
    ca.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server = (x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')]))
        .issuer_name(name).public_key(server_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc)-timedelta(minutes=5))
        .not_valid_after(datetime.now(timezone.utc)+timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'), x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(key, hashes.SHA256()))
    pem.write_bytes(server_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()) + server.public_bytes(serialization.Encoding.PEM))
    return ca, pem


async def verify(args, work):
    sys.path.insert(0, str(ROOT / 'ai-qa-team-api'))
    from app.config import settings
    from app.db.connection import db, client
    from app.models.visual_batch_model import BatchStart
    from app.services import visual_batch_service as service
    from app.services.visual_batch_engine import PodmanBatchEngine
    from app.routes import visual_batch_routes as routes
    from app.utils.auth_dependency import get_current_user
    from fastapi import FastAPI
    from pymongo import ReturnDocument
    import httpx

    service.ROOT = work / 'private-artifacts'
    settings.features.visual_runner_lab = settings.features.visual_runner_batches = True
    settings.visual_batch_podman, settings.visual_batch_image = args.podman, args.image
    engine = PodmanBatchEngine(args.podman)
    class CountingEngine(PodmanBatchEngine):
        def __init__(self):
            super().__init__(args.podman); self.starts = []
        def start(self, batch_id):
            self.starts.append(batch_id); return super().start(batch_id)
    engine = CountingEngine()
    manager = service.VisualBatchService(database=db, engine=engine)
    routes.visual_batches = manager
    for _ in range(60):
        try:
            await client.admin.command('ping'); break
        except Exception:
            await asyncio.sleep(.25)
    else:
        raise RuntimeError('FIXTURE_TLS_MONGO_NOT_READY')
    await manager.initialize()
    await db['projects'].insert_many([{'project_id': p, 'created_by': 'owner@example.test'} for p in ['p1', 'p2']])
    await db['project_memberships'].insert_many([{'project_id': p, 'email': 'member@example.test', 'status': 'ACTIVE', 'role': 'TESTER'} for p in ['p1', 'p2']])
    app = FastAPI(); app.include_router(routes.router)
    async def user(): return {'email': 'member@example.test'}
    app.dependency_overrides[get_current_user] = user
    api = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://fixture')
    report = {'environment': 'Real isolated TLS Mongo + actual Podman/Robot/CfT + ASGI; authentication double, real project authorization',
              'image': args.image, 'checks': [], 'batches': []}
    def record(name, passed, details=None):
        report['checks'].append({'check': name, 'passed': bool(passed), 'details': details})
        (work/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report['checks'][-1]), flush=True)
        if not passed: raise RuntimeError('REAL_CHECK_FAILED:' + name)
    async def create(count, key=None, project='p1'):
        response = await api.post(f'/projects/{project}/visual-lab/batches', json={
            'idempotency_key': key or secrets.token_hex(16), 'case_count': count})
        if response.status_code != 202: raise RuntimeError('BATCH_CREATION_FAILED')
        return response.json()
    async def finish(ids, deadline=160):
        until = time.monotonic()+deadline
        while time.monotonic()<until:
            await manager.tick()
            docs = [await db['visual_batches'].find_one({'batch_id': bid}) for bid in ids]
            if all(d['state'] in service.TERMINAL for d in docs): return docs
            await asyncio.sleep(.3)
        raise RuntimeError('FIXTURE_WAIT_EXCEEDED')
    try:
        contenders = [secrets.token_hex(16) for _ in range(8)]
        claims = await asyncio.gather(*[db['visual_batch_dispatch'].find_one_and_update(
            {'_id': service.LEDGER, 'slots.0': None}, {'$set': {'slots.0': token}},
            return_document=ReturnDocument.AFTER) for token in contenders])
        record('real Mongo atomic slot contention', sum(c is not None for c in claims) == 1)
        await db['visual_batch_dispatch'].update_one({'_id': service.LEDGER}, {'$set': {'slots.0': None}})
        key = secrets.token_hex(16)
        repeats = await asyncio.gather(*[create(2, key) for _ in range(8)])
        first = repeats[0]
        record('real Mongo duplicate enqueue', len({d['batch_id'] for d in repeats}) == 1 and await db['visual_batches'].count_documents({}) == 1)
        a, b, c = first, await create(2, project='p2'), await create(1)
        await manager.tick()
        ledger = await db['visual_batch_dispatch'].find_one({'_id': service.LEDGER})
        record('two slots allocated; third batch queued', sum(bool(v) for v in ledger['slots'].values()) == 2 and
               (await db['visual_batches'].find_one({'batch_id': c['batch_id']}))['state'] == 'queued')
        # Recreate the coordinator object: durable ownership is read, never replayed.
        manager = service.VisualBatchService(database=db, engine=engine)
        routes.visual_batches = manager
        record('cross-project status and cancel denial',
            (await api.get(f"/projects/p2/visual-lab/batches/{a['batch_id']}")).status_code == 404 and
            (await api.post(f"/projects/p2/visual-lab/batches/{a['batch_id']}/cancel")).status_code == 404)
        await api.post(f"/projects/p1/visual-lab/batches/{a['batch_id']}/cancel")
        docs = await finish([a['batch_id'], b['batch_id'], c['batch_id']])
        record('independent cancellation and queue progression', docs[0]['state'] == 'cancelled' and docs[1]['state'] == docs[2]['state'] == 'completed', [d['state'] for d in docs])
        record('fresh sequential cases with independent evidence', all(len(case['screenshots']) == 3 for case in docs[1]['cases']) and
               docs[1]['cases'][0]['finished_at'] <= docs[1]['cases'][1]['started_at'])
        case = docs[1]['cases'][0]['case_run_id']
        base = f"/projects/p2/visual-lab/batches/{b['batch_id']}/cases/{case}/artifacts/01-open"
        image = await api.get(base)
        record('private authorized screenshot and cross-project denial', image.status_code == 200 and image.content[:8] == b'\x89PNG\r\n\x1a\n' and
            image.headers.get('cache-control') == 'no-store' and
            (await api.get(base.replace('/projects/p2/', '/projects/p1/'))).status_code == 404)
        if not args.quick:
            ten = await create(10)
            print('Starting ten-case boundary qualification; normal budgets unchanged.', flush=True)
            qualified = (await finish([ten['batch_id']], deadline=350))[0]
            record('ten-case batch boundary real execution', qualified['state'] == 'completed' and len(qualified['cases']) == 10 and
                   all(c['state'] == 'completed' and len(c['screenshots']) == 3 for c in qualified['cases']))
        else:
            report['not_rerun'] = ['ten-case boundary; retained earlier full post-fix fixture evidence']
        disabled = await create(2)
        await manager.tick()
        settings.features.visual_runner_batches = False
        # A newly initialized controller must reconcile even with the feature off.
        manager = service.VisualBatchService(database=db, engine=engine)
        manager.task = asyncio.create_task(manager.run())
        until = time.monotonic()+70
        while time.monotonic()<until:
            if (await db['visual_batches'].find_one({'batch_id': disabled['batch_id']}))['state'] in service.TERMINAL:
                break
            await asyncio.sleep(.25)
        await manager.shutdown()
        blocked = await api.get('/projects/p1/visual-lab/batches')
        record('feature off rejects API and stops active container', blocked.status_code == 403 and
            (await db['visual_batches'].find_one({'batch_id': disabled['batch_id']}))['state'] in service.TERMINAL)
        settings.features.visual_runner_batches = True
        record('coordinator recovery never replayed starts', len(engine.starts) == len(set(engine.starts)))
        report['batches'] = [{k: doc[k] for k in ['batch_id', 'state', 'cases']} async for doc in db['visual_batches'].find({})]
        record('capacity released after terminal containers', all(v is None for v in (await db['visual_batch_dispatch'].find_one({'_id': service.LEDGER}))['slots'].values()))
    finally:
        report['batches'] = [{k: doc[k] for k in ['batch_id', 'state', 'cases']} async for doc in db['visual_batches'].find({})]
        # Only containers represented by this private fixture database are touched.
        async for doc in db['visual_batches'].find({}):
            try:
                info = await asyncio.to_thread(engine.inspect, doc['batch_id'], doc['image_id'])
                if info and info['status'] == 'running': await asyncio.to_thread(engine.stop, doc['batch_id'])
            except Exception:
                report['cleanup_unverified'] = True
        await api.aclose()
        client.close()
        (work/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--podman', required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--quick', action='store_true', help='Skip the previously qualified ten-case boundary only')
    args = parser.parse_args()
    work = args.output.resolve(); work.mkdir(parents=True, exist_ok=False)
    ca, pem = certificate(work)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    (work/'db').mkdir()
    # Do not read application .env or access configured development/customer DBs.
    os.chdir(work)
    os.environ.update(MONGO_URI=f'mongodb://127.0.0.1:{port}/?serverSelectionTimeoutMS=1000', MONGO_DB='synthetic_batches',
        MONGO_TLS_CA_FILE=str(ca), REDIS_HOST='127.0.0.1', REDIS_PORT='6399', REDIS_USERNAME='', REDIS_PASSWORD='',
        SESSION_SECRET_KEY=secrets.token_hex(32), JWT_SECRET_KEY=secrets.token_hex(32), APP_ENV='test')
    with open(work/'mongo-private.log', 'wb') as log:
        mongo = subprocess.Popen([r'C:\Program Files\mongodb\bin\mongod.exe', '--dbpath', str(work/'db'),
            '--port', str(port), '--bind_ip', '127.0.0.1', '--tlsMode', 'requireTLS', '--tlsCertificateKeyFile', str(pem),
            '--tlsCAFile', str(ca), '--tlsAllowConnectionsWithoutCertificates'], stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            asyncio.run(verify(args, work))
        finally:
            mongo.terminate(); mongo.wait(timeout=15)


if __name__ == '__main__':
    main()
