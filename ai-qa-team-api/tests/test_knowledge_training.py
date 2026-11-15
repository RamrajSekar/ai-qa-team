"""M2 ASGI/project-role/Mongo/provider doubles; no real model or browser calls."""
import asyncio
import json
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import test_product_knowledge as fixtures
from app.models.product_knowledge import KnowledgeDraft


class TrainingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await fixtures.KnowledgeTests.asyncSetUp(self)
        self.db["knowledge_training_reviews"] = fixtures.Collection()
        self.db["scenarios"] = fixtures.Collection()
        self.db["testcases"] = fixtures.Collection()
        self.counter = 0
        self.questions = []
        async def extraction(operation, project, user, request):
            source = json.loads(request.prompt)
            return SimpleNamespace(text=json.dumps({"claims": [
                {"claim_id":f"P{i}","category":"business_rule","statement":text,"epistemic_status":"expected",
                 "source_id":source["source_id"],"quote":text,"segment_index":None}
                for i,text in enumerate(source["text"].splitlines()) if text.strip()],
                "clarification_questions": self.questions}))
        self.usage.execute.side_effect = extraction

    async def start(self, text="Rule one.\nRule two.\nRule three."):
        self.counter += 1
        response = await self.client.post(self.base+"/training",json={"request_id":f"{self.counter:032x}",
            "title":"Training", "source":{"title":"Guide","kind":"document","text":text}})
        self.assertEqual(response.status_code,201,response.text)
        return response.json()

    async def extract(self, review):
        response=await self.client.post(self.base+"/training/"+review["review_id"]+"/extract",json={})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    async def accept(self, review, answers=None):
        response=await self.client.post(self.base+"/training/"+review["review_id"]+"/review",json={
            "expected_revision":review["revision"],"proposals":[{**item,"decision":"confirmed"} for item in review["proposals"]],
            "clarification_answers":review["clarification_answers"] if answers is None else answers})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    async def save(self, review):
        response=await self.client.post(self.base+"/training/"+review["review_id"]+"/save",json={"expected_revision":review["revision"]})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    async def approve(self, review):
        response=await self.client.post(self.base+"/versions/"+review["saved_version"]["version_id"]+"/approve")
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    async def initial(self):
        return await self.approve(await self.save(await self.accept(await self.extract(await self.start()))))

    async def test_discard_stale_correction_and_removal_preserves_approved_knowledge(self):
        original = await self.initial()
        pending = []
        for index, mode in enumerate(("correction", "removal")):
            response = await self.client.post(self.base+"/training", json={"request_id":f"{100+index:032x}",
                "title":"Pending request", "mode":mode,"claim_id":original["claims"][0]["claim_id"]})
            pending.append(response.json())
        await self.initial()  # Both pending bases are now stale.
        before = deepcopy(self.db["product_knowledge_versions"].docs)
        calls = self.usage.execute.await_count
        self.user["role"] = "MEMBER"
        for row in pending:
            path=self.base+"/training/"+row["review_id"]+"/discard"
            response=await self.client.post(path,json={"expected_revision":9})
            self.assertEqual(response.status_code,409)
            response=await self.client.post(path,json={"expected_revision":row["revision"]})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()["state"],"rejected")
            self.assertEqual(response.json()["removed_claim_ids"],[])
            self.assertEqual((await self.client.post(path,json={"expected_revision":row["revision"]})).status_code,200)
            self.assertEqual((await self.client.post(path.replace("P1","P2"),json={"expected_revision":0})).status_code,404)
        self.assertEqual(self.db["product_knowledge_versions"].docs,before)
        self.assertEqual(self.usage.execute.await_count,calls)

    async def test_discard_cannot_revoke_saved_or_approved_training(self):
        review = await self.save(await self.accept(await self.extract(await self.start())))
        path=self.base+"/training/"+review["review_id"]+"/discard"
        self.assertEqual((await self.client.post(path,json={"expected_revision":review["revision"]})).status_code,409)
        await self.approve(review)
        self.assertEqual((await self.client.post(path,json={"expected_revision":review["revision"]})).status_code,409)

    async def test_all_rejected_review_closes_without_answers_or_knowledge_write(self):
        original = await self.initial()
        self.questions = ["Unused clarification?"]
        review = await self.extract(await self.start("Rejected new rule."))
        response = await self.client.post(self.base+"/training/"+review["review_id"]+"/review", json={
            "expected_revision": review["revision"],
            "proposals": [{**item, "decision": "rejected"} for item in review["proposals"]],
            "clarification_answers": review["clarification_answers"]})
        review = response.json()
        before = deepcopy(self.db["product_knowledge_versions"].docs)
        calls = self.usage.execute.await_count
        self.user["role"] = "MEMBER"
        closed = await self.save(review)
        self.assertEqual(closed["state"], "rejected")
        self.assertEqual(closed["clarification_answers"], {})
        self.assertEqual(closed["proposals"], [])
        self.assertNotIn("saved_version", closed)
        self.assertEqual(self.db["product_knowledge_versions"].docs, before)
        self.assertEqual((await self.service.active("P1"))["version_id"], original["version_id"])
        self.assertEqual((await self.save(review))["completed_at"], closed["completed_at"])
        self.assertEqual(self.usage.execute.await_count, calls)
        response = await self.client.post(self.base+"/training/"+review["review_id"]+"/review", json={
            "expected_revision": closed["revision"], "proposals": review["proposals"],
            "clarification_answers": review["clarification_answers"]})
        self.assertEqual(response.status_code, 409)

    async def test_no_change_completion_rejects_stale_revision_and_pending_proposals(self):
        review = await self.extract(await self.start("Not reviewed yet."))
        response = await self.client.post(self.base+"/training/"+review["review_id"]+"/save", json={"expected_revision": review["revision"]})
        self.assertEqual(response.status_code, 409)
        response = await self.client.post(self.base+"/training/"+review["review_id"]+"/review", json={
            "expected_revision": review["revision"], "proposals": [{**item,"decision":"rejected"} for item in review["proposals"]], "clarification_answers": {}})
        updated = response.json()
        response = await self.client.post(self.base+"/training/"+review["review_id"]+"/save", json={"expected_revision": review["revision"]})
        self.assertEqual(response.status_code, 409)
        self.assertEqual((await self.save(updated))["state"], "rejected")

    async def test_full_incremental_correction_and_resumable_clarification_journey(self):
        first=await self.initial();self.assertEqual(len(first["claims"]),3)
        self.questions=["When does the fourth rule apply?"]
        review=await self.accept(await self.extract(await self.start("Rule four.")))
        blocked=await self.client.post(self.base+"/training/"+review["review_id"]+"/save",json={"expected_revision":review["revision"]})
        self.assertEqual(blocked.status_code,409)
        # Fresh service/GET reloads decisions and blank answers without extraction.
        review=(await self.client.get(self.base+"/training/"+review["review_id"])).json()
        self.assertEqual(review["proposals"][0]["decision"],"confirmed")
        self.assertEqual(review["clarification_answers"][self.questions[0]],"")
        self.assertEqual(self.usage.execute.await_count,2)
        review=await self.accept(review,{self.questions[0]:"After saving."})
        fourth=await self.approve(await self.save(review));self.assertEqual(len(fourth["claims"]),4)
        target=fourth["claims"][0]
        response=await self.client.post(self.base+"/training",json={"request_id":"c"*32,"title":"Correction","mode":"correction","claim_id":target["claim_id"]})
        review=response.json();review["proposals"][0]["claim"]["statement"]="Rule one, clarified."
        updated=await self.client.post(self.base+"/training/"+review["review_id"]+"/review",json={"expected_revision":0,"proposals":[{**review["proposals"][0],"decision":"confirmed"}],"clarification_answers":{}})
        corrected=await self.approve(await self.save(updated.json()))
        self.assertEqual(corrected["claims"][1:],fourth["claims"][1:])
        self.assertEqual(corrected["claims"][0]["statement"],"Rule one, clarified.")
        self.assertEqual(self.usage.execute.await_count,2)

    async def test_member_can_review_and_save_but_only_admin_approves(self):
        self.user["role"]="MEMBER"
        review=await self.save(await self.accept(await self.extract(await self.start())))
        url=self.base+"/versions/"+review["saved_version"]["version_id"]+"/approve"
        self.assertEqual((await self.client.post(url)).status_code,403)
        self.assertIsNone(await self.service.active("P1"))
        self.user["role"]="ADMIN"
        self.assertEqual((await self.client.post(url)).status_code,200)
        self.assertEqual((await self.client.get(self.base+"/training/"+review["review_id"])).json()["saved_version"]["status"],"approved")

    async def test_completed_extraction_and_duplicate_submission_are_not_metered_again(self):
        review=await self.extract(await self.start())
        await self.extract(review)
        payload={"request_id":"0"*31+"1","title":"Training","source":{"title":"Guide","kind":"document","text":"Rule one.\nRule two.\nRule three."}}
        self.assertEqual((await self.client.post(self.base+"/training",json=payload)).json()["review_id"],review["review_id"])
        self.assertEqual(len(self.db["knowledge_training_reviews"].docs),1)
        self.assertEqual(len(self.db["product_knowledge_sources"].docs),1)
        self.assertEqual(self.usage.execute.await_count,1)
        self.assertEqual(self.usage.execute.call_args.args[3].max_retries,0)
        payload["title"]="Different"
        self.assertEqual((await self.client.post(self.base+"/training",json=payload)).status_code,409)

    async def test_concurrent_intent_submission_creates_one_pending_review_without_ai(self):
        payload={"request_id":"9"*32,"title":"One intent","source":{"title":"Guide","kind":"document","text":"Rule one."}}
        results=await asyncio.gather(*(self.client.post(self.base+"/training",json=payload) for _ in range(2)))
        self.assertEqual([item.status_code for item in results],[201,201])
        self.assertEqual(results[0].json()["draft_version_id"],results[1].json()["draft_version_id"])
        self.assertEqual(len(self.db["knowledge_training_reviews"].docs),1)
        self.assertFalse(self.usage.execute.called)

    async def test_parallel_extraction_has_one_model_call_and_uncertain_is_explicit(self):
        review=await self.start();entered=asyncio.Event();release=asyncio.Event()
        original=self.usage.execute.side_effect
        async def held(*args):
            entered.set();await release.wait();return await original(*args)
        self.usage.execute.side_effect=held
        first=asyncio.create_task(self.extract(review));await entered.wait()
        duplicate=await self.client.post(self.base+"/training/"+review["review_id"]+"/extract",json={})
        self.assertEqual(duplicate.status_code,409);release.set();await first
        self.assertEqual(self.usage.execute.await_count,1)
        other=await self.start("Rule four.")
        self.usage.execute.side_effect=TimeoutError("synthetic")
        from app.models.knowledge_training import TrainingExtract
        from app.services.knowledge_training import KnowledgeTraining
        service=KnowledgeTraining(self.db,self.service)
        with self.assertRaises(TimeoutError):await service.extract("P1",self.user,other["review_id"],TrainingExtract())
        pending=await service.get("P1",other["review_id"]);self.assertEqual(pending["extraction_state"],"uncertain")
        self.assertEqual((await self.client.post(self.base+"/training/"+other["review_id"]+"/extract",json={})).status_code,409)
        self.assertEqual(self.usage.execute.await_count,2)
        self.usage.execute.side_effect=original
        result=await self.client.post(self.base+"/training/"+other["review_id"]+"/extract",json={"retry_uncertain":True,"expected_attempt":1})
        self.assertEqual(result.status_code,200,result.text);self.assertEqual(self.usage.execute.await_count,3)

    async def test_interrupted_extraction_reconciles_without_replay(self):
        review=await self.start()
        row=self.db["knowledge_training_reviews"].docs[0]
        row.update(extraction_state="running",attempt=1,lease_expires_at="2000-01-01T00:00:00+00:00")
        result=await self.client.get(self.base+"/training/"+review["review_id"])
        self.assertEqual(result.json()["extraction_state"],"uncertain")
        self.assertFalse(self.usage.execute.called)

    async def test_lost_extraction_ack_recovers_completed_result_without_another_call(self):
        review=await self.start()
        from app.models.knowledge_training import TrainingExtract
        from app.services.knowledge_training import KnowledgeTraining
        service=KnowledgeTraining(self.db,self.service);rows=self.db["knowledge_training_reviews"];original=rows.update_one
        async def lost(query,update,**kwargs):
            await original(query,update,**kwargs)
            if update["$set"].get("extraction_state")=="completed":raise TimeoutError("synthetic lost acknowledgement")
        with patch.object(rows,"update_one",side_effect=lost):
            with self.assertRaises(TimeoutError):await service.extract("P1",self.user,review["review_id"],TrainingExtract())
        recovered=await service.get("P1",review["review_id"])
        self.assertEqual(recovered["extraction_state"],"completed")
        self.assertEqual(len(recovered["proposals"]),3)
        await service.extract("P1",self.user,review["review_id"],TrainingExtract())
        self.assertEqual(self.usage.execute.await_count,1)

    async def test_concurrent_review_updates_reject_stale_revision_and_scope(self):
        review=await self.extract(await self.start())
        payload={"expected_revision":review["revision"],"proposals":review["proposals"],"clarification_answers":{}}
        results=await asyncio.gather(*(self.client.post(self.base+"/training/"+review["review_id"]+"/review",json=payload) for _ in range(2)))
        self.assertEqual(sorted(item.status_code for item in results),[200,409])
        for suffix,body in [("",None),("/review",payload),("/extract",{}),("/save",{"expected_revision":0})]:
            url="/projects/P2/knowledge/training/"+review["review_id"]+suffix
            result=await self.client.get(url) if body is None else await self.client.post(url,json=body)
            self.assertEqual(result.status_code,404)

    async def test_rejection_preserves_approved_rule_and_removal_requires_approval(self):
        first=await self.initial();claim=first["claims"][0]
        review=(await self.client.post(self.base+"/training",json={"request_id":"d"*32,"title":"Correction","mode":"correction","claim_id":claim["claim_id"]})).json()
        review["proposals"][0]["decision"]="rejected"
        result=await self.client.post(self.base+"/training/"+review["review_id"]+"/review",json={"expected_revision":0,"proposals":review["proposals"],"clarification_answers":{}})
        rejected=result.json()
        self.assertEqual((await self.client.post(self.base+"/training/"+review["review_id"]+"/save",json={"expected_revision":rejected["revision"]})).status_code,200)
        self.assertEqual((await self.service.active("P1"))["claims"],first["claims"])
        removal=(await self.client.post(self.base+"/training",json={"request_id":"e"*32,"title":"Removal","mode":"removal","claim_id":claim["claim_id"]})).json()
        self.db["scenarios"] = fixtures.Collection({"project_id":"P1","scenario_id":"SC1","title":"Affected scenario","rule_references":[claim["claim_id"]]})
        self.db["testcases"] = fixtures.Collection({"project_id":"P1","testcase_id":"TC1","title":"Affected test","knowledge_version_id":first["version_id"]})
        impact=(await self.client.get(self.base+"/training/"+removal["review_id"])).json()["removal_impact"]
        self.assertEqual(impact["scenarios"][0]["id"],"SC1")
        self.assertEqual(impact["testcases"][0]["id"],"TC1")
        missing=await self.client.post(self.base+"/training/"+removal["review_id"]+"/save",json={"expected_revision":removal["revision"]})
        self.assertEqual(missing.status_code,409)
        removal=(await self.client.post(self.base+"/training/"+removal["review_id"]+"/review",json={"expected_revision":removal["revision"],"proposals":[],"clarification_answers":{},"removal_reason":"Feature retired"})).json()
        saved=await self.save(removal);self.assertEqual(len((await self.service.active("P1"))["claims"]),3)
        after=await self.approve(saved);self.assertEqual(len(after["claims"]),2)
        self.assertEqual(after["removal_reasons"],{claim["claim_id"]:"Feature retired"})

    async def test_lost_save_ack_recovers_same_immutable_draft(self):
        review=await self.accept(await self.extract(await self.start()))
        from app.models.knowledge_training import TrainingSave
        from app.services.knowledge_training import KnowledgeTraining
        service=KnowledgeTraining(self.db,self.service);rows=self.db["knowledge_training_reviews"];original=rows.update_one
        async def lost(query,update,**kwargs):
            await original(query,update,**kwargs)
            if update["$set"].get("state")=="saved":raise TimeoutError("synthetic")
        with patch.object(rows,"update_one",side_effect=lost):
            with self.assertRaises(TimeoutError):await service.save("P1","reviewer",review["review_id"],TrainingSave(expected_revision=review["revision"]))
        recovered=await service.save("P1","reviewer",review["review_id"],TrainingSave(expected_revision=review["revision"]))
        self.assertEqual(recovered["state"],"saved")
        self.assertEqual(len([item for item in self.db["product_knowledge_versions"].docs if item.get("version_id")==review["draft_version_id"]]),1)
        self.assertEqual(self.usage.execute.await_count,1)

    async def test_stale_training_cannot_silently_rebase_and_sources_stay_authorized(self):
        first=await self.initial()
        pending=await self.accept(await self.extract(await self.start("Rule four.")))
        draft=await self.service.create_version("P1","reviewer",KnowledgeDraft(title="Concurrent",claims=[{**first["claims"][0],"claim_id":"K_new"}]))
        await self.service.approve("P1","reviewer",draft["version_id"])
        response=await self.client.post(self.base+"/training/"+pending["review_id"]+"/save",json={"expected_revision":pending["revision"]})
        self.assertEqual(response.status_code,409)
        rebased=await self.client.post(self.base+"/training/"+pending["review_id"]+"/rebase",json={"expected_revision":pending["revision"],"request_id":"b"*32})
        self.assertEqual(rebased.status_code,200,rebased.text)
        self.assertEqual(rebased.json()["proposals"][0]["decision"],"pending")
        self.assertEqual(rebased.json()["base_version_id"],draft["version_id"])
        saved=await self.save(await self.accept(rebased.json()))
        self.assertEqual(len((await self.approve(saved))["claims"]),5)
        self.assertEqual(self.usage.execute.await_count,2)
        self.assertEqual((await self.client.get(self.base+"/sources/"+pending["source_id"])).status_code,200)
        self.assertEqual((await self.client.get("/projects/P2/knowledge/sources/"+pending["source_id"])).status_code,404)

    async def test_reopening_source_reuses_persisted_extraction_and_story_evidence_stays_inferred(self):
        review=await self.extract(await self.start())
        reopened=await self.client.post(self.base+"/training",json={"request_id":"f"*32,"title":"Guide","source_id":review["source_id"]})
        self.assertEqual(reopened.json()["review_id"],review["review_id"])
        await self.extract(reopened.json());self.assertEqual(self.usage.execute.await_count,1)
        source=(await self.client.post(self.base+"/training",json={"request_id":"a"*32,"title":"From story","story_id":"ST1"})).json()
        extracted=await self.extract(source)
        self.assertTrue(all(item["claim"]["epistemic_status"]=="inferred" for item in extracted["proposals"]))
        saved=await self.save(await self.accept(extracted));await self.approve(saved)
        with self.assertRaises(fixtures.HTTPException):await self.service.analyze("P1",self.user,"ST1")

    async def test_proposal_clarification_is_durable_and_required_before_save(self):
        review=await self.extract(await self.start())
        for item in review["proposals"]:item["decision"]="confirmed"
        review["proposals"][0].update(clarification_question="Who saves?",clarification_answer="")
        result=await self.client.post(self.base+"/training/"+review["review_id"]+"/review",json={"expected_revision":review["revision"],"proposals":review["proposals"],"clarification_answers":{}})
        persisted=result.json();blocked=await self.client.post(self.base+"/training/"+review["review_id"]+"/save",json={"expected_revision":persisted["revision"]})
        self.assertEqual(blocked.status_code,409)
        resumed=(await self.client.get(self.base+"/training/"+review["review_id"])).json()
        self.assertEqual(resumed["proposals"][0]["clarification_question"],"Who saves?")
        resumed["proposals"][0]["clarification_answer"]="The reviewer."
        reviewed=(await self.client.post(self.base+"/training/"+review["review_id"]+"/review",json={"expected_revision":resumed["revision"],"proposals":resumed["proposals"],"clarification_answers":{}})).json()
        saved=await self.save(reviewed)
        self.assertEqual(saved["saved_version"]["clarification_answers"]["Who saves?"],"The reviewer.")
