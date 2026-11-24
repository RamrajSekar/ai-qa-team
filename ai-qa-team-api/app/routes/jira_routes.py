from fastapi import APIRouter, Depends, Response
from app.db.connection import db
from app.models.jira_import import JiraPreview, JiraApply, JiraRevision, JiraOAuthStart, JiraOAuthComplete, JiraOAuthGrant, JiraOAuthSelect
from app.services.jira_story_import import JiraStoryImport
from app.services.jira_oauth import JiraOAuth
from app.utils.auth_dependency import get_current_user
from app.utils.feature_flags import feature_required
from app.utils.safe_validation_route import SafeValidationRoute


async def private(response:Response):response.headers["Cache-Control"]="private, no-store"

router=APIRouter(prefix="/projects/{project_id}/jira",tags=["Jira story import"],route_class=SafeValidationRoute,
    dependencies=[Depends(feature_required("jira_story_import","story_management")),Depends(private)])


def service():return JiraStoryImport(db)


@router.get("/connection")
async def connection(project_id:str,user=Depends(get_current_user)):
    row,_=await service().connection(project_id,user)
    return JiraStoryImport.public(row)


@router.post("/disconnect")
async def disconnect(project_id:str,payload:JiraRevision,user=Depends(get_current_user)):
    return await service().disconnect(project_id,user,payload)


@router.post("/preview")
async def preview(project_id:str,payload:JiraPreview,user=Depends(get_current_user)):
    return await service().preview(project_id,user,payload)


@router.post("/apply")
async def apply(project_id:str,payload:JiraApply,user=Depends(get_current_user)):
    return await service().apply(project_id,user,payload)


def oauth():return JiraOAuth(db)


@router.post("/oauth/start")
async def oauth_start(project_id:str,payload:JiraOAuthStart,user=Depends(get_current_user)):
    return await oauth().start(project_id,user,payload)


@router.post("/oauth/complete")
async def oauth_complete(project_id:str,payload:JiraOAuthComplete,user=Depends(get_current_user)):
    return await oauth().complete(project_id,user,payload)


@router.post("/oauth/projects")
async def oauth_projects(project_id:str,payload:JiraOAuthGrant,user=Depends(get_current_user)):
    return await oauth().projects(project_id,user,payload)


@router.post("/oauth/select")
async def oauth_select(project_id:str,payload:JiraOAuthSelect,user=Depends(get_current_user)):
    return await oauth().select(project_id,user,payload)
