# app/ai/scenario_prompts.py

from typing import Dict, Any


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


def build_scenario_prompt_from_story(
    agent_name: str,
    story: Dict[str, Any],
    count: int,
    complexity: str = 'medium',
) -> str:
    """
    Build the LLM prompt when generating scenarios from a Story definition only.
    """

    title = story.get('title', '')
    description = story.get('description', '')
    project_id = story.get('project_id', '')
    story_id = story.get('story_id', '')

    complexity_text = _complexity_instructions(complexity)

    return f"""
    You are an AI Test Scenario Generator called "{agent_name}".

    Context:
    - Project ID: {project_id}
    - Story ID: {story_id}
    - Story Title: {title}
    - Story Description: {description}

    Goal:
    - Generate {count} test scenarios for this story.
    - {complexity_text}

    Output format:
    Return ONLY valid JSON. No markdown, no explanations.

    [
    {{
        "title": "Scenario title",
        "description": "Short scenario description",
        "steps": [
        {{
            "category": "Navigation | Data Input | UI | Assertion | API | Other",
            "action": "Concrete step in natural language",
            "expected": "Expected outcome/result for this step"
        }}
        ]
    }}
    ]
    """.strip()


def build_scenario_prompt_from_recording(
    agent_name: str,
    story: Dict[str, Any],
    recording: Dict[str, Any],
    count: int,
    complexity: str = 'medium',
) -> str:
    """
    Build the LLM prompt when generating scenarios from a Story + Recording.

    `recording` is expected to be a dict from Mongo with fields like:
      - recording_id
      - title
      - description
      - raw_events (list of low-level events)
      - high_level_steps (optional list of text steps)
    """

    story_title = story.get('title', '')
    story_description = story.get('description', '')
    project_id = story.get('project_id', '')
    story_id = story.get('story_id', '')

    rec_id = recording.get('recording_id', '')
    rec_title = recording.get('title', '')
    rec_description = recording.get('description', '')
    raw_events = recording.get('raw_events', [])
    high_level_steps = recording.get('high_level_steps', [])

    complexity_text = _complexity_instructions(complexity)

    return f"""
    You are an AI Test Scenario Generator called "{agent_name}".

    We have a user story AND a recorded user session. Use BOTH to produce high-quality test scenarios.

    Story context:
    - Project ID: {project_id}
    - Story ID: {story_id}
    - Story Title: {story_title}
    - Story Description: {story_description}

    Recording context:
    - Recording ID: {rec_id}
    - Recording Title: {rec_title}
    - Recording Description: {rec_description}

    High-level recorded steps (if present):
    {high_level_steps}

    Raw recorded events (browser-level):
    {raw_events}

    Goal:
    - Generate {count} test scenarios derived from this recording and story.
    - {complexity_text}
    - Use the recording to infer realistic user flows, validations, and edge cases.

    Output format:
    Return ONLY valid JSON. No markdown, no explanations.

    [
    {{
        "title": "Scenario title",
        "description": "Short scenario description based on the recording",
        "steps": [
        {{
            "category": "Navigation | Data Input | UI | Assertion | API | Other",
            "action": "Concrete step in natural language",
            "expected": "Expected outcome/result for this step"
        }}
        ]
    }}
    ]
    """.strip()
