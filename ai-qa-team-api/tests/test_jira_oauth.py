"""Synthetic OAuth transport and database; never live Atlassian credentials."""
import asyncio
from datetime import timedelta
from unittest.mock import patch
import httpx
import test_jira_story_import as fixture
from app.config import settings
from app.models.jira_import import JiraOAuthStart, JiraOAuthComplete, JiraOAuthGrant, JiraOAuthSelect
from app.services.jira_oauth import JiraOAuth
from app.services.jira_story_import import now
from fastapi import HTTPException


class OAuthTests(fixture.JiraTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        for name,value in {'jira_oauth_client_id':'test-client','jira_oauth_client_secret':'CLIENT_CANARY',
            'jira_oauth_redirect_uri':'http://localhost:3000/jira/callback'}.items():
            item=patch.object(settings,name,value);item.start();self.addCleanup(item.stop)
        self.oauth_requests=[]
        def handler(request):
            self.oauth_requests.append(request)
            if request.url.host=='auth.atlassian.com':return httpx.Response(200,json={'access_token':'ACCESS_CANARY','expires_in':3600})
            if request.url.path.endswith('accessible-resources'):return httpx.Response(200,json=[{'id':self.cloud,'url':'https://sample.atlassian.net','scopes':['read:jira-work','read:jira-user']}])
            if request.url.path.endswith('project/search'):return httpx.Response(200,json={'values':[{'key':'APP','name':'Application'}],'isLast':True})
            if '/issue/' in request.url.path:return httpx.Response(200,json=self.remote['APP-1'])
            return httpx.Response(500,json={'secret':'PRIVATE_CANARY'})
        self.oauth=JiraOAuth(self.db,transport=httpx.MockTransport(handler))

    async def flow(self):
        start=await self.oauth.start('P1',self.user,JiraOAuthStart(expected_revision=0))
        payload=JiraOAuthComplete(state=start['state'],code='CODE_CANARY')
        return start,payload

    async def test_oauth_selects_discovered_site_project_and_import_uses_bearer(self):
        start,payload=await self.flow();self.assertIn('read%3Ajira-work',start['authorization_url'])
        grant=await self.oauth.complete('P1',self.user,payload)
        self.assertNotIn('ACCESS_CANARY',str(self.db));self.assertNotIn('CODE_CANARY',str(self.db))
        choice=JiraOAuthGrant(grant_id=grant['grant_id'],cloud_id=self.cloud)
        self.assertEqual((await self.oauth.projects('P1',self.user,choice))['projects'][0]['key'],'APP')
        result=await self.oauth.select('P1',self.user,JiraOAuthSelect(**choice.model_dump(),project_key='APP'))
        self.assertEqual(result['auth_type'],'oauth');self.assertNotIn('credentials',result)
        self.issue();await self.oauth.preview('P1',self.user,fixture.JiraPreview(issue_keys=['APP-1']))
        self.assertEqual(self.oauth_requests[-1].headers['Authorization'],'Bearer ACCESS_CANARY')
        self.assertTrue(all(request.url.host in ('auth.atlassian.com','api.atlassian.com') for request in self.oauth_requests))

    async def test_replayed_simultaneous_and_expired_callback_stop_before_exchange(self):
        _,payload=await self.flow()
        outcomes=await asyncio.gather(self.oauth.complete('P1',self.user,payload),self.oauth.complete('P1',self.user,payload),return_exceptions=True)
        self.assertEqual(sum(isinstance(value,HTTPException) for value in outcomes),1)
        self.assertEqual(sum(request.url.host=='auth.atlassian.com' for request in self.oauth_requests),1)
        _,payload=await self.flow();self.db['jira_oauth_flows'].docs[-1]['expires_at']=now()-timedelta(seconds=1)
        with self.assertRaises(HTTPException):await self.oauth.complete('P1',self.user,payload)
        self.assertEqual(sum(request.url.host=='auth.atlassian.com' for request in self.oauth_requests),1)

    async def test_foreign_project_user_and_unlisted_site_cannot_bind_grant(self):
        _,payload=await self.flow()
        with self.assertRaises(HTTPException):await self.oauth.complete('P2',self.user,payload)
        with self.assertRaises(HTTPException):await self.oauth.complete('P1',{**self.user,'_id':'other-user'},payload)
        self.assertEqual(self.oauth_requests,[])
        grant=await self.oauth.complete('P1',self.user,payload)
        with self.assertRaises(HTTPException):await self.oauth.projects('P1',self.user,JiraOAuthGrant(grant_id=grant['grant_id'],cloud_id='22222222-2222-4222-8222-222222222222'))

    async def test_uncertain_exchange_is_not_replayed_and_expired_bearer_requires_reconnect(self):
        _,payload=await self.flow()
        async def fail(request):raise httpx.ReadTimeout('PRIVATE_CANARY')
        self.oauth.transport=httpx.MockTransport(fail)
        with self.assertRaises(HTTPException) as error:await self.oauth.complete('P1',self.user,payload)
        self.assertNotIn('PRIVATE_CANARY',str(error.exception.detail))
        with self.assertRaises(HTTPException) as error:await self.oauth.complete('P1',self.user,payload)
        self.assertEqual(error.exception.status_code,409)
        with self.assertRaises(HTTPException):await self.oauth.read({'cloud_id':self.cloud},'project/search',credentials={'access_token':'old','expires_at':0})
        self.assertEqual(self.oauth_requests,[])

    async def test_disabled_unconfigured_and_non_admin_do_not_start_flow(self):
        settings.features.jira_story_import=False
        with self.assertRaises(HTTPException):await self.flow()
        settings.features.jira_story_import=True;settings.jira_oauth_client_secret=None
        with self.assertRaises(HTTPException):await self.flow()
        self.assertEqual(self.db['jira_oauth_flows'].docs,[])
        settings.jira_oauth_client_secret='configured';self.db['users'].docs[0]['account_role']='MEMBER'
        with self.assertRaises(HTTPException):await self.flow()
        self.assertEqual(self.oauth_requests,[])

    async def test_unlisted_project_and_changed_connection_are_rejected(self):
        _,payload=await self.flow();grant=await self.oauth.complete('P1',self.user,payload)
        choice=JiraOAuthGrant(grant_id=grant['grant_id'],cloud_id=self.cloud)
        await self.oauth.projects('P1',self.user,choice)
        with self.assertRaises(HTTPException):
            await self.oauth.select('P1',self.user,JiraOAuthSelect(**choice.model_dump(),project_key='FOREIGN'))
        self.assertEqual(self.db['jira_connections'].docs,[])
        await self.connect()
        with self.assertRaises(HTTPException):
            await self.oauth.select('P1',self.user,JiraOAuthSelect(**choice.model_dump(),project_key='APP'))
        self.assertNotEqual(self.db['jira_connections'].docs[0].get('auth_type'),'oauth')

    async def test_oauth_http_routes_and_sanitized_validation(self):
        from app.routes import jira_routes
        with patch.object(jira_routes,'oauth',lambda:self.oauth):
            result=await self.client.post(self.base+'/oauth/start',json={'expected_revision':0})
            self.assertEqual(result.status_code,200,result.text)
            state=result.json()['state']
            response=await self.client.post(self.base+'/oauth/complete',json={'state':state,'code':'CODE_CANARY'})
            self.assertEqual(response.status_code,200,response.text)
            self.assertNotIn('ACCESS_CANARY',response.text)
            result=await self.client.post(self.base+'/oauth/complete',json={'state':state,'code':'CODE_CANARY','extra':'PRIVATE_CANARY'})
            self.assertEqual(result.status_code,422)
            self.assertNotIn('CANARY',result.text)
