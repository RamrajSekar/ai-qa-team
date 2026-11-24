import json
"""HTTP/auth/database/transaction doubles; not live Jira or Mongo transaction proof."""
import asyncio
import base64
from copy import deepcopy
from datetime import timedelta
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import httpx
import test_product_knowledge as fixtures
from fastapi import FastAPI,HTTPException
from pymongo.errors import DuplicateKeyError
from app.config import settings,FeatureFlags
from app.routes import jira_routes
from app.services.jira_story_import import JiraStoryImport,now,text_value
from app.models.jira_import import JiraPreview,JiraApply


def get(doc,key):
    for part in key.split('.'):
        if not isinstance(doc,dict):return None
        doc=doc.get(part)
    return doc


def matches(doc,query):
    for key,value in query.items():
        actual=get(doc,key)
        if isinstance(value,dict) and '$lt' in value:
            if actual is None or actual>=value['$lt']:return False
        elif isinstance(value,dict) and '$gt' in value:
            if actual is None or actual<=value['$gt']:return False
        elif actual!=value:return False
    return True


class Collection:
    def __init__(self):self.docs=[]
    async def find_one(self,query,**kwargs):return deepcopy(next((doc for doc in self.docs if matches(doc,query)),None))
    async def insert_one(self,doc,**kwargs):
        if any(item.get('_id')==doc.get('_id') for item in self.docs):raise DuplicateKeyError('duplicate')
        self.docs.append(deepcopy(doc))
    async def update_one(self,query,update,**kwargs):
        row=next((doc for doc in self.docs if matches(doc,query)),None)
        if row is None:return SimpleNamespace(matched_count=0,modified_count=0)
        for operation,items in update.items():
            for key,value in items.items():
                target=row;parts=key.split('.')
                for part in parts[:-1]:target=target.setdefault(part,{})
                target[parts[-1]]=deepcopy(value) if operation=='$set' else target.get(parts[-1],0)+value
        return SimpleNamespace(matched_count=1,modified_count=1)
    async def find_one_and_update(self,query,update,**kwargs):
        if await self.find_one(query) is None and kwargs.get('upsert'):self.docs.append(dict(query))
        original=await self.find_one(query)
        await self.update_one(query,update)
        return await self.find_one({"_id":original["_id"]}) if original else None


class DB(dict):
    def __missing__(self,key):self[key]=Collection();return self[key]


class JiraTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db=DB();self.user={'_id':'user-a','email':'a@example.test','platform_role':'OWNER'}
        self.db['users'].docs=[{**self.user,'account_id':'ACC_A','account_state':'ACTIVE','account_role':'OWNER'}]
        self.db['customer_accounts'].docs=[{'_id':'ACC_A','status':'ACTIVE','billing_version':1,'subscription':{'status':'active','limits':{'stories_limit':10},'usage':{'stories_used':0}}}]
        self.db['projects'].docs=[{'_id':'project-a','project_id':'P1','account_id':'ACC_A'},{'project_id':'P2','account_id':'ACC_B'}]
        self.db['project_memberships'].docs=[{'project_id':'P1','account_id':'ACC_A','email':self.user['email'],'status':'ACTIVE','role':'ADMIN'}]
        self.requests=[];self.remote={}
        self.cloud='11111111-1111-4111-8111-111111111111'
        def handler(request):
            self.requests.append(request)
            if request.url.path.endswith('/myself'):return httpx.Response(200,json={'accountId':'jira-user'})
            if request.url.path.endswith('/serverInfo'):return httpx.Response(200,json={'baseUrl':'https://sample.atlassian.net'})
            key=request.url.path.split('/')[-1]
            return httpx.Response(200,json=self.remote[key]) if key in self.remote else httpx.Response(404,json={'error':'PRIVATE_CANARY'})
        lock=asyncio.Lock()
        async def transaction(work):
            async with lock:
                before=deepcopy(self.db)
                try:return await work(None)
                except BaseException:self.db.clear();self.db.update(before);raise
        self.service=JiraStoryImport(self.db,transport=httpx.MockTransport(handler),transaction=transaction)
        for target,name,value in ((settings,'features',FeatureFlags(jira_story_import=True,story_management=True,product_knowledge=True,story_analysis=True)),
            (settings,'jira_secret_master_key',base64.urlsafe_b64encode(b'K'*32).decode()),(jira_routes,'service',lambda:self.service)):
            p=patch.object(target,name,value);p.start();self.addCleanup(p.stop)
        app=FastAPI();self.app=app;app.include_router(jira_routes.router);app.dependency_overrides[jira_routes.get_current_user]=lambda:self.user
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test');self.addAsyncCleanup(self.client.aclose)
        self.base='/projects/P1/jira'
        self.config={'expected_revision':0,'cloud_id':self.cloud,'site':'sample.atlassian.net','project_key':'APP','email':'jira@example.com','api_token':'TEST_TOKEN_CANARY','acceptance_field':'customfield_10001'}

    async def connect(self):
        # Existing encrypted token records remain readable. No production setup API.
        await self.service.scope('P1',self.user,admin=True)
        import os
        identity=self.service.key('ACC_A','P1');nonce=os.urandom(12)
        encrypted=self.service.cipher().encrypt(nonce,json.dumps({'email':'jira@example.com','token':'TEST_TOKEN_CANARY'}).encode(),identity.encode())
        row={'_id':identity,'account_id':'ACC_A','project_id':'P1','cloud_id':self.cloud,'site':'sample.atlassian.net',
             'project_key':'APP','acceptance_field':'customfield_10001','revision':1,'connected':True,
             'nonce':base64.b64encode(nonce).decode(),'credentials':base64.b64encode(encrypted).decode()}
        self.db['jira_connections'].docs=[row]
        return self.service.public(row)

    def issue(self,key='APP-1',description='Original description'):
        self.remote[key]={'id':key.split('-')[1],'key':key,'fields':{'summary':'Story '+key,'description':{'type':'doc','content':[{'type':'paragraph','content':[{'type':'text','text':description}]}]},'customfield_10001':'Show confirmation.','updated':'2026-11-15'}}

    async def preview(self,keys=None):return await self.service.preview('P1',self.user,JiraPreview(issue_keys=keys or ['APP-1']))

    def selection(self,preview,fields=None):return JiraApply(preview_id=preview['preview_id'],reviewed=True,selections=[{'issue_id':item['issue_id'],'fields':fields or ['title','description','acceptance_criteria']} for item in preview['items']])

    async def test_encrypted_connection_public_status_and_disabled_guards(self):
        result=await self.connect();self.assertTrue(result['connected']);await self.service.read(self.db['jira_connections'].docs[0],'myself')
        self.assertNotIn('CANARY',str(self.db['jira_connections'].docs));self.assertNotIn('jira@example',str(self.db['jira_connections'].docs))
        self.assertNotIn('credentials',result)
        self.assertTrue(all(request.method=='GET' and request.url.host=='api.atlassian.com' for request in self.requests))
        settings.features.jira_story_import=False
        self.assertEqual((await self.client.get(self.base+'/connection')).status_code,403)
        self.assertEqual((await self.client.post(self.base+'/preview',json={'issue_keys':['APP-1']})).status_code,403)

    async def test_preview_apply_is_idempotent_and_never_writes_jira(self):
        await self.connect();self.issue();preview=await self.preview();self.assertEqual(self.db['stories'].docs,[])
        calls=len(self.requests);result=await self.service.apply('P1',self.user,self.selection(preview))
        self.assertEqual(result['stories'][0]['story_id'],'S001');self.assertEqual(self.db['customer_accounts'].docs[0]['subscription']['usage']['stories_used'],1)
        self.assertEqual(await self.service.apply('P1',self.user,self.selection(preview)),result)
        self.assertEqual(len(self.requests),calls);self.assertEqual(len(self.db['stories'].docs),1)
        self.assertEqual(self.db['stories'].docs[0]['status'],'pending')

    async def test_reimport_preserves_unselected_local_edits_and_detects_race(self):
        await self.connect();self.issue();await self.service.apply('P1',self.user,self.selection(await self.preview()))
        self.db['stories'].docs[0]['title']='Local title';self.issue(description='Updated remote description')
        preview=await self.preview();self.assertIn('title',preview['items'][0]['conflicts'])
        await self.service.apply('P1',self.user,self.selection(preview,['description']))
        self.assertEqual(self.db['stories'].docs[0]['title'],'Local title')
        self.assertEqual(self.db['stories'].docs[0]['description'],'Updated remote description')
        preview=await self.preview();self.db['stories'].docs[0]['description']='Edited after preview'
        with self.assertRaises(HTTPException) as error:await self.service.apply('P1',self.user,self.selection(preview,['description']))
        self.assertEqual(error.exception.status_code,409)

    async def test_quota_failure_rolls_back_entire_import_and_counter(self):
        await self.connect();self.issue();self.issue('APP-2');self.db['customer_accounts'].docs[0]['subscription']['limits']['stories_limit']=1
        preview=await self.preview(['APP-1','APP-2'])
        with self.assertRaises(HTTPException) as error:await self.service.apply('P1',self.user,self.selection(preview))
        self.assertEqual(error.exception.status_code,403);self.assertEqual(self.db['stories'].docs,[])
        self.assertEqual(self.db['customer_accounts'].docs[0]['subscription']['usage']['stories_used'],0)

    async def test_duplicate_previews_cannot_create_duplicate_stories(self):
        await self.connect();self.issue();first=await self.preview();second=await self.preview()
        results=await asyncio.gather(self.service.apply('P1',self.user,self.selection(first)),self.service.apply('P1',self.user,self.selection(second)),return_exceptions=True)
        self.assertEqual(sum(isinstance(item,HTTPException) for item in results),1)
        self.assertEqual(len(self.db['stories'].docs),1);self.assertEqual(self.db['customer_accounts'].docs[0]['subscription']['usage']['stories_used'],1)

    async def test_tenant_admin_project_restrictions_before_credentials_or_http(self):
        await self.connect();calls=len(self.requests)
        with self.assertRaises(HTTPException):await self.service.preview('P2',self.user,JiraPreview(issue_keys=['APP-1']))
        with self.assertRaises(HTTPException):await self.service.preview('P1',self.user,JiraPreview(issue_keys=['OTHER-1']))
        self.db['users'].docs[0]['account_role']='MEMBER'
        with self.assertRaises(HTTPException) as error:await self.connect()
        self.assertEqual(error.exception.status_code,403);self.assertEqual(len(self.requests),calls)

    async def test_expiry_rotation_bad_secret_and_error_sanitization(self):
        await self.connect();self.issue();preview=await self.preview();self.db['jira_import_previews'].docs[0]['expires_at']=now()-timedelta(seconds=1)
        with self.assertRaises(HTTPException):await self.service.apply('P1',self.user,self.selection(preview))
        response=await self.client.post(self.base+'/preview',json={'issue_keys':['APP-404']})
        self.assertEqual(response.status_code,502);self.assertNotIn('PRIVATE_CANARY',response.text)
        settings.jira_secret_master_key=None
        with self.assertRaises(HTTPException) as error:await self.preview()
        self.assertEqual(error.exception.status_code,503)

    async def test_bounded_adf_and_client_payload_rejection(self):
        text,warnings=text_value({'type':'doc','content':[{'type':'media','attrs':{'url':'http://metadata.invalid'}},{'type':'paragraph','content':[{'type':'text','text':'Safe text'}]}]})
        self.assertEqual(text,'Safe text');self.assertTrue(warnings)
        with self.assertRaises(HTTPException):text_value('x'*30001)
        response=await self.client.post(self.base+'/connection',json={**self.config,'site':'127.0.0.1','extra':'PRIVATE_CANARY'})
        self.assertEqual(response.status_code,405);self.assertNotIn('PRIVATE_CANARY',response.text)

    async def test_http_connection_and_disconnect_invalidate_preview(self):
        from app.models.jira_import import JiraRevision
        response=await self.client.post(self.base+'/connection',json=self.config)
        self.assertEqual(response.status_code,405,response.text)
        await self.connect();self.issue();preview=await self.preview()
        await self.service.disconnect('P1',self.user,JiraRevision(expected_revision=1))
        with self.assertRaises(HTTPException) as error:
            await self.service.apply('P1',self.user,self.selection(preview))
        self.assertEqual(error.exception.status_code,409)
        self.assertEqual(self.db['jira_connections'].docs[0]['credentials'],None)
        self.assertEqual(self.db['stories'].docs,[])

    async def test_token_setup_is_absent_from_flags_and_openapi(self):
        self.assertNotIn('jira_api_token_setup',FeatureFlags.model_fields)
        schema=self.app.openapi()
        self.assertNotIn('post',schema['paths']['/projects/{project_id}/jira/connection'])
        self.assertNotIn('JiraConnection',schema.get('components',{}).get('schemas',{}))
        self.assertEqual(self.requests,[])
