"""Opt-in real runner through HTTP/service, with isolated in-memory Mongo protocol doubles."""
import asyncio
import copy
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_visual_lab import TEST_ENV
with patch.dict(os.environ, TEST_ENV):
    from app.config import settings, FeatureFlags
    from app.services import visual_lab_service as service
    from app.routes import visual_lab_routes as routes
    from app.utils.auth_dependency import get_current_user

from fastapi import FastAPI, HTTPException
import httpx
from pymongo.errors import DuplicateKeyError


def match(doc, query):
    for key, value in query.items():
        if key == '$or':
            if not any(match(doc, item) for item in value): return False
        elif isinstance(value, dict):
            if '$in' in value and doc.get(key) not in value['$in']: return False
            if '$lt' in value and (doc.get(key) is None or doc[key] >= value['$lt']): return False
        elif doc.get(key) != value: return False
    return True


class Collection:
    def __init__(self): self.docs = []
    async def insert_one(self, doc): self.docs.append(copy.deepcopy(doc))
    async def find_one(self, query): return next((copy.deepcopy(d) for d in self.docs if match(d, query)), None)
    async def update_one(self, query, update):
        for doc in self.docs:
            if match(doc, query): doc.update(copy.deepcopy(update['$set'])); break
    async def find_one_and_update(self, query, update, **_):
        doc = next((d for d in self.docs if match(d, query)), None)
        if doc is None:
            if any(d['_id'] == query['_id'] for d in self.docs): raise DuplicateKeyError('busy')
            doc = {'_id': query['_id']}; self.docs.append(doc)
        doc.update(copy.deepcopy(update['$set']))
        return copy.deepcopy(doc)


@unittest.skipUnless(os.environ.get('VISUAL_LAB_BROWSER_TESTS') == '1', 'Opt-in controlled local browser check')
class BrowserServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_start_observe_artifacts_cancel_complete_and_persistence(self):
        database = {key: Collection() for key in ('visual_lab_runs', 'visual_lab_locks')}
        manager = service.VisualLabService()
        app = FastAPI()
        app.include_router(routes.router)
        async def user(): return {'email': 'synthetic-member@example.test'}
        app.dependency_overrides[get_current_user] = user
        async def member(project, _):
            if project not in {'p1', 'p2'}: raise HTTPException(404, 'No access')
        with patch.object(settings, 'features', FeatureFlags(visual_runner_lab=True)), \
             patch.object(settings, 'app_env', 'test'), \
             patch.object(settings, 'visual_runner_chrome', os.environ['LAB_TEST_CHROME']), \
             patch.object(settings, 'visual_runner_driver', os.environ['LAB_TEST_DRIVER']), \
             patch.object(service, 'db', database), patch.object(service, 'visual_lab', manager), \
             patch.object(routes, 'visual_lab', manager), patch.object(routes, 'require_project_member', member):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                base = '/projects/p1/visual-lab/runs'
                try:
                    response = await client.post(base, json={'headed': False})
                    self.assertEqual(response.status_code, 202, response.text)
                    run_id = response.json()['run_id']
                    self.assertNotIn('chrome', response.text)
                    self.assertNotIn('created_by', response.json())
                    duplicate = await client.post('/projects/p2/visual-lab/runs', json={})
                    self.assertEqual(duplicate.status_code, 409)
                    self.assertEqual((await client.get('/projects/p2/visual-lab/runs/'+run_id)).status_code, 404)
                    async def wait_for(predicate, run):
                        deadline = time.monotonic() + 70
                        while time.monotonic() < deadline:
                            result = (await client.get(base+'/'+run)).json()
                            if predicate(result): return result
                            if result['state'] in service.TERMINAL:
                                self.fail(f'Runner stopped before expected observation: {result}')
                            await asyncio.sleep(.3)
                        self.fail('Runner did not reach expected lifecycle')
                    observed = await wait_for(lambda r: bool(r['screenshots']), run_id)
                    image = await client.get(base+'/'+run_id+'/artifacts/'+observed['screenshots'][0])
                    self.assertEqual(image.status_code, 200)
                    self.assertTrue(image.content.startswith(b'\x89PNG'))
                    self.assertEqual((await client.get('/projects/p2/visual-lab/runs/'+run_id+'/artifacts/01-open')).status_code, 404)
                    self.assertEqual((await client.post(base+'/'+run_id+'/cancel')).status_code, 200)
                    cancelled = await wait_for(lambda r: r['state'] in service.TERMINAL, run_id)
                    self.assertEqual(cancelled['state'], 'cancelled')
                    await asyncio.gather(*list(manager.tasks))
                    response = await client.post(base, json={'headed': False})
                    self.assertEqual(response.status_code, 202, response.text)
                    second = response.json()['run_id']
                    finished = await wait_for(lambda r: r['state'] in service.TERMINAL, second)
                    self.assertEqual(finished['state'], 'completed', finished)
                    self.assertEqual(len(finished['screenshots']), 3)
                    # A new manager can inspect durable documents/files without replaying the browser.
                    restored = await service.VisualLabService().reconcile(second, 'p1')
                    self.assertEqual(restored.state, 'completed')
                    self.assertEqual(len(database['visual_lab_runs'].docs), 2)
                finally:
                    await manager.shutdown()


if __name__ == '__main__': unittest.main()
