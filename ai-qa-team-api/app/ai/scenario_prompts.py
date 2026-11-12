"""Legacy scenario contracts with allowlisted, non-executable template slots."""
from app.services.legacy_prompt_defaults import LEGACY_PROMPT_DEFAULTS
from app.services.prompt_templates import render_template

def _complexity_instructions(complexity: str) -> str:
    complexity = (complexity or 'medium').lower()

    if complexity == 'basic':
        return (
            'Generate simple, high-level scenarios with 3–5 steps each. '
            'Focus on happy path only, minimal validations, no edge cases.'
        )
    if complexity == 'advanced':
        return (
            'Generate detailed scenarios including happy paths, edge cases, and negative flows. '
            'Each scenario should have 8–12 steps with strong validations and assertions.'
        )
    # default: medium
    return (
        'Generate realistic scenarios with both happy path and a few edge/negative cases. '
        'Each scenario should have around 5–8 steps with clear validations.'
    )



def build_scenario_prompt_from_story(agent_name, story, count, complexity='medium', *, template=None):
    return render_template(template or LEGACY_PROMPT_DEFAULTS['LEGACY_STORY_SCENARIOS']['system_prompt'], {
        'agent_name': agent_name, 'project_id': story.get('project_id', ''), 'story_id': story.get('story_id', ''),
        'title': story.get('title', ''), 'description': story.get('description', ''),
        'count': count, 'complexity_text': _complexity_instructions(complexity),
    })


def build_scenario_prompt_from_recording(agent_name, story, recording, count, complexity='medium', *, template=None):
    return render_template(template or LEGACY_PROMPT_DEFAULTS['LEGACY_RECORDING_SCENARIOS']['system_prompt'], {
        'agent_name': agent_name, 'project_id': story.get('project_id', ''), 'story_id': story.get('story_id', ''),
        'story_title': story.get('title', ''), 'story_description': story.get('description', ''),
        'rec_id': recording.get('recording_id', ''), 'rec_title': recording.get('title', ''),
        'rec_description': recording.get('description', ''), 'raw_events': recording.get('raw_events', []),
        'high_level_steps': recording.get('high_level_steps', []),
        'count': count, 'complexity_text': _complexity_instructions(complexity),
    })
