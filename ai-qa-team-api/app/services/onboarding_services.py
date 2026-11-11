from typing import Literal
from bson import ObjectId
from app.db.connection import db

OnboardingStatus = Literal['not_started', 'in_progress', 'completed']

async def get_onboarding_status(user_id: str) -> dict:
    user = await db['users'].find_one({'_id': ObjectId(user_id)})
    if not user:
        return {'status': 'not_started', 'step': 1}

    status = user.get('onboarding_status', 'not_started')
    step = user.get('onboarding_step', 1)

    # If they already have a project, auto-promote to completed
    projects_count = await db['projects'].count_documents({'created_by': user['_id']})
    if projects_count > 0 and status != 'completed':
        status = 'completed'
        step = 6  # last step

        await db['users'].update_one(
            {'_id': user['_id']},
            {'$set': {'onboarding_status': status, 'onboarding_step': step}}
        )

    return {'status': status, 'step': step}


async def update_onboarding_step(user_id: str, step: int, status: OnboardingStatus):
    await db['users'].update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {
            'onboarding_status': status,
            'onboarding_step': step
        }}
    )
