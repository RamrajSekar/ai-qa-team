from fastapi import APIRouter, Depends
# from app.services.subscription_services import increment_usage
from app.utils.auth_dependency import get_current_user
from app.utils.subscription_dependency import subscription_required

router = APIRouter(prefix="/execute", tags=["Execution"])

@router.post("/")
async def run_tests(
    test_data: dict,
    current_user=Depends(subscription_required("executions"))
):
    """
    Trigger a test execution.
    Enforces plan limits using subscription_required('executions').
    """
    user_id = current_user.get("_id") or current_user.get("id") or current_user.get("email")

    return {
        "message": "Test execution started successfully.",
        "user": user_id,
        "plan": current_user.get("plan", "free")
    }