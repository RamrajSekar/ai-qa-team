"""Opt-in local-Mongo quota fault/concurrency checks. No providers or application DB."""
import asyncio
from copy import deepcopy
import json
import io
from contextlib import redirect_stdout
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
import argparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update(MONGO_URI="mongodb://127.0.0.1:27129", MONGO_DB="qa_quota_fixture_only",
    REDIS_HOST="127.0.0.1", REDIS_PORT="6399", REDIS_USERNAME="", REDIS_PASSWORD="",
    JWT_SECRET_KEY="local-quota-fixture-only", SESSION_SECRET_KEY="local-quota-fixture-only")
from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings, FeatureFlags
from app.services.resource_quota import ResourceQuota, fingerprint


async def verify(db):
    checks=[]
    async def fixture(limits=None, legacy=False):
        identity=uuid4().hex
        subscription={"status":"active","plan":"pro","ai_allowance_version":1,
            "usage":{"scenarios_used":0,"testcases_used":0,"testcases_basic_used":0,"testcases_medium_used":0,"testcases_advanced_used":0,"ai_gen_used":10,"managed_ai_credits_used":7,"byok_ai_requests_used":3},
            "limits":{"scenarios_limit":3,"testcases_limit":3,"testcases_basic_limit":2,"testcases_medium_limit":2,"testcases_advanced_limit":2,**(limits or {})}}
        user={"_id":ObjectId(),"email":identity+'@example.com',"subscription":deepcopy(subscription)}
        collection='users';owner_id=user['_id']
        if not legacy:
            owner_id='ACC_'+identity;collection='customer_accounts'
            user.update(account_id=owner_id,account_state='ACTIVE',account_role='OWNER')
            await db[collection].insert_one({'_id':owner_id,'status':'ACTIVE','billing_version':1,'subscription':subscription})
        await db['users'].insert_one(user)
        return user,collection,owner_id
    def doc(user,kind,ordinal=0,tier='basic'):
        return {'project_id':'P1','created_by':user['email'],'title':'Fixture '+str(ordinal),
            ('scenario_id' if kind=='scenarios' else 'testcase_id'):uuid4().hex,'complexity':tier}
    async def rejected(awaitable,code):
        try:await awaitable
        except HTTPException as error:
            assert error.status_code==code,(error.status_code,code);return
        raise AssertionError('Expected rejection')
    async def run(name,work):
        await work();checks.append({'name':name,'passed':True})

    async def partial():
        user,collection,owner=await fixture();q=ResourceQuota(db)
        async with q.admission(user,'P1','testcases',3,'basic') as r:
            assert r['capacity']==2
            await q.persist(r,doc(user,'testcases'),0)
        row=await db[collection].find_one({'_id':owner})
        assert row['subscription']['usage']['testcases_used']==1 and row['subscription']['usage']['testcases_basic_used']==1
        assert row['resource_quota_pending']=={'testcases_used':0,'testcases_basic_used':0}
        assert [row['subscription']['usage'][key] for key in ('ai_gen_used','managed_ai_credits_used','byok_ai_requests_used')]==[10,7,3]
    await run('partial_output_releases_unused_slots_and_preserves_ai_balances',partial)

    async def failure():
        user,collection,owner=await fixture();q=ResourceQuota(db)
        try:
            async with q.admission(user,'P1','scenarios',3):raise RuntimeError('fixture model failure')
        except RuntimeError:pass
        row=await db[collection].find_one({'_id':owner});assert row['resource_quota_pending']['scenarios_used']==0
        assert row['subscription']['usage']['scenarios_used']==0
    await run('known_generation_failure_releases_capacity',failure)

    async def interrupted():
        user,collection,owner=await fixture({'scenarios_limit':2});q=ResourceQuota(db);key=uuid4().hex
        r=await q.reserve(user,'P1','scenarios',2,request_id=key)
        item=doc(user,'scenarios');stored=await q.persist(r,item,0);assert isinstance(stored['_id'],ObjectId)
        # New instance simulates runtime restart. No expiry/replay or usage reset.
        recovered=ResourceQuota(db)
        await rejected(recovered.reserve(user,'P2','scenarios',1),403)
        await recovered.settle(r)
        await recovered.persist(r,item,0)  # exact DB-only idempotent recovery
        await rejected(recovered.persist(r,doc(user,'scenarios',1),1),409)
        await rejected(recovered.reserve(user,'P1','scenarios',1,request_id=key),409)
        row=await db[collection].find_one({'_id':owner})
        assert row['subscription']['usage']['scenarios_used']==1 and row['resource_quota_pending']['scenarios_used']==0
        assert await db['scenarios'].count_documents({'created_by':user['email']})==1
    await run('interruption_recovery_does_not_duplicate_or_replay_generation',interrupted)

    async def rollback():
        user,collection,owner=await fixture();underlying=db['scenarios']
        class FailingCollection:
            def __getattr__(self,name):return getattr(underlying,name)
            async def insert_one(self,*args,**kwargs):
                await underlying.insert_one(*args,**kwargs)
                raise RuntimeError('fixture failure after insert before commit')
        class Database:
            client=db.client
            def __getitem__(self,key):return FailingCollection() if key=='scenarios' else db[key]
        q=ResourceQuota(Database())
        try:
            async with q.admission(user,'P1','scenarios',1) as r:await q.persist(r,doc(user,'scenarios'),0)
        except RuntimeError:pass
        row=await db[collection].find_one({'_id':owner})
        assert await underlying.count_documents({'created_by':user['email']})==0
        assert row['subscription']['usage']['scenarios_used']==0 and row['resource_quota_pending']['scenarios_used']==0
    await run('transaction_abort_rolls_back_row_and_usage_together',rollback)

    async def lost_ack():
        user,collection,owner=await fixture();q=ResourceQuota(db);r=await q.reserve(user,'P1','scenarios',2)
        item=doc(user,'scenarios');original=q.transaction
        async def committed_then_lost(work):
            await original(work)
            raise HTTPException(503,'fixture lost commit acknowledgement')
        with patch.object(q,'transaction',committed_then_lost):await rejected(q.persist(r,item,0),503)
        await ResourceQuota(db).settle(r)
        await ResourceQuota(db).persist(r,item,0)
        row=await db[collection].find_one({'_id':owner})
        assert row['subscription']['usage']['scenarios_used']==1 and row['resource_quota_pending']['scenarios_used']==0
        assert await db['scenarios'].count_documents({'created_by':user['email']})==1
    await run('lost_commit_acknowledgement_reconciles_exactly_once',lost_ack)

    async def tiers():
        user,collection,owner=await fixture({'testcases_limit':2,'testcases_basic_limit':1,'testcases_medium_limit':1,'testcases_advanced_limit':1});q=ResourceQuota(db)
        basic=await q.reserve(user,'P1','testcases',1,'basic')
        await rejected(q.reserve(user,'P1','testcases',1,'basic'),403)
        medium=await q.reserve(user,'P1','testcases',1,'medium')
        await rejected(q.reserve(user,'P1','testcases',1,'advanced'),403)
        await q.persist(basic,doc(user,'testcases'),0);await q.persist(medium,doc(user,'testcases',tier='medium'),0)
        await q.settle(basic);await q.settle(medium)
        row=await db[collection].find_one({'_id':owner});assert row['subscription']['usage']['testcases_used']==2
    await run('aggregate_and_complexity_capacity_are_reserved_together',tiers)

    async def scope():
        user,collection,owner=await fixture({'scenarios_limit':1});q=ResourceQuota(db)
        other={**user,'_id':ObjectId(),'email':uuid4().hex+'@example.com','account_role':'MEMBER'};await db['users'].insert_one(other)
        results=await asyncio.gather(q.reserve(user,'P1','scenarios',1),ResourceQuota(db).reserve(other,'P2','scenarios',1),return_exceptions=True)
        wins=[r for r in results if isinstance(r,dict)]
        assert len(wins)==1 and sum(isinstance(r,HTTPException) and r.status_code==403 for r in results)==1
        await q.settle(wins[0])
        foreign,_,_=await fixture({'scenarios_limit':1})
        with patch.object(settings.features,'account_subscriptions',False):
            r=await q.reserve(foreign,'P1','scenarios',1)
            assert r['owner_collection']=='customer_accounts'
            await q.settle(r)
    await run('capacity_is_shared_across_account_users_and_projects_not_customers',scope)

    async def legacy():
        user,collection,owner=await fixture({'scenarios_limit':2},legacy=True)
        await db['users'].update_one({'_id':owner},{'$set':{'subscription.usage.scenarios_used':1}})
        await db['scenarios'].insert_one(doc(user,'scenarios'))
        q=ResourceQuota(db)
        with patch.object(settings.features,'account_subscriptions',False):
            async with q.admission(user,'P1','scenarios',20) as r:
                assert r['capacity']==1
                await q.persist(r,doc(user,'scenarios'),0)
            await rejected(q.reserve(user,'P1','scenarios',1),403)
        assert await db['scenarios'].count_documents({'created_by':user['email']})==2
    await run('legacy_user_scope_keeps_existing_inventory_and_limit',legacy)

    async def stale_recovery():
        user,_,_=await fixture();q=ResourceQuota(db);r=await q.reserve(user,'P1','scenarios',2)
        expected=fingerprint(await db['resource_quota_reservations'].find_one({'_id':r['_id']}))
        await q.persist(r,doc(user,'scenarios'),0)
        await rejected(q.settle(r,expected_digest=expected),409)
        fresh=await db['resource_quota_reservations'].find_one({'_id':r['_id']})
        await q.settle(r,expected_digest=fingerprint(fresh))
    await run('stale_operator_recovery_plan_is_rejected',stale_recovery)

    async def recovery_cli():
        import reconcile_resource_quota as cli
        user,collection,owner=await fixture();q=ResourceQuota(db);r=await q.reserve(user,'P1','scenarios',2)
        argv=['reconcile_resource_quota.py','--reservation-id',r['_id']]
        with patch.object(cli,'db',db), patch.object(settings,'app_env','test'):
            output=io.StringIO()
            with patch.object(sys,'argv',argv),redirect_stdout(output):await cli.main()
            plan=json.loads(output.getvalue());assert not plan['applied']
            await q.persist(r,doc(user,'scenarios'),0)
            with patch.object(sys,'argv',[*argv,'--apply','--confirm-close','--plan-digest',plan['plan_digest']]):
                await rejected(cli.main(),409)
            row=await db['resource_quota_reservations'].find_one({'_id':r['_id']})
            output=io.StringIO()
            with patch.object(sys,'argv',[*argv,'--apply','--confirm-close','--plan-digest',fingerprint(row)]),redirect_stdout(output):await cli.main()
            assert json.loads(output.getvalue())['state']=='SETTLED'
        row=await db[collection].find_one({'_id':owner})
        assert row['subscription']['usage']['scenarios_used']==1 and row['resource_quota_pending']['scenarios_used']==0
    await run('development_recovery_cli_dry_run_digest_and_confirmation',recovery_cli)

    async def corrupt():
        user,collection,owner=await fixture();q=ResourceQuota(db)
        await db[collection].update_one({'_id':owner},{'$set':{'resource_quota_pending.scenarios_used':-1}})
        await rejected(q.reserve(user,'P1','scenarios',1),503)
        assert await db['resource_quota_reservations'].count_documents({'owner_id':owner})==0
        other,_,_=await fixture();r=await q.reserve(other,'P1','testcases',1,'basic')
        await rejected(q.persist(r,doc(other,'testcases',tier='advanced'),0),422)
        await q.settle(r)
    await run('invalid_pending_state_and_tier_mismatch_fail_closed',corrupt)

    async def repeat():
        user,_,_=await fixture();q=ResourceQuota(db);key=uuid4().hex
        r=await q.reserve(user,'P1','scenarios',1,request_id=key)
        await rejected(q.reserve(user,'P1','scenarios',1,request_id=key),409)
        await q.settle(r)
        await rejected(q.reserve(user,'P1','scenarios',1,request_id=key),409)
    await run('same_request_identity_cannot_reserve_or_generate_twice',repeat)
    return checks


async def main():
    parser=argparse.ArgumentParser();parser.add_argument('--confirm-isolated-local',action='store_true',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    name='qa_resource_quota_'+uuid4().hex
    client=AsyncIOMotorClient('mongodb://127.0.0.1:27129/?replicaSet=qaTestDesign',serverSelectionTimeoutMS=5000,socketTimeoutMS=10000)
    with patch.object(settings,'features',FeatureFlags(customer_accounts=True,account_subscriptions=True)):
        try:
            assert (await client.admin.command('hello')).get('setName')=='qaTestDesign'
            checks=await verify(client[name])
        finally:
            await client.drop_database(name);client.close()
    report={'checks':checks,'database':'isolated-loopback-replica-set','cleanup':'generated database dropped','providers':'none'}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))

if __name__=='__main__':asyncio.run(main())
