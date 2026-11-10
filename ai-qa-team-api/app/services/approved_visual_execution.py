"""Explicitly launched, one-slot development executor. Interrupted runs are never replayed."""
import asyncio
from datetime import datetime, timedelta, timezone
import logging

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.models.approved_visual_run import VisualRunSelection
from app.services.approved_visual_run import ApprovedVisualRuns
from app.utils.feature_flags import require_features
from app.utils.project_authorization import require_project_member


SLOT = 'browserstack-synthetic-v1'
tasks = set()
logger = logging.getLogger(__name__)


class Stopped(Exception):
    pass


async def start(service, project_id, run_id, user):
    require_features('approved_visual_run_execution')
    if not settings.browserstack_username or not settings.browserstack_access_key:
        raise HTTPException(503, 'Configure BrowserStack credentials on the development API.')
    current = await service.status(project_id, run_id)
    if current.state != 'admitted':
        return current
    preview = await service.preview(project_id, VisualRunSelection(
        approved_test_version_id=current.test.version_id, environment_id=current.environment_id,
    ))
    if preview.preview_digest != current.preview_digest:
        raise HTTPException(409, 'Run inputs changed. Cancel this admission and preview again.')

    leases = service.db['approved_visual_execution_slots']
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=4)
    await leases.delete_one({'_id': SLOT, 'expires_at': {'$lte': now}})
    lease = {'_id': SLOT, 'run_id': run_id}
    try:
        await leases.insert_one({**lease, 'expires_at': expires})
    except DuplicateKeyError:
        raise HTTPException(409, 'The single synthetic browser slot is busy.') from None

    query = {'project_id': project_id, '_id': run_id}
    try:
        claimed = await service.db['approved_visual_runs'].find_one_and_update(
            {**query, 'run.state': 'admitted'},
            {'$set': {'run.state': 'running', 'run.execution_adapter': 'browserstack-direct-webdriver-v1',
                      'execution_expires_at': expires}},
            return_document=ReturnDocument.AFTER,
        )
        if claimed:
            task = asyncio.create_task(execute(service, query, lease, current, user))
            tasks.add(task)
            task.add_done_callback(tasks.discard)
            return ApprovedVisualRuns.read_run(claimed)
    except BaseException:
        await leases.delete_one(lease)
        raise
    await leases.delete_one(lease)
    return await service.status(project_id, run_id)


async def execute(service, query, lease, run, user):
    runs = service.db['approved_visual_runs']
    remote = None
    result = ('blocked', None, None, 'EXECUTION_INTERRUPTED')

    async def checkpoint():
        if not (settings.features.approved_visual_run_admission and
                settings.features.approved_visual_run_execution) or not await runs.find_one(
            {**query, 'run.state': 'running'}
        ):
            raise Stopped()

    try:
        async with asyncio.timeout(run.timeout_seconds):
            await checkpoint()
            await require_project_member(query['project_id'], user)
            preview = await service.preview(query['project_id'], VisualRunSelection(
                approved_test_version_id=run.test.version_id, environment_id=run.environment_id,
            ))
            if preview.preview_digest != run.preview_digest:
                raise HTTPException(409, 'Run inputs changed.')
            from app.services.synthetic_visual_browser import RemoteSyntheticBrowser
            remote = RemoteSyntheticBrowser(settings.browserstack_username, settings.browserstack_access_key)
            result = await remote.execute(run.test.button_label, run.test.expected_text, checkpoint)
    except Stopped:
        result = ('cancelled', None, None, None)
    except TimeoutError:
        result = ('needs_review', None, None, 'EXECUTION_TIMEOUT')
    except Exception:
        result = ('blocked', None, None, 'SYNTHETIC_EXECUTION_UNAVAILABLE')
    finally:
        cleanup = remote is None
        if remote:
            try:
                async with asyncio.timeout(15):
                    await remote.close()
                cleanup = remote.cleanup_confirmed
            except Exception:
                cleanup = False
        try:
            verdict, observed, evidence, reason = result
            if not cleanup:
                if verdict != 'cancelled':
                    verdict = 'needs_review'
                reason = 'REMOTE_CLEANUP_UNCONFIRMED'
            fields = {'run.state': 'cancelled' if verdict == 'cancelled' else 'completed',
                      'run.verdict': verdict, 'run.observed_text': observed,
                      'run.reason': reason, 'run.evidence_available': evidence is not None}
            if evidence is not None:
                fields['evidence_png'] = evidence
            await runs.update_one({**query, 'run.state': 'running'}, {'$set': fields})
            await runs.update_one({**query, 'run.state': 'cancelling'}, {'$set': {
                'run.state': 'cancelled', 'run.verdict': 'cancelled',
                'run.reason': None if cleanup else 'REMOTE_CLEANUP_UNCONFIRMED',
            }})
        except Exception:
            logger.warning('Synthetic visual execution result could not be persisted.')
        finally:
            if cleanup:
                try:
                    await service.db['approved_visual_execution_slots'].delete_one(lease)
                except Exception:
                    logger.warning('Synthetic visual execution slot will expire.')


async def shutdown():
    active = tuple(tasks)
    for task in active:
        task.cancel()
    await asyncio.gather(*active, return_exceptions=True)
