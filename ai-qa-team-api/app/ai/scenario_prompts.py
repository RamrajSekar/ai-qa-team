def build_scenario_prompt(agent_name: str, story: dict, count: int) -> str:
    """
    Centralized prompt file so UI can override later.
    """


    return f"""
        You are an AI Scenario Generator named {agent_name}.

        Generate EXACTLY {count} test scenarios for this story.
        DO NOT return more than {count}.
        DO NOT return less than {count}.

        Story:
        Title: {story.get("title")}
        Description: {story.get("description")}

        Each scenario must return JSON only in this exact format:

        [
        {{
            "title": "...",
            "description": "...",
            "steps": [
            {{ "category": "...", "action": "...", "expected": "..." }}
            ]
        }}
        ]

        IMPORTANT:
        - Return EXACTLY {count} items in the list.
        - NOTHING OUTSIDE JSON.
        """
