"""Bounded read-only Jira Cloud API; explicit reviewed snapshots into local stories."""
import base64
import json
import os
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError
from app.config import settings
from app.services.customer_accounts import CustomerAccounts
from app.services.approved_visual_run import digest
from app.utils.feature_flags import require_features

FIELDS = ("title", "description", "acceptance_criteria")


def now():return datetime.now(timezone.utc)


def text_value(value):
    if value is None:return "", []
    if isinstance(value,str):
        if len(value)>30000:raise HTTPException(413,"Jira field exceeds the import size limit.")
        return value, []
    warnings=[]; parts=[]; nodes=0
    def walk(node,depth=0):
        nonlocal nodes
        nodes+=1
        if nodes>5000 or depth>20:raise HTTPException(413,"Jira document exceeds processing limits.")
        if not isinstance(node,dict):raise HTTPException(502,"Unsupported Jira field format.")
        kind=node.get("type")
        if kind=="text":parts.append(str(node.get("text","")))
        elif kind=="hardBreak":parts.append("\n")
        elif kind in {"doc","paragraph","heading","bulletList","orderedList","listItem","blockquote","codeBlock","panel","table","tableRow","tableCell","tableHeader","rule"}:
            for child in node.get("content",[]):walk(child,depth+1)
            if kind in {"paragraph","heading","listItem","tableRow","codeBlock","rule"}:parts.append("\n")
        else:warnings.append("Unsupported embedded content was omitted; review the original Jira issue.")
        if sum(map(len,parts))>30000:raise HTTPException(413,"Jira field exceeds the import size limit.")
    walk(value)
    return "".join(parts).strip(), sorted(set(warnings))


