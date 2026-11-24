"""User-bound, single-use Jira consent; encrypted short-lived grants, no replay."""
import base64
import json
import os
import re
import secrets
from datetime import timedelta
from urllib.parse import urlencode, urlsplit
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.services.approved_visual_run import digest
from app.services.jira_story_import import JiraStoryImport, now


class JiraOAuth(JiraStoryImport):
    @staticmethod
    def configuration():
        uri=settings.jira_oauth_redirect_uri or ""
        parsed=urlsplit(uri)
        local=parsed.scheme=="http" and parsed.hostname in ("localhost","127.0.0.1")
        if (not settings.jira_oauth_client_id or not settings.jira_oauth_client_secret
            or not (parsed.scheme=="https" or local) or not parsed.netloc
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path!="/jira/callback"):
            raise HTTPException(503,"Jira sign-in is not configured by the platform administrator.")
        return uri

    def encrypt(self,identity,value):
        nonce=os.urandom(12)
        return {"nonce":base64.b64encode(nonce).decode(),"credentials":base64.b64encode(
            self.cipher().encrypt(nonce,json.dumps(value).encode(),identity.encode())).decode()}

    def decrypt(self,row):
        try:
            return json.loads(self.cipher().decrypt(base64.b64decode(row["nonce"]),
                base64.b64decode(row["credentials"]),row["_id"].encode()))
        except HTTPException:raise
        except Exception:raise HTTPException(409,"Jira sign-in is unavailable. Connect again.") from None

    async def request(self,url,*,token=None,body=None):
        # All URLs are trusted literals, never a callback/site-supplied origin.
        try:
            async with httpx.AsyncClient(transport=self.transport,trust_env=False,follow_redirects=False,timeout=15) as client:
                async with client.stream("POST" if body is not None else "GET",url,json=body,
                    headers={"Authorization":"Bearer "+token} if token else {}) as response:
                    if response.status_code!=200:raise ValueError()
                    chunks=[];size=0
                    async for chunk in response.aiter_bytes():
                        size+=len(chunk)
                        if size>1000000:raise ValueError()
                        chunks.append(chunk)
                    return json.loads(b"".join(chunks))
        except Exception:
            raise HTTPException(502,"Jira sign-in could not be confirmed. Connect again; no automatic retry was made.") from None

    async def start(self,project,user,payload):
        _,account=await self.scope(project,user,admin=True)
        uri=self.configuration();self.cipher()
        connection=await self.db["jira_connections"].find_one({"_id":self.key(account["_id"],project)})
        if (connection or {}).get("revision",0)!=payload.expected_revision:
            raise HTTPException(409,"Connection changed. Reload before connecting.")
        state=secrets.token_urlsafe(32)
        await self.db["jira_oauth_flows"].insert_one({"_id":digest(state),"project_id":project,
            "account_id":account["_id"],"user_id":str(user["_id"]),"revision":payload.expected_revision,
            "stage":"pending","expires_at":now()+timedelta(minutes=10)})
        return {"state":state,"authorization_url":"https://auth.atlassian.com/authorize?"+urlencode({
            "audience":"api.atlassian.com","client_id":settings.jira_oauth_client_id,
            "scope":"read:jira-work read:jira-user","redirect_uri":uri,"state":state,
            "response_type":"code","prompt":"consent"})}

    async def complete(self,project,user,payload):
        _,account=await self.scope(project,user,admin=True)
        uri=self.configuration()
        # Consume before exchanging: uncertain code exchanges are never repeated.
        row=await self.db["jira_oauth_flows"].find_one_and_update({"_id":digest(payload.state),
            "project_id":project,"account_id":account["_id"],"user_id":str(user["_id"]),
            "stage":"pending","expires_at":{"$gt":now()}},{"$set":{"stage":"exchanging"}},return_document=ReturnDocument.AFTER)
        if not row:raise HTTPException(409,"Jira sign-in expired or was already used. Connect again.")
        result=await self.request("https://auth.atlassian.com/oauth/token",body={"grant_type":"authorization_code",
            "client_id":settings.jira_oauth_client_id,"client_secret":settings.jira_oauth_client_secret,
            "redirect_uri":uri,"code":payload.code.get_secret_value()})
        if (not isinstance(result,dict) or not isinstance(result.get("access_token"),str)
            or not 0<len(result["access_token"])<=16000 or type(result.get("expires_in")) is not int
            or not 0<result["expires_in"]<=86400):
            raise HTTPException(502,"Jira returned an invalid sign-in response. Connect again.")
        token=result["access_token"]
        resources=await self.request("https://api.atlassian.com/oauth/token/accessible-resources",token=token)
        if not isinstance(resources,list) or len(resources)>100:raise HTTPException(502,"Jira site list is unavailable.")
        sites=[]
        for resource in resources:
            if not isinstance(resource,dict):continue
            try:cloud=str(UUID(resource.get("id","")))
            except (ValueError,TypeError,AttributeError):continue
            url=resource.get("url","")
            if not isinstance(url,str) or not re.fullmatch(r"https://[a-z0-9][a-z0-9-]{0,61}\.atlassian\.net/?",url):continue
            scopes=resource.get("scopes",[])
            if not isinstance(scopes,list) or not {"read:jira-work","read:jira-user"}.issubset(scopes):continue
            sites.append({"cloud_id":cloud,"site":urlsplit(url).hostname})
        if not sites:raise HTTPException(400,"No supported Jira site has the required read permissions.")
        grant=uuid4().hex
        credentials={"access_token":token,"expires_at":now().timestamp()+result["expires_in"]-30}
        await self.db["jira_oauth_grants"].insert_one({"_id":grant,"project_id":project,"account_id":account["_id"],
            "user_id":str(user["_id"]),"revision":row["revision"],"sites":sites,"stage":"selecting",
            "expires_at":now()+timedelta(minutes=10),**self.encrypt(grant,credentials)})
        return {"grant_id":grant,"sites":sites}

    async def grant(self,project,user,payload):
        _,account=await self.scope(project,user,admin=True)
        row=await self.db["jira_oauth_grants"].find_one({"_id":payload.grant_id,"project_id":project,
            "account_id":account["_id"],"user_id":str(user["_id"]),"stage":"selecting","expires_at":{"$gt":now()}})
        if not row:raise HTTPException(409,"Jira selection expired. Connect again.")
        site=next((site for site in row["sites"] if site["cloud_id"]==str(payload.cloud_id)),None)
        if not site:raise HTTPException(422,"Select a Jira site from the authorized list.")
        return row,site,self.decrypt(row)

    async def projects(self,project,user,payload):
        row,site,credentials=await self.grant(project,user,payload)
        result=await self.read(site,"project/search",credentials=credentials,params={"maxResults":50,"startAt":0})
        values=result.get("values",[])
        if not isinstance(values,list) or len(values)>50:raise HTTPException(502,"Jira project list is unavailable.")
        projects=[{"key":item["key"],"name":str(item.get("name",""))[:200]} for item in values
            if isinstance(item,dict) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,19}",str(item.get("key","")))]
        await self.db["jira_oauth_grants"].update_one({"_id":row["_id"],"stage":"selecting"},
            {"$set":{"selected_cloud":site["cloud_id"],"projects":projects}})
        return {"projects":projects,"limited":not result.get("isLast",True)}

    async def select(self,project,user,payload):
        row,site,credentials=await self.grant(project,user,payload)
        if row.get("selected_cloud")!=site["cloud_id"] or payload.project_key not in [item["key"] for item in row.get("projects",[])]:
            raise HTTPException(422,"Choose a project from the retrieved list.")
        identity=self.key(row["account_id"],project)
        connection={"account_id":row["account_id"],"project_id":project,**site,"auth_type":"oauth",
            "project_key":payload.project_key,"acceptance_field":payload.acceptance_field,"connected":True,
            "revision":row["revision"]+1,"updated_at":now(),"authorized_by":str(user["_id"]),**self.encrypt(identity,credentials)}
        old=await self.db["jira_connections"].find_one({"_id":identity})
        if old:
            result=await self.db["jira_connections"].update_one({"_id":identity,"revision":row["revision"]},{"$set":connection})
            if result.matched_count!=1:raise HTTPException(409,"Connection changed. Connect again.")
        else:
            if row["revision"]!=0:raise HTTPException(409,"Connection changed. Connect again.")
            try:await self.db["jira_connections"].insert_one({"_id":identity,**connection})
            except DuplicateKeyError:raise HTTPException(409,"Connection changed. Connect again.") from None
        await self.db["jira_oauth_grants"].update_one({"_id":row["_id"]},{"$set":{"stage":"used","credentials":None,"nonce":None}})
        return self.public(connection)
