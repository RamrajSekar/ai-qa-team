"""Opt-in five-check demonstration: real isolated TLS Mongo/Podman; auth double.

Reuses only the private-service fixture bootstrap, never configured development DBs.
Browser overlap is measured by simultaneous bounded in-container observation,
not inferred from queued/running Mongo records.
"""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import sys
import time

import run_visual_batch_real as fixture


async def verify(args, work):
    sys.path.insert(0, str(fixture.ROOT / 'ai-qa-team-api'))
    from app.config import settings
    from app.db.connection import db, client
    from app.services import visual_batch_service as service
    from app.services.visual_batch_engine import PodmanBatchEngine
    from app.routes import visual_batch_routes as routes
    from app.utils.auth_dependency import get_current_user
    from fastapi import FastAPI
    import httpx

    service.ROOT = work / 'private-artifacts'
    settings.features.visual_runner_lab = settings.features.visual_runner_batches = True
    settings.visual_batch_podman, settings.visual_batch_image = args.podman, args.image
    settings.visual_batch_global_slots = settings.visual_batch_account_slots = settings.visual_batch_project_slots = 5
    count = 1 if args.quick else 5  # --quick is a separately recorded one-browser control.
    engine = PodmanBatchEngine(args.podman)
    manager = service.ParallelVisualBatchService(database=db, engine=engine)
    routes.visual_batches = manager
    report = {'environment': 'Real private TLS Mongo, Podman, Robot, HTTPX/CfT; ASGI auth double; no normal UI login',
              'image': args.image, 'checks': [], 'samples': [], 'batches': []}

    def record(name, passed, details=None):
        row = {'check': name, 'passed': bool(passed), 'details': details}
        report['checks'].append(row)
        (work/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(row), flush=True)

    async def finish(batch_id, seconds=180):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            await manager.tick()
            doc = await db['visual_batches'].find_one({'batch_id': batch_id})
            if doc['state'] in service.TERMINAL:
                return doc
            await asyncio.sleep(.25)
        raise RuntimeError('FIXTURE_WAIT_EXCEEDED')

    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[get_current_user] = lambda: {'email': 'member@example.test'}
    api = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://fixture')
    try:
        for _ in range(60):
            try:
                await client.admin.command('ping')
                break
            except Exception:
                await asyncio.sleep(.25)
        else:
            raise RuntimeError('FIXTURE_TLS_MONGO_NOT_READY')
        await manager.initialize()
        await db['projects'].insert_many([{'project_id': p, 'created_by': 'owner@example.test'} for p in ['p1', 'p2']])
        await db['project_memberships'].insert_one({'project_id':'p1', 'email':'member@example.test', 'status':'ACTIVE', 'role':'TESTER'})
        key = secrets.token_hex(16)
        async def create(count, token):
            response = await api.post('/projects/p1/visual-lab/batches', json={'idempotency_key':token, 'case_count':count})
            if response.status_code != 202:
                raise RuntimeError('BATCH_CREATION_FAILED')
            return response.json()
        if args.quick:
            # Explicit fault injection, not a reproduction of the historical cause.
            # Local image lookup only: no pull, container or browser is attempted.
            settings.visual_batch_image = '0'*64
            broken = await create(1, secrets.token_hex(16))
            failed = await finish(broken['batch_id'])
            case = failed['cases'][0]
            record('injected missing-image preparation error survives reconciliation and API',
                failed['state'] == 'interrupted' and case['diagnostic_code'] == 'ENGINE_UNAVAILABLE' and
                (case.get('preparation') or {}).get('error_stage') == 'image_lookup' and
                (case.get('preparation') or {}).get('reason') == 'command_failed' and
                (await api.get(f"/projects/p1/visual-lab/batches/{broken['batch_id']}" )).json()['cases'][0]['preparation']['error_stage'] == 'image_lookup')
            settings.visual_batch_image = args.image
        requests = await asyncio.gather(*[create(count, key) for _ in range(8)])
        batch = requests[0]
        bid = batch['batch_id']
        record('duplicate requests create one parent', len({r['batch_id'] for r in requests}) == 1)
        await manager.tick()
        children = await db['visual_batch_checks'].find({'parent_batch_id':bid}).to_list(10)
        record('independent one-case containers reserved', len(children) == count and all(len(c['manifest']['cases']) == 1 for c in children), {'count':count})

        # Read-only observers persist bounded session-live intervals in the private
        # output volumes. They never delay/retry the workflow or change its budgets.
        # Detached exec returns promptly; normal engine control keeps its 30s bound.
        probe = """import json,time,sys
from pathlib import Path
cid=sys.argv[1]; deadline=time.monotonic()+90
output=Path('/output/overlap-observation.json')
result={'first_seen':None,'last_seen':None,'samples':0}
while time.monotonic()<deadline:
 try:
  raw=json.loads((Path('/output/cases')/cid/'state.json').read_text())
 except (OSError,ValueError): raw={}
 alive=False
 for p in Path('/proc').glob('[0-9]*/status'):
  try:
   fields=dict(line.split(':',1) for line in p.read_text().splitlines() if ':' in line)
   if fields.get('Name','').strip()=='chrome' and not fields.get('State','').strip().startswith('Z'): alive=True
  except FileNotFoundError: pass
 if alive and raw.get('startup_diagnostics',{}).get('session_created') and raw.get('state')=='running':
  result['first_seen']=result['first_seen'] or time.time()
  result['last_seen']=time.time(); result['samples']+=1
 output.write_text(json.dumps(result))
 if raw.get('state') in ['stopping','completed','failed','cancelled','interrupted','timed_out']: break
 time.sleep(.1)
"""
        async def attach(child):
            cid = child['batch_id']
            try:
                await asyncio.to_thread(engine.command, 'exec', '--detach', engine.name(cid), 'python', '-c', probe, cid)
                return True
            except Exception:
                return False
        report['observer_attached'] = await asyncio.gather(*[attach(c) for c in children])
        complete = await finish(bid)
        observations = work / 'observations'
        observations.mkdir(exist_ok=True)
        for child in children:
            cid = child['batch_id']
            try:
                dest = observations / (cid + '.json')
                await asyncio.to_thread(engine.copy, cid, 'overlap-observation.json', dest)
                value = json.loads(dest.read_text())
                report['samples'].append({'case_run_id':cid, **{k:value.get(k) for k in ['first_seen','last_seen','samples']}})
            except Exception:
                report['samples'].append({'case_run_id':cid, 'observation':'unavailable'})
        observed = [s for s in report['samples'] if s.get('first_seen') and s.get('last_seen') and s.get('samples',0)>1]
        overlap = max(0, min(s['last_seen'] for s in observed)-max(s['first_seen'] for s in observed)) if len(observed)==count else 0
        record('first-attempt completions and three screenshots per check', complete['state'] == 'completed' and
            all(c['state'] == 'completed' and len(c['screenshots']) == 3 for c in complete['cases']),
            [{'state':c['state'], 'diagnostic_code':c.get('diagnostic_code')} for c in complete['cases']])
        record('established browser sessions observed together', overlap > 0,
            {'successful_observations':len(observed), 'overlap_seconds':overlap, 'sampling_interval_seconds':.1})
        case = complete['cases'][0]['case_run_id']
        artifact_base = f'/projects/p1/visual-lab/batches/{bid}/cases/{case}/artifacts/'
        images = [await api.get(artifact_base + name) for name in ['01-open','02-filled','03-confirmed']]
        record('three private authorized screenshots and cross-project denial',
            all(image.status_code == 200 and image.content[:8] == b'\x89PNG\r\n\x1a\n' and
                image.headers.get('cache-control') == 'no-store' for image in images) and
            (await api.get((artifact_base+'01-open').replace('/p1/', '/p2/'))).status_code == 404 and
            (await api.post(f'/projects/p2/visual-lab/batches/{bid}/cancel')).status_code == 404)
        if args.quick:
            ledger = await db['visual_batch_dispatch'].find_one({'_id': service.CHECK_LEDGER})
            info = await asyncio.to_thread(engine.inspect, complete['cases'][0]['case_run_id'], args.image)
            record('control container exited and capacity released', info and info['status'] == 'exited' and
                info['pid'] == 0 and all(value is None for value in ledger['slots'].values()))
            if not all(check['passed'] for check in report['checks']):
                raise RuntimeError('CONTROL_INCOMPLETE_SEE_REPORT')
            return
        # A separate five-case parent exercises cancellation; completed first batch
        # is never replayed. Reconstruct controller before cancellation recovery.
        cancelled = await create(5, secrets.token_hex(16))
        await manager.tick()
        await api.post(f"/projects/p1/visual-lab/batches/{cancelled['batch_id']}/cancel")
        manager = service.ParallelVisualBatchService(database=db, engine=engine)
        routes.visual_batches = manager
        ended = await finish(cancelled['batch_id'])
        record('five-case cancellation after controller reconstruction', ended['state'] == 'cancelled' and
            all(c['state'] in ['completed','cancelled'] for c in ended['cases']))
        ledger = await db['visual_batch_dispatch'].find_one({'_id': service.CHECK_LEDGER})
        infos = await asyncio.gather(*[asyncio.to_thread(engine.inspect, c['batch_id'], args.image)
            async for c in db['visual_batch_checks'].find({})])
        record('terminal containers and released capacity', all(v is None for v in ledger['slots'].values()) and
            all(i and i['status'] in ['exited','stopped'] and i['pid'] == 0 for i in infos))
        if not all(check['passed'] for check in report['checks']):
            raise RuntimeError('REAL_CHECKS_INCOMPLETE_SEE_REPORT')
    except Exception as exc:
        report['fixture_error'] = type(exc).__name__ if type(exc).__name__ in {'EngineError','RuntimeError'} else 'FIXTURE_ERROR'
        if getattr(exc, 'reason', None) in {'command_timeout','process_launch_failed','command_failed'}:
            report['engine_reason'] = exc.reason
        raise
    finally:
        report['batches'] = [{k:d[k] for k in ['batch_id','state','cases']}
                            async for d in db['visual_batches'].find({})]
        async for child in db['visual_batch_checks'].find({}):
            try:
                info = await asyncio.to_thread(engine.inspect, child['batch_id'], args.image)
                if info and info['status'] == 'running':
                    await asyncio.to_thread(engine.stop, child['batch_id'])
            except Exception:
                report['cleanup_unverified'] = True
        (work/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        await api.aclose()
        client.close()


if __name__ == '__main__':
    fixture.verify = verify
    fixture.main()