class JiraStoryImport:
    def __init__(self,database,*,transport=None,transaction=None):
        self.db,self.transport,self.transaction=database,transport,transaction

    async def scope(self,project,user,admin=False):
        require_features("jira_story_import","story_management")
        row=await self.db["projects"].find_one({"project_id":project})
        account=await CustomerAccounts(self.db).project(row,user)
        member=await self.db["project_memberships"].find_one({"project_id":project,"account_id":account["_id"],"email":user["email"].strip().lower(),"status":"ACTIVE"})
        if not member:raise HTTPException(404,"Project not found or access denied.")
        if admin:await CustomerAccounts(self.db).admin(user)
        return row,account

    @staticmethod
    def key(account,project):return digest(["jira-connection-v1",account,project])

    @staticmethod
    def cipher():
        try:
            key=base64.urlsafe_b64decode(settings.jira_secret_master_key or "")
            if len(key)!=32:raise ValueError()
            return AESGCM(key)
        except Exception:raise HTTPException(503,"Jira credential encryption is not configured.") from None

    @staticmethod
    def public(row):
        if not row:return {"connected":False,"revision":0}
        return {key:row.get(key) for key in ("connected","revision","site","cloud_id","project_key","acceptance_field","auth_type")}

    async def connection(self,project,user):
        _,account=await self.scope(project,user)
        row=await self.db["jira_connections"].find_one({"_id":self.key(account["_id"],project),"account_id":account["_id"],"project_id":project})
        return row,account

    async def read(self,connection,path,*,credentials=None,params=None):
        if credentials is None:
            try:
                raw=self.cipher().decrypt(base64.b64decode(connection["nonce"]),base64.b64decode(connection["credentials"]),connection["_id"].encode())
                credentials=json.loads(raw)
            except HTTPException:raise
            except Exception:raise HTTPException(503,"Jira credentials are unavailable. Reconnect through an account administrator.") from None
        if credentials.get("access_token"):
            if credentials.get("expires_at",0)<=now().timestamp():
                raise HTTPException(409,"Jira access expired. Reconnect Jira before continuing.")
            auth=None;headers={"Accept":"application/json","Authorization":"Bearer "+credentials["access_token"]}
        else:
            auth=httpx.BasicAuth(credentials["email"],credentials["token"]);headers={"Accept":"application/json"}
        try:
            async with httpx.AsyncClient(transport=self.transport,trust_env=False,follow_redirects=False,timeout=10) as client:
                url="https://api.atlassian.com/ex/jira/"+connection["cloud_id"]+"/rest/api/3/"+path
                async with client.stream("GET",url,auth=auth,params=params,headers=headers) as response:
                    if response.status_code in (401,403):raise HTTPException(400,"Jira credentials or read permissions were rejected.")
                    if response.status_code==429:raise HTTPException(429,"Jira rate limit reached. Retry explicitly later.")
                    if response.status_code!=200:raise HTTPException(502,"Jira could not return the requested data.")
                    chunks=[];size=0
                    async for chunk in response.aiter_bytes():
                        size+=len(chunk)
                        if size>1000000:raise HTTPException(413,"Jira response exceeds import limits.")
                        chunks.append(chunk)
                    value=json.loads(b"".join(chunks))
                    if not isinstance(value,dict):raise ValueError()
                    return value
        except HTTPException:raise
        except Exception:raise HTTPException(502,"Jira request failed. No automatic retry was made.") from None

    async def disconnect(self,project,user,payload):
        _,account=await self.scope(project,user,admin=True)
        result=await self.db["jira_connections"].update_one({"_id":self.key(account["_id"],project),"revision":payload.expected_revision},
            {"$set":{"connected":False,"credentials":None,"nonce":None,"revision":payload.expected_revision+1}})
        if result.matched_count!=1:raise HTTPException(409,"Connection changed. Reload its status.")
        return {"connected":False,"revision":payload.expected_revision+1}

    async def preview(self,project,user,payload):
        connection,account=await self.connection(project,user)
        if not connection or not connection["connected"]:raise HTTPException(409,"Connect Jira before importing.")
        keys=payload.issue_keys
        if len(set(keys))!=len(keys) or any(not re.fullmatch(re.escape(connection["project_key"])+r"-[1-9][0-9]{0,19}",key) for key in keys):
            raise HTTPException(422,"Select unique issue keys from the configured Jira project.")
        items=[]
        for key in keys:
            fields=["summary","description","updated","issuetype"]+([connection["acceptance_field"]] if connection["acceptance_field"] else [])
            remote=await self.read(connection,"issue/"+key,params={"fields":",".join(fields)})
            identity=str(remote.get("id",""));values=remote.get("fields",{})
            if not re.fullmatch(r"[0-9]{1,30}",identity) or remote.get("key")!=key:raise HTTPException(502,"Jira returned an unexpected issue identity.")
            description,warnings=text_value(values.get("description"));criteria,extra=text_value(values.get(connection["acceptance_field"])) if connection["acceptance_field"] else ("",[])
            title=values.get("summary","")
            if not isinstance(title,str) or not title.strip() or len(title)>500:raise HTTPException(502,"Jira issue title is unavailable or exceeds limits.")
            incoming={"title":title,"description":description,"acceptance_criteria":criteria}
            local_id=digest(["jira-story-v1",account["_id"],project,connection["cloud_id"],identity])
            current=await self.db["stories"].find_one({"_id":local_id,"project_id":project})
            current_fields={name:(current or {}).get(name) or "" for name in FIELDS}
            baseline=(current or {}).get("jira_import",{}).get("baseline",{})
            conflicts=[name for name in FIELDS if current and current_fields[name]!=baseline.get(name,"") and current_fields[name]!=incoming[name]]
            items.append({"issue_id":identity,"issue_key":key,"local_id":local_id,"story_id":(current or {}).get("story_id"),"incoming":incoming,
                "current":current_fields if current else None,"current_digest":digest(current_fields) if current else None,
                "conflicts":conflicts,"warnings":sorted(set(warnings+extra)),"remote_updated_at":str(values.get("updated") or "")[:100]})
        identity=uuid4().hex
        row={"_id":identity,"preview_id":identity,"account_id":account["_id"],"project_id":project,"connection_revision":connection["revision"],
            "cloud_id":connection["cloud_id"],"site":connection["site"],"items":items,"state":"pending","created_by":str(user.get("_id")),
            "created_at":now(),"expires_at":now()+timedelta(minutes=10)}
        await self.db["jira_import_previews"].insert_one(row)
        return {"preview_id":identity,"items":[{key:value for key,value in item.items() if key not in ("local_id","current_digest")} for item in items],"state":"pending"}

    async def apply(self,project,user,payload):
        _,account=await self.scope(project,user)
        async def work(session):
            options={"session":session} if session is not None else {}
            billing=await self.db["customer_accounts"].find_one({"_id":account["_id"],"status":"ACTIVE"},**options)
            if not billing:raise HTTPException(403,"Customer account is unavailable.")
            row=await self.db["jira_import_previews"].find_one({"_id":payload.preview_id,"project_id":project,"account_id":account["_id"]},**options)
            if not row:raise HTTPException(404,"Import preview not found.")
            selection_digest=digest([item.model_dump() for item in payload.selections])
            if row["state"]=="applied":
                if row["selection_digest"]!=selection_digest:raise HTTPException(409,"This preview was already applied with different selections.")
                return row["result"]
            expiry=row["expires_at"]
            if expiry.tzinfo is None:expiry=expiry.replace(tzinfo=timezone.utc)
            connection=await self.db["jira_connections"].find_one({"_id":self.key(account["_id"],project)},**options)
            if expiry<=now() or not connection or not connection["connected"] or connection["revision"]!=row["connection_revision"]:
                raise HTTPException(409,"Preview expired or connection changed. Preview again before importing.")
            if len({item.issue_id for item in payload.selections})!=len(payload.selections):raise HTTPException(422,"Select each issue once.")
            results=[]
            for selected in payload.selections:
                item=next((item for item in row["items"] if item["issue_id"]==selected.issue_id),None)
                if not item or len(set(selected.fields))!=len(selected.fields):raise HTTPException(422,"Select only previewed issues and unique fields.")
                current=await self.db["stories"].find_one({"_id":item["local_id"],"project_id":project},**options)
                current_fields={name:(current or {}).get(name) or "" for name in FIELDS}
                if (digest(current_fields) if current else None)!=item["current_digest"]:
                    raise HTTPException(409,"A story changed after preview. Preview again to protect local edits.")
                if not current and set(selected.fields)!=set(FIELDS):raise HTTPException(422,"New stories require review of all mapped fields.")
                updates={name:item["incoming"][name] for name in selected.fields}
                if current:
                    baseline={**current.get("jira_import",{}).get("baseline",{}),**updates}
                    story_id=current["story_id"]
                else:
                    subscription=billing.get("subscription",{})
                    if billing.get("billing_version")!=1 or subscription.get("status")!="active" or "stories_limit" not in subscription.get("limits",{}):
                        raise HTTPException(409,"Account billing migration/configuration is required before Jira import.")
                    query={"_id":account["_id"],"billing_version":1,"status":"ACTIVE","subscription.status":"active"}
                    limit=subscription["limits"]["stories_limit"]
                    if limit is not None:query["subscription.usage.stories_used"]={"$lt":limit}
                    reserved=await self.db["customer_accounts"].update_one(query,{"$inc":{"subscription.usage.stories_used":1}},**options)
                    if reserved.modified_count!=1:raise HTTPException(403,"Account story allowance reached.")
                    counter=await self.db["counters"].find_one_and_update({"_id":"story_id"},{"$inc":{"seq":1}},upsert=True,return_document=ReturnDocument.AFTER,**options)
                    story_id=f'S{counter["seq"]:03d}';baseline=dict(updates)
                metadata={"cloud_id":row["cloud_id"],"issue_id":item["issue_id"],"issue_key":item["issue_key"],"url":"https://"+row["site"]+"/browse/"+item["issue_key"],
                    "baseline":baseline,"remote_updated_at":item["remote_updated_at"],"imported_at":now().isoformat()}
                updates.update(jira_issue_key=item["issue_key"],jira_url=metadata["url"])
                if current:
                    await self.db["stories"].update_one({"_id":item["local_id"],"project_id":project},{"$set":{**updates,"jira_import":metadata}},**options)
                else:
                    await self.db["stories"].insert_one({"_id":item["local_id"],"account_id":account["_id"],"project_id":project,"story_id":story_id,**updates,
                        "jira_import":metadata,"status":"pending","tags":[],"scenarios":[],"out_of_scope":"","created_by":user["email"],"created_at":now().isoformat()},**options)
                results.append({"issue_key":item["issue_key"],"story_id":story_id,"action":"updated" if current else "created"})
            result={"preview_id":payload.preview_id,"stories":results}
            await self.db["jira_import_previews"].update_one({"_id":row["_id"]},{"$set":{"state":"applied","selection_digest":selection_digest,"result":result}},**options)
            return result
        try:
            if self.transaction:return await self.transaction(work)
            async with await self.db.client.start_session() as session:
                async with session.start_transaction():return await work(session)
        except HTTPException:raise
        except (PyMongoError,AttributeError):
            raise HTTPException(503,"Transactional import could not be confirmed. Refresh/retry this same preview to reconcile; do not create a duplicate import.") from None
