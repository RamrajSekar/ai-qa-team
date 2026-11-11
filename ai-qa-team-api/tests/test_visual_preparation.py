"""Preparation regressions with explicit engine/DB doubles; no live services."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import test_visual_batches as fixture  # Reuse isolated import configuration only.
from app.models.visual_batch_model import PreparationDiagnostics
from app.services.visual_batch_engine import EngineError, PodmanBatchEngine
from app.services.visual_batch_service import VisualBatchService, ParallelVisualBatchService


class EngineStages(unittest.TestCase):
    def test_each_prepare_failure_identifies_stage_without_raw_output(self):
        stages = ['image_lookup', 'volume_create', 'container_create', 'manifest_copy']
        for failure in range(4):
            with self.subTest(stage=stages[failure]), patch('app.services.visual_batch_engine.Path.is_file', return_value=True):
                engine = PodmanBatchEngine('fixture')
                events = []
                counter = 0
                def command(*args):
                    nonlocal counter
                    index = counter
                    counter += 1
                    if index == failure:
                        raise EngineError('ENGINE_UNAVAILABLE', reason='command_timeout')
                    return ''
                engine.command = command
                with self.assertRaises(EngineError):
                    engine.prepare('a'*32, 'b'*64, Path('private-canary'),
                        progress=lambda *event: events.append(event))
                self.assertEqual(events[-1][0:2], (stages[failure], 'failed'))
                self.assertEqual(events[-1][3], 'command_timeout')
                self.assertNotIn('private-canary', json.dumps(events))


class DurablePreparation(unittest.IsolatedAsyncioTestCase):
    async def test_first_error_survives_launch_and_interruption(self):
        with patch('app.services.visual_batch_engine.Path.is_file', return_value=True):
            engine = PodmanBatchEngine('fixture')
        engine.command = MagicMock(side_effect=['', EngineError('ENGINE_UNAVAILABLE', reason='command_failed')])
        manager = VisualBatchService()
        manager.save = AsyncMock()
        doc = {'_id':'a'*32, 'batch_id':'a'*32, 'image_id':'b'*64, 'manifest':{},
               'cases':[{'case_run_id':'a'*32, 'state':'queued'}]}
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[2]/'tmp') as folder:
            with patch('app.services.visual_batch_service.ROOT', Path(folder)):
                await manager.launch(doc, doc, engine)
        saved = manager.save.await_args.args[1]
        self.assertEqual(saved['preparation']['error_stage'], 'volume_create')
        self.assertEqual(saved['preparation']['reason'], 'command_failed')
        self.assertEqual(saved['diagnostic_code'], 'ENGINE_UNAVAILABLE')
        await manager.finish_interrupted({**doc, **saved})
        final = manager.save.await_args.args[1]
        self.assertEqual(final['diagnostic_code'], 'ENGINE_UNAVAILABLE')
        self.assertEqual(final['cases'][0]['preparation'], saved['preparation'])
        self.assertEqual(final['cases'][0]['diagnostic_code'], 'ENGINE_UNAVAILABLE')

    async def test_parent_retains_child_error_and_typed_diagnostics(self):
        database = MagicMock()
        collection = database.__getitem__.return_value
        prep = PreparationDiagnostics(stage='manifest_copy', error_stage='manifest_copy', reason='command_timeout').model_dump(mode='json')
        child = {'batch_id':'a'*32, 'state':'interrupted', 'diagnostic_code':'ENGINE_UNAVAILABLE',
                 'preparation':prep, 'cases':[{'case_run_id':'a'*32, 'state':'not_executed', 'screenshots':[]}]}
        collection.find.return_value.to_list = AsyncMock(return_value=[child])
        collection.update_one = AsyncMock()
        manager = ParallelVisualBatchService(database=database)
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[2]/'tmp') as folder:
            with patch('app.services.visual_batch_service.ROOT', Path(folder)):
                await manager.sync_parent({'_id':'parent', 'batch_id':'b'*32, 'cancel_requested':False,
                                           'cases':[{'case_run_id':'a'*32}]})
        case = collection.update_one.await_args.args[1]['$set']['cases'][0]
        self.assertEqual(case['diagnostic_code'], 'ENGINE_UNAVAILABLE')
        self.assertEqual(case['preparation'], prep)

    async def test_process_loss_keeps_last_durable_stage(self):
        manager = VisualBatchService()
        manager.save = AsyncMock()
        prep = PreparationDiagnostics(stage='container_create').model_dump(mode='json')
        await manager.finish_interrupted({'cases':[{'state':'queued'}], 'preparation':prep})
        saved = manager.save.await_args.args[1]
        self.assertEqual(saved['diagnostic_code'], 'DISPATCH_INTERRUPTED')
        self.assertEqual(saved['cases'][0]['preparation']['stage'], 'container_create')
        self.assertIsNone(saved['cases'][0]['preparation']['reason'])


if __name__ == '__main__':
    unittest.main()
