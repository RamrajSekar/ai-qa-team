"""Explicit requirements approvals, separate from product knowledge and execution."""
from datetime import datetime, timezone
import json
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from app.services.approved_visual_run import digest
from app.services.product_knowledge import ProductKnowledge
from app.utils.feature_flags import require_features


class RequirementContexts:
    def __init__(self,database):
        self.db=database;self.rows=database["requirement_contexts"];self.knowledge=ProductKnowledge(database)

    @staticmethod
    def gate():require_features("product_knowledge","story_analysis")

    @staticmethod
    def key(kind,project,*values):return kind+":"+digest([project,*values])

    async def row(self,project,story,identity):
        self.gate()
        row=await self.rows.find_one({"_id":identity,"project_id":project,"story_id":story,"record_type":"context"})
        if not row:raise HTTPException(404,"Requirements context not found in this story.")
        if digest({key:value for key,value in row.items() if key!="content_digest"})!=row["content_digest"]:
            raise HTTPException(409,"Requirements content integrity check failed.")
        return row

    async def head(self,project,story,release):
        current=None
        for _ in range(100):
            receipt=await self.rows.find_one({"_id":self.key("activation",project,story,release,current),"project_id":project})
            if not receipt:return current
            if receipt.get("impact_state")!="completed":raise HTTPException(409,"Release activation requires impact reconciliation. Retry its explicit activation.")
            current=receipt["context_id"]
        raise HTTPException(409,"Release history requires maintenance.")

    async def approval(self,row):
        receipt=await self.rows.find_one({"_id":self.key("approval",row["project_id"],row["context_id"]),"project_id":row["project_id"]})
        if receipt and receipt["content_digest"]!=row["content_digest"]:raise HTTPException(409,"Requirements approval integrity check failed.")
        return receipt

    async def fresh(self,row,require_review=True):
        story=await self.knowledge.story(row["project_id"],row["story_id"])
        knowledge=await self.knowledge.active(row["project_id"])
        if digest(story)!=row["story_digest"] or (row["basis"]=="approved_change" and ((knowledge or {}).get("version_id")!=row["base_knowledge_version_id"] or digest((knowledge or {}).get("claims",[]))!=row["base_knowledge_digest"])):
            raise HTTPException(409,"Story or product knowledge changed. Save and approve a new requirements context.")
        latest=await self.knowledge.latest_analysis(row["project_id"],row["story_id"])
        if not latest or latest["analysis_id"]!=row["analysis_id"] or latest["stale"]:
            raise HTTPException(409,"Analysis changed. Review a new requirements context.")
        analysis=await self.knowledge.record("story_analyses",row["project_id"],row["analysis_id"])
        if analysis.get("story_id")!=row["story_id"] or (require_review and analysis.get("status")!="reviewed") or digest(analysis)!=row["analysis_digest"]:
            raise HTTPException(409,"Pinned analysis review changed. Review a new requirements context.")
        return story,knowledge,analysis

    async def view(self,row):
        if digest({key:value for key,value in row.items() if key!="content_digest"})!=row["content_digest"]:
            raise HTTPException(409,"Requirements content integrity check failed.")
        receipt=await self.approval(row)
        try:await self.fresh(row,require_review=bool(receipt));stale=False
        except HTTPException as error:
            if error.status_code!=409:raise
            stale=True
        activation=await self.rows.find_one({"_id":self.key("activation",row["project_id"],row["story_id"],row["target_release"],row["parent_context_id"]),"project_id":row["project_id"]})
        activated=bool(activation and activation["context_id"]==row["context_id"])
        try:head=await self.head(row["project_id"],row["story_id"],row["target_release"])
        except HTTPException:head=None
        if head not in (row["parent_context_id"],row["context_id"]):stale=True
        status="activating" if activated and activation.get("impact_state")!="completed" else "active" if activated and head==row["context_id"] else "superseded" if activated else "approved" if receipt else "draft"
        return {**self.knowledge.public(row),"status":status,"stale":stale,
            "approver":{key:receipt[key] for key in ("approved_by","approved_by_name","approved_by_role","approved_at")} if receipt else None}

    async def listing(self,project,story):
        self.gate();await self.knowledge.story(project,story)
        rows=await self.rows.find({"project_id":project,"story_id":story,"record_type":"context"}).sort("created_at",-1).to_list(50)
        knowledge=await self.knowledge.active(project)
        rules={c["claim_id"]:{"claim_id":c["claim_id"],"statement":c["statement"]} for c in (knowledge or {}).get("claims",[])}
        for row in rows:
            if await self.approval(row):
                for decision in row.get("effective_decisions",[]):
                    rules.setdefault(decision["requirement_id"],{"claim_id":decision["requirement_id"],"statement":row["target_release"]+": "+decision["expected_result"]})
        views=[await self.view(row) for row in rows]
        return {"contexts":[{key:row[key] for key in ("context_id","basis","target_release","status","stale","approver")} for row in views],"rules":list(rules.values())[:200],"current_knowledge_version_id":(knowledge or {}).get("version_id")}

    async def impact(self,row):
        result={};rules={d["rule_id"] for d in row["decisions"] if d.get("rule_id")}
        for collection,identity in (("scenarios","scenario_id"),("testcases","testcase_id")):
            rows=await self.db[collection].find({"project_id":row["project_id"]}).to_list(1001)
            if len(rows)>1000:raise HTTPException(409,"Impact review exceeds the supported size. Review dependencies before activation.")
            result[collection]=[{"id":item[identity],"title":item.get("title","")} for item in rows
                if item.get("requirements_context_id")!=row["context_id"] and (set(item.get("rule_references") or [])&rules
                or (row["base_knowledge_version_id"] and item.get("knowledge_version_id")==row["base_knowledge_version_id"]))]
        return result

    async def create(self,project,story_id,actor,payload):
        self.gate();existing=await self.rows.find_one({"_id":payload.request_id})
        request_digest=digest(payload.model_dump())
        if existing:
            if existing.get("project_id")!=project or existing.get("story_id")!=story_id or existing.get("request_digest")!=request_digest:
                raise HTTPException(409,"This save key is already in use. Reload before saving.")
            return {**await self.view(existing),"impact":await self.impact(existing)}
        story=await self.knowledge.story(project,story_id)
        analysis=await self.knowledge.latest_analysis(project,story_id)
        if not analysis or analysis["analysis_id"]!=payload.analysis_id or analysis["stale"]:
            raise HTTPException(409,"Analyze and review the current story before saving a requirements context.")
        raw_analysis=await self.knowledge.record("story_analyses",project,payload.analysis_id)
        knowledge=await self.knowledge.active(project)
        if payload.basis=="story_only_provisional" and analysis.get("analysis_mode")!="story_only":
            raise HTTPException(409,"Provisional designs require an explicit reviewed story-only analysis.")
        decisions=[d.model_dump() for d in payload.decisions];findings={f["finding_id"]:f for f in analysis["findings"]}
        selected=[d["finding_id"] for d in decisions if d.get("finding_id")]
        if len(selected)!=len(set(selected)) or set(selected)-set(findings):raise HTTPException(422,"Select each available finding once.")
        release=payload.target_release.strip()
        parent_id=await self.head(project,story_id,release)
        parent=await self.row(project,story_id,parent_id) if parent_id else None
        if parent and not await self.approval(parent):raise HTTPException(409,"Release parent approval is unavailable.")
        inherited=(parent or {}).get("effective_decisions",[])
        rules={c["claim_id"] for c in (knowledge or {}).get("claims",[])}|{d["requirement_id"] for d in inherited}
        changed=[d["rule_id"] for d in decisions if d.get("rule_id")]
        if len(changed)!=len(set(changed)) or set(changed)-rules:raise HTTPException(422,"Choose each affected approved rule once.")
        for decision in decisions:
            finding=findings.get(decision.get("finding_id"))
            if finding and finding.get("knowledge_claim_id") and decision["decision"]=="intentional_change" and decision.get("rule_id")!=finding["knowledge_claim_id"]:
                raise HTTPException(422,"A conflict decision must address its linked knowledge rule.")
        if payload.basis=="approved_change" and {f["finding_id"] for f in findings.values() if f["category"]=="knowledge_conflict"}-set(selected):
            raise HTTPException(422,"Record a decision for every knowledge conflict.")
        effective={d["requirement_id"]:dict(d) for d in inherited} if payload.basis=="approved_change" else {}
        for index,decision in enumerate(decisions):
            if decision["decision"]=="intentional_change":
                key=decision.get("rule_id") or "R_"+payload.request_id+"_"+str(index)
                effective[key]={**decision,"requirement_id":key,"approved_context_origin":payload.request_id}
        row={"_id":payload.request_id,"context_id":payload.request_id,"record_type":"context","project_id":project,
            "story_id":story_id,"basis":payload.basis,"target_release":release,"decisions":decisions,
            "story_digest":digest(story),"story_snapshot":story,"analysis_id":payload.analysis_id,"analysis_digest":digest(raw_analysis),
            "base_knowledge_version_id":(knowledge or {}).get("version_id") if payload.basis=="approved_change" else None,
            "base_knowledge_digest":digest((knowledge or {}).get("claims",[])),"parent_context_id":parent_id,
            "effective_decisions":list(effective.values()),
            "created_by":actor,"created_at":datetime.now(timezone.utc).isoformat(),"request_digest":request_digest}
        row["content_digest"]=digest(row)
        if len(effective)>100 or len(json.dumps(row).encode())>250000:
            raise HTTPException(413,"Release requirements exceed the review size limit. Preserve history and reduce this context's scope.")
        impact=await self.impact(row)
        try:await self.rows.insert_one(row)
        except DuplicateKeyError:raise HTTPException(409,"Save already exists. Reload to reconcile.") from None
        return {**await self.view(row),"impact":impact}

    async def approve(self,project,story,identity,actor):
        row=await self.row(project,story,identity)
        if await self.approval(row):return {**await self.view(row),"impact":await self.impact(row)}
        await self.fresh(row)
        if row["basis"]=="approved_change" and any(d["decision"]!="intentional_change" for d in row["decisions"]):
            raise HTTPException(409,"Correct the story or clarify unresolved decisions before approving intentional changes.")
        if await self.head(project,story,row["target_release"])!=row["parent_context_id"]:
            raise HTTPException(409,"Release context changed. Review a new draft.")
        impact=await self.impact(row)
        receipt={"_id":self.key("approval",project,identity),"project_id":project,"record_type":"approval", "context_id":identity,
            "content_digest":row["content_digest"],"approved_by":str(actor.get("_id") or actor.get("email")),
            "approved_by_name":actor.get("name") or actor.get("email") or "Project administrator",
            "approved_by_role":"ADMIN","approved_at":datetime.now(timezone.utc).isoformat()}
        try:await self.rows.insert_one(receipt)
        except DuplicateKeyError:pass
        return {**await self.view(row),"impact":impact}

    async def activate(self,project,story,identity,actor):
        row=await self.row(project,story,identity)
        if row["basis"]!="approved_change" or not await self.approval(row):raise HTTPException(409,"Approve an intentional release change before activation.")
        key=self.key("activation",project,story,row["target_release"],row["parent_context_id"])
        previous=await self.rows.find_one({"_id":key,"project_id":project})
        if previous and previous["context_id"]==identity:
            impact=previous["impact"]
            if previous.get("impact_state")=="completed":return {**await self.view(row),"impact":impact}
        else:
            await self.fresh(row);impact=await self.impact(row)
        receipt={"_id":key,"project_id":project,"record_type":"activation","context_id":identity,"impact_state":"pending","impact":impact,
            "activated_by":actor,"activated_at":datetime.now(timezone.utc).isoformat()}
        try:await self.rows.insert_one(receipt)
        except DuplicateKeyError:
            winner=await self.rows.find_one({"_id":key,"project_id":project})
            if not winner or winner["context_id"]!=identity:raise HTTPException(409,"Another release context won activation. Reload before continuing.") from None
        try:
            # Idempotent metadata reconciliation only; never update approvals or executions.
            for collection,rows in impact.items():
                field="scenario_id" if collection=="scenarios" else "testcase_id"
                for item in rows:
                    await self.db[collection].update_one({"project_id":project,field:item["id"]},{"$set":{
                        "requirements_review_required":True,"requirements_review_context_id":identity,"requirements_review_release":row["target_release"],
                        "requirements_reviews."+digest(row["target_release"]):{"context_id":identity,"release":row["target_release"]}}})
            await self.rows.update_one({"_id":key,"project_id":project},{"$set":{"impact_state":"completed"}})
        except Exception:
            raise HTTPException(503,"Activation is recorded but impact cleanup is incomplete. Review and explicitly retry activation of this same context to reconcile.") from None
        return {**await self.view(row),"impact":impact}

    async def resolve(self,project,story,identity):
        row=await self.row(project,story,identity)
        story_data,base,analysis=await self.fresh(row)
        if not await self.approval(row):raise HTTPException(409,"Approve the selected requirements context before generation.")
        head=await self.head(project,story,row["target_release"])
        if head not in (row["parent_context_id"],identity):raise HTTPException(409,"Selected release context was superseded. Review its successor.")
        if row["basis"]=="story_only_provisional":
            knowledge={"version_id":None,"claims":[],"content_digest":digest([])}
        else:
            eligible,_=await self.knowledge.analysis_knowledge(project,story,base) if base else ({"claims":[]},[])
            claims={c["claim_id"]:dict(c) for c in eligible["claims"]}
            for decision in row["effective_decisions"]:
                if decision["decision"]!="intentional_change":raise HTTPException(409,"Unresolved requirement decisions block generation.")
                if decision.get("rule_id"):claims.pop(decision["rule_id"],None)
                # A removal still supplies a positive explicit absence assertion.
                key=decision["requirement_id"]
                claims[key]={"claim_id":key,"category":"business_rule","statement":decision["expected_result"],
                    "epistemic_status":"expected","source_id":decision["approved_context_origin"],"segment_index":None,"quote":decision["expected_result"],
                    "requirement_basis":"human_approved_change"}
            knowledge={"version_id":row["base_knowledge_version_id"],"claims":list(claims.values()),"content_digest":digest(list(claims.values()))}
        effective_story=dict(story_data)
        if row["basis"]=="approved_change":
            expectations="\n".join(d["expected_result"] for d in row["effective_decisions"])
            effective_story["acceptance_criteria"]="Approved release expectations:\n"+expectations
        elif not (story_data.get("acceptance_criteria") or "").strip():
            effective_story["acceptance_criteria"]=story_data["description"]
        return {"knowledge":knowledge,"analysis":self.knowledge.public(analysis),"requirements_story":effective_story,
            "criteria_basis":"approved_release_expectations" if row["basis"]=="approved_change" else "provisional_story_requirements",
            "requirements_policy":"Original story text can describe superseded behavior. Generate against the effective approved release expectations, not conflicting original criteria. Follow explicit human-approved changes for this release. Do not validate a story using its own extracted proposals. Provisional story-only designs are not validated against product knowledge and require human review.",
            "requirements_context_id":identity,
            "requirements_context_digest":row["content_digest"],"design_basis":row["basis"],"target_release":row["target_release"],
            "approved_requirement_changes":row["effective_decisions"],"independent_knowledge_validation":False}
