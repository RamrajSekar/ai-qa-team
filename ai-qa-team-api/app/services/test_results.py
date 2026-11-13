"""Append-only version-linked results. No browser, provider, secrets or legacy queue."""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.models.test_result import TestResult
from app.services.approved_visual_run import digest
from app.services.test_design_review import TestDesignReview


def expectations(case):
    return ([{"id": f"step:{i}", "text": step["expected"]} for i, step in enumerate(case.get("procedure", [])) if step.get("expected", "").strip()]
        + [{"id": f"assertion:{i}", "text": text} for i, text in enumerate(case.get("assertions", [])) if text.strip()])


class TestResults:
    def __init__(self, database):
        self.db = database

    async def case_exists(self, project, case):
        if not await self.db["testcases"].find_one({"project_id": project, "testcase_id": case}):
            raise HTTPException(404, "Test case not found in this project.")

    @staticmethod
    def public(record):
        return TestResult.model_validate({key: value for key, value in record.items() if key in TestResult.model_fields}).model_dump()

    async def eligible(self, project, case):
        try:
            state = await TestDesignReview(self.db).state(project, case)
        except HTTPException as exc:
            if exc.status_code not in (403, 409): raise
            return None, "Enable test design review and approve a current test design before recording results."
        version = next((v for v in state["versions"] if v["version_id"] == state["active_version_id"] and v["status"] == "approved"), None)
        if not version or state["review_required"]:
            return None, "Review and approve a current test design first. Draft or stale designs cannot receive a new result."
        return version, None

    async def history(self, project, case, skip=0):
        await self.case_exists(project, case)
        version, reason = await self.eligible(project, case)
        rows = await self.db["test_results"].find({"project_id": project, "testcase_id": case}).sort([("recorded_at", -1), ("_id", -1)]).skip(skip).limit(21).to_list(21)
        environments = await self.db["environments"].find({"project_id": project}, {"env_id": 1, "name": 1, "env_type": 1}).limit(100).to_list(100)
        return {"eligible_version": ({"version_id": version["version_id"], "case": version["case"], "expectations": expectations(version["case"])} if version else None),
                "reason": reason, "records": [self.public(row) for row in rows[:20]], "has_more": len(rows) > 20,
                "environments": [{"env_id": env["env_id"], "name": env.get("name") or env.get("env_type") or env["env_id"]} for env in environments if env.get("env_id")]}

    async def summaries(self, project, case_ids):
        # One aggregation, scoped before grouping; never load another project's results.
        pipeline = [{"$match": {"project_id": project, "testcase_id": {"$in": case_ids}}},
                    {"$sort": {"recorded_at": -1, "_id": -1}},
                    {"$group": {"_id": {"case": "$testcase_id", "mode": "$mode"}, "latest": {"$first": "$$ROOT"}}}]
        rows = await self.db["test_results"].aggregate(pipeline).to_list(100)
        documents = await self.db["test_design_documents"].find({"project_id": project, "testcase_id": {"$in": case_ids}}, {"testcase_id": 1, "active_version_id": 1, "versions.version_id": 1, "versions.status": 1, "versions.parent_version_id": 1}).to_list(50)
        result = {case: {"manual": None, "automated": None, "approved_version_id": None, "design_status": None} for case in case_ids}
        for document in documents:
            active = document.get("active_version_id")
            result[document["testcase_id"]]["approved_version_id"] = active
            pending = any(version.get("status") == "draft" and version.get("parent_version_id") == active for version in document.get("versions", []))
            result[document["testcase_id"]]["design_status"] = "in_review" if pending else "approved" if active else "draft"
        for row in rows:
            record = row["latest"]
            if record["mode"] in ("manual", "automated"):
                result[record["testcase_id"]][record["mode"]] = {**{key: record[key] for key in ("run_id", "mode", "verdict", "recorded_at")}, "version_id": record["specification"]["version_id"], "execution_id": record.get("execution_id")}
        return result

    @staticmethod
    def specification(version):
        context = version.get("context", {})
        return {"version_id": version["version_id"], "content_digest": version["content_digest"], "case": version["case"],
                "approved_by": version.get("approved_by"), "approved_at": version.get("approved_at"),
                "approved_by_display_name": version.get("approved_by_display_name"), "approved_by_project_role": version.get("approved_by_project_role"),
                "approval_policy": version.get("approval_policy"),
                **{field: context.get(field) for field in ("design_basis", "story_id", "scenario_id", "knowledge_version_id", "story_analysis_id")}}

    async def environment(self, project, env_id):
        if not env_id: return None
        env = await self.db["environments"].find_one({"project_id": project, "env_id": env_id}, {"env_id": 1, "name": 1, "env_type": 1, "revision": 1})
        if not env: raise HTTPException(404, "Environment not found in this project.")
        return {field: env.get(field) for field in ("env_id", "name", "env_type", "revision")}

    async def create_execution(self, project, actor, payload):
        key = digest(["manual-execution-v1", project, actor, payload.idempotency_key])
        fingerprint = digest(payload.model_dump())
        existing = await self.db["manual_test_executions"].find_one({"_id": key, "project_id": project})
        if existing:
            if existing["request_digest"] != fingerprint: raise HTTPException(409, "This execution save key was used with different content.")
            return {"execution_id": existing["execution_id"]}
        if not payload.title.strip() or not payload.release_cycle.strip(): raise HTTPException(422, "Enter a title and Release/Cycle details.")
        if len({item.testcase_id for item in payload.cases}) != len(payload.cases): raise HTTPException(422, "Select each case once.")
        pinned = []
        for selected in payload.cases:
            await self.case_exists(project, selected.testcase_id)
            version, reason = await self.eligible(project, selected.testcase_id)
            if not version or version["version_id"] != selected.version_id: raise HTTPException(409, reason or "A selected approval changed. Refresh your selection.")
            pinned.append({"testcase_id": selected.testcase_id, "specification": self.specification(version)})
        manifest = {"title": payload.title.strip(), "release_cycle": payload.release_cycle.strip(), "mode": "manual", "adapter": "human-report-v1",
                    "environment": await self.environment(project, payload.environment_id), "cases": pinned}
        record = {"_id": key, "execution_id": uuid4().hex, "schema_version": "manual-execution-v1", "project_id": project,
                  "manifest": manifest, "manifest_digest": digest(manifest), "created_by": actor,
                  "created_at": datetime.now(timezone.utc).isoformat(), "request_digest": fingerprint}
        try: await self.db["manual_test_executions"].insert_one(record)
        except DuplicateKeyError:
            existing = await self.db["manual_test_executions"].find_one({"_id": key, "project_id": project})
            if not existing or existing["request_digest"] != fingerprint: raise HTTPException(409, "Execution save conflicted. Refresh before retrying.") from None
            record = existing
        return {"execution_id": record["execution_id"]}

    async def execution(self, project, execution_id):
        execution = await self.db["manual_test_executions"].find_one({"project_id": project, "execution_id": execution_id})
        if not execution: raise HTTPException(404, "Manual execution not found in this project.")
        records = await self.db["test_results"].find({"project_id": project, "execution_id": execution_id}).limit(10).to_list(10)
        public = {key: execution[key] for key in ("execution_id", "schema_version", "project_id", "manifest", "manifest_digest", "created_by", "created_at")}
        count = len(records)
        public.update({"results": [self.public(row) for row in records], "expectations": {item["testcase_id"]: expectations(item["specification"]["case"]) for item in execution["manifest"]["cases"]}, "completed_count": count,
                       "lifecycle": "completed" if count == len(execution["manifest"]["cases"]) else "in_progress"})
        return public

    async def executions(self, project, skip):
        rows = await self.db["manual_test_executions"].find({"project_id": project}).sort([("created_at", -1), ("_id", -1)]).skip(skip).limit(21).to_list(21)
        return {"records": [{"execution_id": row["execution_id"], "title": row["manifest"]["title"], "release_cycle": row["manifest"]["release_cycle"],
                             "mode": "manual", "case_count": len(row["manifest"]["cases"]), "created_at": row["created_at"]} for row in rows[:20]], "has_more": len(rows) > 20}

    async def record_manual(self, project, case, actor, payload, *, actor_name=None):
        await self.case_exists(project, case)
        # _id makes duplicate submission safe even after source changes or a lost response.
        key = digest(["manual-execution-case-v1", project, payload.execution_id, case]) if payload.execution_id else digest(["manual-result-v1", project, case, actor, payload.idempotency_key])
        fingerprint = digest(payload.model_dump(exclude={"idempotency_key"}) if payload.execution_id else payload.model_dump())
        existing = await self.db["test_results"].find_one({"_id": key, "project_id": project, "testcase_id": case})
        if existing:
            if existing["request_digest"] != fingerprint: raise HTTPException(409, "This save key was used with different content.")
            return self.public(existing)
        execution = None
        if payload.execution_id:
            execution = await self.execution(project, payload.execution_id)
            pinned = next((item for item in execution["manifest"]["cases"] if item["testcase_id"] == case), None)
            if not pinned or pinned["specification"]["version_id"] != payload.version_id: raise HTTPException(409, "This case/version is not in the selected execution.")
            spec = pinned["specification"]
            version = {"version_id": spec["version_id"], "case": spec["case"]}
        else:
            version, reason = await self.eligible(project, case)
            if not version or version["version_id"] != payload.version_id:
                raise HTTPException(409, reason or "The approved version changed. Reload and review before recording a new result.")
            spec = self.specification(version)
        actual = payload.actual_result.strip()
        if not actual: raise HTTPException(422, "Describe the actual result without credentials or personal data.")
        required = {item["id"] for item in expectations(version["case"])}
        verified = set(payload.verified_expectation_ids)
        if len(verified) != len(payload.verified_expectation_ids) or not verified.issubset(required):
            raise HTTPException(422, "Select only the approved expectations, once each.")
        if payload.verdict == "passed" and (not required or verified != required):
            raise HTTPException(422, "Confirm every approved expectation before reporting Passed.")
        environment = execution["manifest"]["environment"] if execution else await self.environment(project, payload.environment_id)
        if execution and payload.environment_id and (environment or {}).get("env_id") != payload.environment_id:
            raise HTTPException(409, "The execution environment is pinned and cannot be replaced.")
        result = TestResult(run_id=uuid4().hex, execution_id=payload.execution_id, project_id=project, testcase_id=case, mode="manual", adapter="human-report-v1",
            lifecycle="cancelled" if payload.verdict == "cancelled" else "completed", verdict=payload.verdict, actual_result=actual,
            verified_expectation_ids=payload.verified_expectation_ids, specification=spec, environment=environment,
            executor_id=actor, executor_display_name=actor_name[:240] if actor_name else None, recorded_at=datetime.now(timezone.utc).isoformat()).model_dump()
        try:
            await self.db["test_results"].insert_one({"_id": key, "request_digest": fingerprint, **result})
        except DuplicateKeyError:
            existing = await self.db["test_results"].find_one({"_id": key, "project_id": project, "testcase_id": case})
            if not existing or existing["request_digest"] != fingerprint:
                raise HTTPException(409, "Result save conflicted. Reload before saving again.") from None
            return self.public(existing)
        return result
