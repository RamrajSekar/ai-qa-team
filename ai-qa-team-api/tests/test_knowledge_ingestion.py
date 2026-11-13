"""Temporary private files, Mongo/auth/model doubles; no cloud or provider calls."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from app.config import settings, FeatureFlags, KnowledgeIngestionSettings
from app.routes import product_knowledge_routes as routes
from app.services.knowledge_ingestion import KnowledgeIngestion, PrivateDevelopmentStore
from app.workers import knowledge_ingestion_worker as worker
from test_manual_results import Collection as BaseCollection


class Collection(BaseCollection):
    @staticmethod
    def matches(doc, query):
        return all((doc.get(key) is not None and doc[key]<value['$lt']) if isinstance(value,dict) and '$lt' in value else BaseCollection.matches(doc,{key:value}) for key,value in query.items())

    async def update_many(self, query, update):
        for doc in self.docs:
            if self.matches(doc,query):doc.update(update.get('$set',{}))

    async def update_one(self, query, update, **kwargs):
        matched = any(self.matches(doc, query) for doc in self.docs)
        await super().update_one(query, update, **kwargs)
        return SimpleNamespace(matched_count=int(matched))


class IngestionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.db = {key:Collection() for key in ('knowledge_ingestion_jobs','product_knowledge_sources','prompt_definitions')}
        config = KnowledgeIngestionSettings(storage_backend='local_dev',local_private_root=self.temp.name,allow_local_development=True,infrastructure_verified=True,max_upload_bytes=1024,decoder_engine='fixture-engine',decoder_image='fixture-image:local')
        self.user={'_id':'U1','email':'fixture@example.test','role':'ADMIN'}
        async def member(project,user):
            if project!='P1': raise __import__('fastapi').HTTPException(404,'Access denied')
        async def admin(project,user):
            await member(project,user)
            if user['role']!='ADMIN': raise __import__('fastapi').HTTPException(403,'Admin required')
        for target,key,value in ((settings,'features',FeatureFlags(product_knowledge=True,knowledge_uploads=True,knowledge_media_processing=True,knowledge_image_interpretation=True)),
            (settings,'knowledge_ingestion',config),(settings,'app_env','test'),(routes,'db',self.db),(routes,'require_project_member',member),(routes,'require_project_admin',admin),(worker,'require_project_member',member)):
            context=patch.object(target,key,value);context.start();self.addCleanup(context.stop)
        app=FastAPI();app.include_router(routes.router);app.dependency_overrides[routes.get_current_user]=lambda:self.user
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test');self.addAsyncCleanup(self.client.aclose)
        self.base='/projects/P1/knowledge/uploads';self.content=b'Synthetic product guide.'

    async def admit(self,**fields):
        return await self.client.post(self.base,json={'title':'Synthetic source','format':'txt','size_bytes':len(self.content),'sha256':hashlib.sha256(self.content).hexdigest(),**fields})

    async def test_disabled_and_unqualified_admission_stop_before_files_or_jobs(self):
        settings.features.knowledge_uploads=False
        self.assertEqual((await self.admit()).status_code,403)
        settings.features.knowledge_uploads=True;settings.knowledge_ingestion.infrastructure_verified=False
        self.assertEqual((await self.admit()).status_code,503)
        self.assertEqual(self.db['knowledge_ingestion_jobs'].docs,[])
        self.assertEqual(list(Path(self.temp.name).iterdir()),[])
        self.assertFalse(FeatureFlags().knowledge_uploads);self.assertFalse(FeatureFlags().knowledge_media_processing)

    async def test_stream_checksum_private_status_and_cross_project_guards(self):
        admitted=await self.admit();self.assertEqual(admitted.status_code,201,admitted.text);identity=admitted.json()['upload_id']
        response=await self.client.put(self.base+'/'+identity+'/content',content=self.content,headers={'content-type':'application/octet-stream'})
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['state'],'queued')
        self.assertNotIn(self.temp.name,response.text);self.assertNotIn(self.user['email'],response.text)
        self.assertEqual(response.headers['cache-control'],'private, no-store')
        self.assertEqual((await self.client.put(self.base+'/'+identity+'/content',content=self.content,headers={'content-type':'application/octet-stream'})).status_code,409)
        for suffix in ['', '/images/'+'a'*32]:
            self.assertEqual((await self.client.get(self.base.replace('/P1/','/P2/')+'/'+identity+suffix)).status_code,404)
        self.assertEqual((await self.client.delete(self.base.replace('/P1/','/P2/')+'/'+identity)).status_code,404)

    async def test_rejected_content_is_deleted_and_consent_cannot_be_bypassed(self):
        self.assertEqual((await self.admit(format='mp4')).status_code,422)
        self.assertEqual((await self.admit(interpret_images=True)).status_code,422)
        identity=(await self.admit()).json()['upload_id']
        response=await self.client.put(self.base+'/'+identity+'/content',content=b'wrong',headers={'content-type':'application/octet-stream'})
        self.assertEqual(response.status_code,422)
        self.assertFalse((PrivateDevelopmentStore().folder('P1',identity)/'input').exists())
        self.assertEqual((await self.client.get(self.base+'/'+identity)).json()['state'],'failed')
        self.assertEqual((await self.admit(size_bytes=2048)).status_code,413)
        self.assertEqual((await self.client.get(self.base+'/../../private')).status_code,404)

    async def test_authorized_images_expiry_deletion_and_processing_cancellation(self):
        identity=(await self.admit()).json()['upload_id'];folder=PrivateDevelopmentStore().folder('P1',identity)
        image='a'*32;(folder/(image+'.png')).write_bytes(b'\x89PNG\r\n\x1a\nsynthetic')
        row=self.db['knowledge_ingestion_jobs'].docs[0];row.update(state='ready',images=[{'image_id':image,'page':1}])
        response=await self.client.get(self.base+'/'+identity+'/images/'+image)
        self.assertEqual(response.status_code,200);self.assertEqual(response.headers['x-content-type-options'],'nosniff')
        row['expires_at']='2000-01-01T00:00:00+00:00';self.assertEqual((await self.client.get(self.base+'/'+identity+'/images/'+image)).status_code,404)
        row['state']='processing';response=await self.client.delete(self.base+'/'+identity)
        self.assertEqual(response.json()['state'],'cancelling');self.assertTrue((folder/'cancel').exists())
        row['state']='blocked';settings.features.knowledge_uploads=False
        self.assertEqual((await self.client.delete(self.base+'/'+identity)).json()['state'],'deleted')
        self.assertEqual(list(folder.iterdir()),[])

    async def test_worker_creates_unapproved_page_sources_without_ai_or_approval(self):
        identity=(await self.admit()).json()['upload_id'];job=self.db['knowledge_ingestion_jobs'].docs[0]
        job.update(state='processing',lease_owner='owner')
        decoder=AsyncMock(return_value={'pages':[{'page':1,'text':'Synthetic page one.'}],'images':[]})
        factory=AsyncMock()
        result=await worker.process_job(self.db,job,self.user,PrivateDevelopmentStore(),decoder=decoder,usage_factory=factory)
        self.assertEqual(len(result['source_ids']),1);factory.assert_not_called()
        source=self.db['product_knowledge_sources'].docs[0]
        self.assertEqual(source['origin']['page_number'],1);self.assertEqual(source['origin']['upload_id'],identity)
        self.assertNotIn('approved_at',source)

    async def test_expiry_and_interrupted_leases_are_not_replayed_with_intake_disabled(self):
        from datetime import datetime,timezone
        identity=(await self.admit()).json()['upload_id'];folder=PrivateDevelopmentStore().folder('P1',identity)
        (folder/'input').write_bytes(self.content)
        row=self.db['knowledge_ingestion_jobs'].docs[0];row.update(state='processing',lease_expires_at='2000-01-01T00:00:00+00:00')
        settings.features.knowledge_uploads=False
        await KnowledgeIngestion(self.db).reconcile_and_expire(datetime.now(timezone.utc))
        self.assertEqual(row['state'],'blocked');self.assertEqual(row['error_code'],'INTERRUPTED_NO_REPLAY')
        row['expires_at']='2000-01-01T00:00:00+00:00'
        await KnowledgeIngestion(self.db).reconcile_and_expire(datetime.now(timezone.utc))
        self.assertEqual(row['state'],'deleted');self.assertFalse((folder/'input').exists())

    async def test_image_observations_retain_page_image_and_prompt_provenance(self):
        from PIL import Image
        identity=(await self.admit(format='pdf',consent_ai=True,interpret_images=True)).json()['upload_id'];job=self.db['knowledge_ingestion_jobs'].docs[0]
        job.update(state='processing',lease_owner='owner');folder=PrivateDevelopmentStore().folder('P1',identity)
        image_id='a'*32;Image.new('RGB',(4,4),'blue').save(folder/(image_id+'.png'))
        decoder=AsyncMock(return_value={'pages':[{'page':1,'text':'Synthetic page.'}],'images':[{'image_id':image_id,'page':1}]})
        usage=SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(text='Observed blue synthetic control.')))
        result=await worker.process_job(self.db,job,self.user,PrivateDevelopmentStore(),decoder=decoder,usage_factory=lambda **kwargs:usage)
        self.assertEqual(len(result['source_ids']),2)
        source=self.db['product_knowledge_sources'].docs[-1]
        self.assertEqual(source['origin']['page_number'],1);self.assertEqual(source['origin']['image_id'],image_id)
        self.assertEqual(source['origin']['prompt_key'],'MEDIA_IMAGE_OBSERVATION_V1')
        self.assertEqual(usage.execute.call_args.args[0].value,'MEDIA_IMAGE_OBSERVATION')

    def test_container_command_has_restricted_runtime_and_server_owned_mount(self):
        command=worker.decoder_command(settings.knowledge_ingestion,Path(self.temp.name),'a'*32,10001,10001)
        self.assertEqual(command[command.index('--network')+1],'none')
        self.assertIn('--read-only',command);self.assertIn('no-new-privileges',command);self.assertIn('--pull=never',command)
        self.assertEqual(command[command.index('--cap-drop')+1],'ALL')
        self.assertNotIn('--privileged',command);self.assertNotIn('--env-file',command)
        self.assertEqual(command[command.index('--name')+1],'qa-knowledge-'+'a'*32)
        with self.assertRaises(RuntimeError):worker.decoder_command(settings.knowledge_ingestion,Path(self.temp.name),'a'*32,0,0)
        with self.assertRaises(RuntimeError):worker.decoder_command(settings.knowledge_ingestion,Path(self.temp.name),'../../private',10001,10001)
