"""Resolve explicit resource references before account-scoped API work.

Project services still apply their role/action checks. This adds a shared tenant
boundary to legacy endpoints that previously relied only on creator email.
"""
from fastapi import HTTPException


async def authorize_references(request, user, database):
    from app.utils.project_authorization import require_project_member

    references = {**dict(request.query_params), **request.path_params}
    if request.method in ("POST", "PUT", "PATCH") and "application/json" in request.headers.get("content-type", ""):
        try:
            body = await request.json()
        except ValueError:
            body = None  # Normal route validation handles malformed JSON.
        if isinstance(body, dict):
            # Do not traverse training text, model output or arbitrary customer data.
            for key in ("project_id", "story_id", "scenario_id", "testcase_id", "testcase_ids", "environment_id", "env_id", "recording_id", "repository_id"):
                if key in body:
                    if key in references and references[key] != body[key]:
                        raise HTTPException(422, "Conflicting resource references.")
                    references[key] = body[key]
    projects = set()
    if references.get("project_id"):
        projects.add(str(references["project_id"]))
    resources = {"story_id": "stories", "scenario_id": "scenarios", "testcase_id": "testcases",
                 "recording_id": "recordings", "env_id": "environments", "repository_id": "repositories",
                 "execution_id": "executions", "membership_id": "project_memberships"}
    if references.get("environment_id"):
        references["env_id"] = references["environment_id"]
    for key, collection in resources.items():
        values = references.get("testcase_ids", []) if key == "testcase_id" else []
        if not isinstance(values, list):
            raise HTTPException(422, "Invalid resource references.")
        values = [*values, *([references[key]] if references.get(key) else [])]
        for value in values:
            if not isinstance(value, str):
                raise HTTPException(422, "Invalid resource references.")
            document = await database[collection].find_one({key: value})
            if document and document.get("project_id"):
                projects.add(document["project_id"])
    for project_id in projects:
        # Narrow account-administration capability, not project-content access.
        import re
        if re.fullmatch(r"/projects/[^/]+/team(?:/[^/]+)?", request.url.path) and user.get("account_role") in ("OWNER", "ADMIN"):
            from app.services.customer_accounts import CustomerAccounts
            service = CustomerAccounts(database)
            await service.admin(user)
            await service.project(await database["projects"].find_one({"project_id": project_id}), user)
        else:
            await require_project_member(project_id, user)
