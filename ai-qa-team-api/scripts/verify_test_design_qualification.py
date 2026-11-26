"""Opt-in local-only qualification. Never uses configured application Mongo/AI.

Requires the separate loopback Mongo replica set on port 27129. All data lives in
an auto-generated database and is dropped in finally. AI responses/session Redis
are deterministic doubles; HTTP auth, authorization, routes and Mongo are real.
"""
import argparse
import asyncio
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Explicit fixture settings before any application import. No configured services.
os.environ.update(MONGO_URI="mongodb://127.0.0.1:27129", MONGO_DB="qa_local_qualification_only",
    REDIS_HOST="127.0.0.1", REDIS_PORT="6399", REDIS_USERNAME="", REDIS_PASSWORD="",
    JWT_SECRET_KEY="local-test-design-qualification-only", SESSION_SECRET_KEY="local-qualification-only",
    KNOWLEDGE_ENCRYPTION_REQUIRED="false")
import httpx
from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings, FeatureFlags
from app.routes import auth_routes, account_routes, project_routes, story_routes, scenario_routes, testcase_routes, product_knowledge_routes, test_design_routes
from app.services.product_knowledge import ProductKnowledge
from app.services.test_design_review import TestDesignReview
from app.services.ai.ai_usage_service import AIUsageService
from app.services.ai.ai_usage_policy import AIOperation, get_ai_usage_policy, AIUsageError
from app.services.ai.base_provider import LLMResponse
from app.models.product_knowledge import KnowledgeDraft, KnowledgeSourceInput
from app.models.test_design_review import TestDesignDraft
from app.utils import redis_client
from app.utils.jwt_handler import create_access_token
from bson import ObjectId

RULE = "Saving a draft shows Draft saved."
CRITERION = "Saving a draft shows Draft saved."
INTENT = {"title":"Save draft confirmation","description":"Check saved confirmation","purpose":"Verify saving",
    "role":None,"coverage_type":"happy_path","preconditions":["A draft is open"],"expected_outcome":"Draft saved.",
    "acceptance_criteria_refs":[CRITERION],"rule_references":["K1"]}
CASE = {"title":"Save draft confirmation details","purpose":"Verify saving","role":None,
    "preconditions":["A draft is open"],"public_data":[],"procedure":[{"instruction":"Save the draft","expected":"Draft saved."}],
    "assertions":["Draft saved."],"cleanup":[],"acceptance_criteria_refs":[CRITERION],"rule_references":["K1"]}


