"""Explicit development Mongo verification; synthetic data, no login/provider/browser calls."""
import asyncio
from contextlib import ExitStack
import json
from uuid import uuid4
from unittest.mock import patch
from fastapi import HTTPException
from app.config import settings
from app.db.connection import db
from app.models.test_design_review import TestDesignDraft
from app.models.test_result import ManualExecutionInput, ManualResultInput
from app.services.approved_visual_run import digest
from app.services.test_design_review import TestDesignReview
from app.services.test_results import TestResults
from verify_customer_accounts_real import FixtureDB

async def main():
    if settings.app_env.lower() not in {'development','local','test'}: raise SystemExit('Development services only.')
    prefix='manual_results_fixture_'+uuid4().hex+'_';database=FixtureDB(prefix);checks={};stage='readiness';cleanup=False
    try:
        await asyncio.wait_for(db.command('ping'),15)
        with ExitStack() as stack:
            for flag in ('manual_test_results','test_generation','product_knowledge','story_analysis'): stack.enter_context(patch.object(settings.features,flag,True))
            project=prefix+'project';story={'story_id':'ST1','title':'Save draft','description':'Synthetic','acceptance_criteria':'Show Draft saved.','out_of_scope':''}
            await database['stories'].insert_one({**story,'project_id':project})
            await database['product_knowledge_versions'].insert_one({'version_id':'a'*32,'project_id':project,'status':'approved','approved_at':'2026-11-13T00:00:00Z','content_digest':'b'*64,'claims':[{'claim_id':'K1','statement':'Show Draft saved.','epistemic_status':'expected'}]})
            await database['story_analyses'].insert_one({'analysis_id':'c'*32,'project_id':project,'story_id':'ST1','created_at':'2026-11-13T00:00:00Z','status':'reviewed','story_digest':digest(story),'knowledge_version_id':'a'*32,'findings':[],'resolutions':[]})
            await database['scenarios'].insert_one({'project_id':project,'scenario_id':'SC1','story_id':'ST1','approved':True,'title':'Draft coverage','knowledge_version_id':'a'*32})
            review=TestDesignReview(database);selected=[]
            for i in range(2):
                case_id='TC'+str(i+1);await database['testcases'].insert_one({'project_id':project,'testcase_id':case_id,'scenario_id':'SC1','title':'Synthetic case '+str(i),'knowledge_version_id':'a'*32})
                content={'title':'Synthetic case '+str(i),'purpose':'Check confirmation','role':None,'preconditions':[],'public_data':[],'procedure':[{'instruction':'Click Save','expected':'Draft saved'}],'assertions':['Draft saved appears'],'cleanup':[],'acceptance_criteria_refs':['Show Draft saved.'],'rule_references':['K1']}
                version=await review.create(project,case_id,'fixture-reviewer',TestDesignDraft(case=content,idempotency_key=uuid4().hex))
                approved=await review.approve(project,case_id,'fixture-reviewer',version['version_id'],actor_name='Fixture Approver',project_role='TESTER');selected.append({'testcase_id':case_id,'version_id':approved['version_id']})
            service=TestResults(database);payload=ManualExecutionInput(title='Synthetic Release 2',release_cycle='Cycle A',cases=selected,idempotency_key=uuid4().hex)
            stage='real_mongo_execution_creation_contention'
            first,second=await asyncio.gather(service.create_execution(project,'fixture',payload),service.create_execution(project,'fixture',payload));assert first==second;execution=first['execution_id'];assert await database['manual_test_executions'].count_documents({})==1;checks[stage]=True
            stage='real_mongo_case_result_contention'
            result=ManualResultInput(execution_id=execution,version_id=selected[0]['version_id'],idempotency_key=uuid4().hex,actual_result='Draft saved appeared',verdict='passed',verified_expectation_ids=['step:0','assertion:0'])
            a,b=await asyncio.gather(service.record_manual(project,'TC1','fixture',result),service.record_manual(project,'TC1','fixture',result));assert a['run_id']==b['run_id'];assert await database['test_results'].count_documents({})==1;checks[stage]=True
            stage='pinned_failure_fresh_service_and_summary'
            await database['stories'].update_one({'project_id':project},{'$set':{'title':'Later story edit'}})
            await service.record_manual(project,'TC2','fixture',ManualResultInput(execution_id=execution,version_id=selected[1]['version_id'],idempotency_key=uuid4().hex,actual_result='Confirmation missing',verdict='failed'))
            fresh=TestResults(database);state=await fresh.execution(project,execution);assert state['lifecycle']=='completed' and {row['verdict'] for row in state['results']}=={'passed','failed'}
            assert all(row['specification']['approved_by']=='fixture-reviewer' and row['specification']['approved_by_display_name']=='Fixture Approver' for row in state['results'])
            summaries=await fresh.summaries(project,['TC1','TC2']);assert summaries['TC1']['manual']['verdict']=='passed' and summaries['TC2']['manual']['verdict']=='failed';assert summaries['TC1']['design_status']=='approved';assert all(item['automated'] is None for item in summaries.values());checks[stage]=True
            stage='scope_and_immutable_completion'
            try: await fresh.execution('FOREIGN',execution)
            except HTTPException as error: assert error.status_code==404
            else: raise AssertionError('foreign execution visible')
            try: await fresh.record_manual(project,'TC1','fixture',result.model_copy(update={'actual_result':'Changed'}))
            except HTTPException as error: assert error.status_code==409
            else: raise AssertionError('result changed')
            assert await database['test_results'].count_documents({})==2;checks[stage]=True
            stage='legacy_manual_approval_without_knowledge'
            with patch.object(settings.features,'product_knowledge',False),patch.object(settings.features,'story_analysis',False):
                await database['testcases'].insert_one({'project_id':project,'testcase_id':'TC3','scenario_id':'SC3','title':'Legacy manual case'})
                await database['scenarios'].insert_one({'project_id':project,'scenario_id':'SC3','story_id':'ST1','approved':True,'title':'Legacy coverage'})
                for field in ('assertions','cleanup','acceptance_criteria_refs','rule_references'): content.pop(field,None)
                draft=await review.create(project,'TC3','fixture-reviewer',TestDesignDraft(case=content,idempotency_key=uuid4().hex))
                version=await review.approve(project,'TC3','fixture-reviewer',draft['version_id'])
                result=await fresh.record_manual(project,'TC3','fixture',ManualResultInput(version_id=version['version_id'],idempotency_key=uuid4().hex,actual_result='Draft saved appeared',verdict='passed',verified_expectation_ids=['step:0']))
                assert result['specification']['design_basis']=='reviewer-authored-expectations-v1' and result['specification']['knowledge_version_id'] is None
                checks[stage]=True

    except Exception as error: checks['failure_stage']=stage;checks['failure_type']=type(error).__name__
    finally:
        try:
            for name in database.names:
                assert name.startswith(prefix);await asyncio.wait_for(db[name].drop(),15)
            cleanup=True
        except Exception: cleanup=False
        print(json.dumps({'real_development_mongo':checks,'fixture_cleanup':cleanup,'real_login_verified':False,'external_calls':0},indent=2))
    if not cleanup or 'failure_type' in checks: raise SystemExit(1)
if __name__=='__main__':asyncio.run(main())