class Qualification:
    def __init__(self, db, entitlements_v2=False):
        self.entitlements_v2 = entitlements_v2
        self.db=db; self.case=deepcopy(CASE); self.intent=deepcopy(INTENT); self.report={"database":"ephemeral-loopback-only","provider":"deterministic-double",
            "checks":[],"findings":[],"ai_calls":0}; self.race_operation=None; self.race_count=0; self.race_gate=asyncio.Event()

    def check(self, name, result, **detail):
        self.report["checks"].append({"name":name,"passed":bool(result),**detail})
        if not result:self.report["findings"].append(name)

    async def fake_ai(self, service, operation, project, user, request):
        self.report["ai_calls"]+=1
        content=json.loads(request.prompt)
        if str(operation)==self.race_operation:
            self.race_count+=1
            if self.race_count==2:self.race_gate.set()
            await asyncio.wait_for(self.race_gate.wait(),10)
        key=request.response_schema_name
        if key=="knowledge_extraction_v1":
            source=content
            result={"claims":[{"claim_id":"K1","category":"business_rule","statement":RULE,
                "epistemic_status":"expected","source_id":source["source_id"],"quote":RULE}],"clarification_questions":[]}
        elif key=="story_analysis_v1":result={"summary":"Requirements are clear.","findings":[]}
        elif key=="scenario_design_v1":result={"scenarios":[deepcopy(self.intent)]}
        elif key=="test_design_v1":result={"testcases":[deepcopy(self.case)]}
        else:raise AssertionError("Unexpected AI operation: "+str(key))
        return LLMResponse(text=json.dumps(result),provider_id="fixture",model="deterministic")

    async def call(self, client, method, path, expected=200, **kwargs):
        response=await client.request(method,path,**kwargs)
        assert response.status_code==expected,(method,path,response.status_code,response.text[:1000])
        return response.json() if response.content else None

    async def run(self):
        app=FastAPI()
        routers=(auth_routes,account_routes,project_routes,story_routes,scenario_routes,testcase_routes,product_knowledge_routes,test_design_routes)
        for module in routers:app.include_router(module.router)
        with ExitStack() as stack:
            # Patch each already-imported module's database binding, not auth logic.
            for name,module in list(sys.modules.items()):
                if name.startswith('app.') and module is not None and 'db' in vars(module):
                    stack.enter_context(patch.object(module,'db',self.db))
            stack.enter_context(patch.object(settings,'features',FeatureFlags(customer_accounts=True,account_subscriptions=True,
                separate_ai_allowances=True,product_knowledge=True,story_analysis=True,story_management=True,scenario_generation=True,
                test_generation=True,manual_test_results=True)))
            stack.enter_context(patch.object(settings,'app_env','test'))
            stack.enter_context(patch.object(redis_client,'redis_client',redis_client.LocalCache()))
            async def execute(service,*args,**kwargs):return await self.fake_ai(service,*args,**kwargs)
            stack.enter_context(patch.object(AIUsageService,'execute',execute))
            transport=httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport,base_url='http://qualification.test') as owner, httpx.AsyncClient(transport=transport,base_url='http://qualification.test') as foreign:
                await self.call(owner,'POST','/auth/signup',json={"name":"QA Owner","email":"owner@example.com","password":"fixture-password"})
                await self.call(owner,'PATCH','/account',json={"name":"QA Fixture"})
                if self.entitlements_v2:
                    from app.services.account_entitlements import plan_entitlements, apply_entitlements
                    row = await self.db['customer_accounts'].find_one({'status':'ACTIVE'})
                    plan = plan_entitlements([row], {row['_id']:'free'})
                    await apply_entitlements(self.db, plan, plan['plan_digest'], maintenance_confirmed=True)
                    self.check('explicit_v2_adoption_before_route_journey', not plan['errors'])
                project=await self.call(owner,'POST','/projects',json={"name":"Qualification project","created_by":"owner@example.com"})
                project_id=project['project_id']; root=f'/projects/{project_id}/knowledge'
                self.check('signup_account_project',project['current_user_role']=='ADMIN')
                review=await self.call(owner,'POST',root+'/training',201,json={"request_id":uuid4().hex,"title":"Business rule","source":{"title":"Independent product notes","kind":"document","text":RULE}})
                review=await self.call(owner,'POST',root+'/training/'+review['review_id']+'/extract',json={})
                proposals=deepcopy(review['proposals'])
                for proposal in proposals:proposal['decision']='confirmed'
                review=await self.call(owner,'POST',root+'/training/'+review['review_id']+'/review',json={"expected_revision":review['revision'],"proposals":proposals,"clarification_answers":{}})
                review=await self.call(owner,'POST',root+'/training/'+review['review_id']+'/save',json={"expected_revision":review['revision']})
                version=review['saved_version']; approved=await self.call(owner,'POST',root+'/versions/'+version['version_id']+'/approve')
                self.case['rule_references']=[approved['claims'][0]['claim_id']]; self.intent['rule_references']=list(self.case['rule_references'])
                self.check('teach_review_approve_real_mongo',approved['status']=='approved' and len(approved['claims'])==1)
                story=await self.call(owner,'POST','/stories',json={"project_id":project_id,"title":"Save draft","description":"Users save drafts for later editing.","acceptance_criteria":CRITERION})
                story_id=story['story_id']
                analysis=await self.call(owner,'POST',root+f'/stories/{story_id}/analyze?analysis_mode=knowledge_aware')
                await self.call(owner,'POST',root+f'/stories/{story_id}/analysis/'+analysis['analysis_id']+'/review',json={"resolutions":[]})
                result=await self.call(owner,'POST',f'/scenarios/generate-from-story?story_id={story_id}&count=1&complexity=basic&approved_story=true')
                scenario=result['scenarios'][0]; scenario_id=scenario['scenario_id']
                await self.call(owner,'PUT',f'/scenarios/{scenario_id}/approve')
                cases=await self.call(owner,'POST',f'/testcases/generate?scenario_id={scenario_id}&project_id={project_id}&count=1&complexity=basic')
                testcase=cases[0]; testcase_id=testcase['testcase_id']; design=f'/projects/{project_id}/test-design/cases/{testcase_id}'
                draft=await self.call(owner,'POST',design,201,json={"idempotency_key":uuid4().hex,"case":self.case})
                final=await self.call(owner,'POST',design+'/'+draft['version_id']+'/approve')
                exported=await self.call(owner,'GET',design+'/'+draft['version_id']+'/export')
                self.check('story_analysis_scenario_case_approval_export',final['status']=='approved' and final['approved_by_display_name']=='QA Owner' and json.loads(exported['content'])['executable'] is False)
                self.check('exact_context_and_preconditions',testcase['preconditions']==CASE['preconditions'] and testcase['knowledge_version_id']==approved['version_id'])
                await self.call(foreign,'POST','/auth/signup',json={"name":"Foreign","email":"foreign@example.com","password":"fixture-password"})
                denied=[]
                for path in (root,root+'/sources/'+approved['claims'][0]['source_id'],root+'/versions/'+approved['version_id'],root+f'/stories/{story_id}/analysis',design,design+'/'+draft['version_id']+'/export',f'/scenarios/project-list?project_id={project_id}',f'/testcases/project-list?project_id={project_id}'):
                    response=await foreign.get(path);denied.append(response.status_code in (403,404))
                self.check('foreign_account_read_evidence_and_export_isolation',all(denied),paths=len(denied))
                response=await foreign.post(root+'/versions/'+approved['version_id']+'/approve')
                self.check('foreign_account_cannot_approve',response.status_code in (403,404))
                await self.ai_credit_races(project_id)
                await self.object_quota_races(owner,project_id,story_id,scenario_id,testcase_id)
                await self.approval_races(project_id,testcase_id,approved)
                await self.member_checks(app, owner, project_id, testcase_id, approved, draft)
                before=self.report['ai_calls']
                account=(await self.db['projects'].find_one({'project_id':project_id}))['account_id']
                await self.db['customer_accounts'].update_one({'_id':account},{'$set':{'subscription.limits.testcases_limit':100,'subscription.limits.testcases_basic_limit':100}})
                await self.db['stories'].update_one({'story_id':story_id},{'$set':{'description':'Changed story requirements.'}})
                denied_case=await owner.post(f'/testcases/generate?scenario_id={scenario_id}&project_id={project_id}&count=1&complexity=basic')
                self.check('changed_story_blocks_test_design',denied_case.status_code==409 and self.report['ai_calls']==before)
                self.check('no_execution_or_media_started',await self.db['executions'].count_documents({})==0 and await self.db['knowledge_ingestion_jobs'].count_documents({})==0)
        return self.report

    async def member_checks(self, app, owner, project, testcase, approved, draft):
        owner_row=await self.db['users'].find_one({'email':'owner@example.com'})
        member={**deepcopy(owner_row),'_id':ObjectId(),'email':'member@example.com','name':'QA Member','role':'tester','account_role':'MEMBER','platform_role':'NONE'}
        await self.db['users'].insert_one(member)
        root=f'/projects/{project}/knowledge';design=f'/projects/{project}/test-design/cases/{testcase}'
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://qualification.test') as client:
            await self.call(client,'POST','/auth/login',json={'email':'member@example.com','password':'fixture-password'})
            denied=await client.get(root)
            self.check('same_account_without_project_membership_denied',denied.status_code in (403,404))
            await self.db['project_memberships'].insert_one({'membership_id':'qualification-member','project_id':project,'account_id':member['account_id'],'email':member['email'],'role':'TESTER','status':'ACTIVE'})
            response=await client.get(root)
            self.check('project_member_can_read_approved_knowledge',response.status_code==200)
            response=await client.post(root+'/versions/'+approved['version_id']+'/approve')
            self.check('project_member_cannot_approve_knowledge',response.status_code==403)
            # Retrying an already-approved design remains immutable and does not
            # replace the original approver with this member.
            response=await client.post(design+'/'+draft['version_id']+'/approve')
            self.check('member_design_approval_retry_preserves_actor',response.status_code==200 and response.json()['approved_by_display_name']=='QA Owner')
            # New saved draft: current member policy allows explicit approval.
            saved=await self.call(client,'POST',design,201,json={'case':self.case,'idempotency_key':uuid4().hex})
            result=await self.call(client,'POST',design+'/'+saved['version_id']+'/approve')
            self.check('project_member_can_approve_design_under_member_policy',result['approved_by_display_name']=='QA Member' and result['approved_by_project_role']=='TESTER')
        foreign=await self.db['users'].find_one({'email':'foreign@example.com'})
        await self.db['users'].update_one({'_id':foreign['_id']},{'$set':{'platform_role':'OWNER'}})
        await self.db['project_memberships'].insert_one({'membership_id':'foreign-stale','project_id':project,'email':foreign['email'],'role':'ADMIN','status':'ACTIVE'})
        token=create_access_token({'email':foreign['email'],'role':'admin'})
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://qualification.test',cookies={'access_token':token}) as client:
            response=await client.get(design+'/'+draft['version_id']+'/export')
            self.check('platform_owner_with_foreign_stale_membership_denied',response.status_code in (403,404))

    async def approval_races(self, project, testcase, approved):
        knowledge_project=project+'_receipt_race'
        baseline=ProductKnowledge(self.db)
        source=await baseline.add_source(knowledge_project,'fixture',KnowledgeSourceInput(title='Race source',kind='document',text=RULE))
        claim={**approved['claims'][0],'source_id':source['source_id']}
        root=await baseline.create_version(knowledge_project,'fixture',KnowledgeDraft(title='Race root',claims=[claim]))
        approved=await baseline.approve(knowledge_project,'fixture',root['version_id'])
        drafts=[await ProductKnowledge(self.db).create_version(knowledge_project,'fixture',KnowledgeDraft(title='Competing successor',claims=[{**approved['claims'][0],'claim_id':key}])) for key in ('K2','K3')]
        services=[ProductKnowledge(self.db),ProductKnowledge(self.db)];gate=asyncio.Event();arrived=0
        async def sync_active(original, identity):
            nonlocal arrived
            value=await original(identity);arrived+=1
            if arrived==2:gate.set()
            await asyncio.wait_for(gate.wait(),10);return value
        for service in services:
            original=service.active
            service.active=lambda identity, original=original:sync_active(original,identity)
        results=await asyncio.gather(*(service.approve(knowledge_project,'fixture',draft['version_id']) for service,draft in zip(services,drafts)),return_exceptions=True)
        wins=[value for value in results if isinstance(value,dict)]
        self.check('knowledge_competing_approvals_one_winner',len(wins)==1 and sum(isinstance(value,HTTPException) and value.status_code==409 for value in results)==1)
        service=ProductKnowledge(self.db)
        repeated=await service.approve(knowledge_project,'another-reviewer',wins[0]['version_id'])
        self.check('knowledge_retry_preserves_original_approval',repeated['approved_by']==wins[0]['approved_by'] and repeated['approved_at']==wins[0]['approved_at'])
        # The independent receipt race cannot change the journey project.
        # Competing saved test designs still publish through one CAS winner.
        review=TestDesignReview(self.db)
        drafts=[await review.create(project,testcase,'fixture',TestDesignDraft(case=self.case,idempotency_key=uuid4().hex,acknowledge_source_changes=True)) for _ in range(2)]
        gate=asyncio.Event();arrived=0;original=review.context
        async def sync_context(*args):
            nonlocal arrived
            value=await original(*args);arrived+=1
            if arrived==2:gate.set()
            await asyncio.wait_for(gate.wait(),10);return value
        review.context=sync_context
        results=await asyncio.gather(*(review.approve(project,testcase,'fixture',value['version_id']) for value in drafts),return_exceptions=True)
        self.check('test_design_competing_approvals_one_winner',sum(isinstance(value,dict) for value in results)==1 and sum(isinstance(value,HTTPException) and value.status_code==409 for value in results)==1)

    async def ai_credit_races(self, project):
        account=(await self.db['projects'].find_one({'project_id':project}))['account_id'];now=datetime.now(timezone.utc)
        for mode,field,limit in (('MANAGED','managed_ai_credits_used','managed_ai_credits_limit'),('BYOK','byok_ai_requests_used','byok_ai_requests_limit')):
            await self.db['customer_accounts'].update_one({'_id':account},{'$set':{f'subscription.usage.{field}':0,f'subscription.limits.{limit}':1}})
            service=AIUsageService(database=self.db)
            results=await asyncio.gather(*(service._reserve(account,get_ai_usage_policy(AIOperation.SCENARIO_DESIGN),now,mode=mode) for _ in range(8)),return_exceptions=True)
            row=await self.db['customer_accounts'].find_one({'_id':account})
            self.check(mode.lower()+'_last_credit_atomic',sum(isinstance(value,dict) for value in results)==1 and row['subscription']['usage'][field]==1)

    async def object_quota_races(self, client, project, story, scenario, testcase):
        # Run before approval races so context changes cannot mask resource limits.
        account=(await self.db['projects'].find_one({'project_id':project}))['account_id']
        for kind,operation,path,manual in (
            ('scenarios','SCENARIO_DESIGN',f'/scenarios/generate-from-story?story_id={story}&count=1&complexity=basic&approved_story=true',False),
            ('scenarios','SCENARIO_DESIGN',f'/scenarios/generate-from-story?story_id={story}&count=1&complexity=basic&approved_story=true',True),
            ('testcases','TEST_DESIGN',f'/testcases/generate?scenario_id={scenario}&project_id={project}&count=1&complexity=basic',False),
            ('testcases','TEST_DESIGN',f'/testcases/generate?scenario_id={scenario}&project_id={project}&count=1&complexity=basic',True)):
            # These concurrent calls intentionally use a deterministic design
            # boundary: AI rate/concurrency controls are not resource reservations.
            used=await self.db[kind].count_documents({'project_id':project})
            changes={f'subscription.usage.{kind}_used':used,f'subscription.limits.{kind}_limit':used+1}
            if kind=='testcases':changes.update({'subscription.usage.testcases_basic_used':used,'subscription.limits.testcases_basic_limit':used+1})
            await self.db['customer_accounts'].update_one({'_id':account},{'$set':changes})
            self.race_operation=operation;self.race_count=0;self.race_gate=asyncio.Event()
            first=asyncio.create_task(client.post(path))
            for _ in range(100):
                if self.race_count:break
                await asyncio.sleep(.01)
            assert self.race_count==1, 'First generation did not enter the deterministic provider'
            if manual and kind=='scenarios':
                second=await client.post('/scenarios',json={**self.intent,'story_id':story,'complexity':'basic','steps':[]})
            elif manual:
                second=await client.post(f'/testcases/draft?project_id={project}&scenario_id={scenario}',json={'title':'Manual fixture','description':'Manual fixture','steps':[{'action':'click','description':'Save draft','expected':'Draft saved.'}]})
            else:
                second=await client.post(path)
            self.race_gate.set()
            results=[await first,second]
            self.race_operation=None
            row=await self.db['customer_accounts'].find_one({'_id':account});actual=await self.db[kind].count_documents({'project_id':project})
            self.check(('manual_' if manual else '')+kind+'_last_slot_enforced',actual==used+1 and sorted(value.status_code for value in results)==[200,403] and self.race_count==1,statuses=[value.status_code for value in results],before=used,after=actual,limit=used+1,usage=row['subscription']['usage'][kind+'_used'])


        # Partial generation releases slots; replay of that same intentional
        # request must not spend another AI request or create duplicate rows.
        used=await self.db['scenarios'].count_documents({'project_id':project})
        await self.db['customer_accounts'].update_one({'_id':account},{'$set':{'subscription.limits.scenarios_limit':used+4}})
        request_id=uuid4().hex
        path=f'/scenarios/generate-from-story?story_id={story}&count=3&complexity=basic&approved_story=true&request_id={request_id}'
        calls=self.report['ai_calls']
        first=await client.post(path);second=await client.post(path)
        record=await self.db['resource_quota_reservations'].find_one({'request_id':request_id})
        self.check('request_identity_prevents_generation_replay_after_partial_output',first.status_code==200 and second.status_code==409 and self.report['ai_calls']==calls+1 and record['state']=='SETTLED' and record['remaining']==0)


async def main():
    parser=argparse.ArgumentParser();parser.add_argument('--confirm-isolated-local',action='store_true',required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--entitlements-v2',action='store_true');args=parser.parse_args()
    name='qa_test_design_'+uuid4().hex
    assert re.fullmatch(r'qa_test_design_[0-9a-f]{32}',name)
    client=AsyncIOMotorClient('mongodb://127.0.0.1:27129/?replicaSet=qaTestDesign',serverSelectionTimeoutMS=5000,socketTimeoutMS=10000)
    try:
        hello=await client.admin.command('hello')
        assert hello.get('setName')=='qaTestDesign', 'Refuse an unknown local Mongo service'
        for collection,identity in (('users','email'),('projects','project_id'),('stories','story_id'),('scenarios','scenario_id'),('testcases','testcase_id')):
            await client[name][collection].create_index(identity,unique=True)
        await client[name]['project_memberships'].create_index([('project_id',1),('email',1)],unique=True)
        result=await Qualification(client[name], entitlements_v2=args.entitlements_v2).run()
        result['ephemeral_database']=name
    finally:
        await client.drop_database(name)
        client.close()
    result['cleanup']='ephemeral database dropped'
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    return 1 if result['findings'] else 0

if __name__=='__main__':raise SystemExit(asyncio.run(main()))
