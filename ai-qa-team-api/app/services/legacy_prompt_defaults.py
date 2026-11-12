"""Preserved legacy templates; dynamic customer data never enters the registry."""

LEGACY_PROMPT_DEFAULTS = {'LEGACY_STORY_SCENARIOS': {'system_prompt': 'You are an AI Test Scenario Generator called '
                                             '"{{agent_name}}".\n'
                                             '\n'
                                             '    Context:\n'
                                             '    - Project ID: {{project_id}}\n'
                                             '    - Story ID: {{story_id}}\n'
                                             '    - Story Title: {{title}}\n'
                                             '    - Story Description: {{description}}\n'
                                             '\n'
                                             '    Goal:\n'
                                             '    - Generate {{count}} test scenarios for this story.\n'
                                             '    - {{complexity_text}}\n'
                                             '\n'
                                             '    Output format:\n'
                                             '    Return ONLY valid JSON. No markdown, no explanations.\n'
                                             '\n'
                                             '    [\n'
                                             '    {\n'
                                             '        "title": "Scenario title",\n'
                                             '        "description": "Short scenario description",\n'
                                             '        "steps": [\n'
                                             '        {\n'
                                             '            "category": "Navigation | Data Input | UI | '
                                             'Assertion | API | Other",\n'
                                             '            "action": "Concrete step in natural language",\n'
                                             '            "expected": "Expected outcome/result for this '
                                             'step"\n'
                                             '        }\n'
                                             '        ]\n'
                                             '    }\n'
                                             '    ]',
                            'template_variables': ['agent_name',
                                                   'project_id',
                                                   'story_id',
                                                   'title',
                                                   'description',
                                                   'count',
                                                   'complexity_text'],
                            'output_contract': 'LegacyScenarioSteps[]'},
 'LEGACY_RECORDING_SCENARIOS': {'system_prompt': 'You are an AI Test Scenario Generator called '
                                                 '"{{agent_name}}".\n'
                                                 '\n'
                                                 '    We have a user story AND a recorded user session. Use '
                                                 'BOTH to produce high-quality test scenarios.\n'
                                                 '\n'
                                                 '    Story context:\n'
                                                 '    - Project ID: {{project_id}}\n'
                                                 '    - Story ID: {{story_id}}\n'
                                                 '    - Story Title: {{story_title}}\n'
                                                 '    - Story Description: {{story_description}}\n'
                                                 '\n'
                                                 '    Recording context:\n'
                                                 '    - Recording ID: {{rec_id}}\n'
                                                 '    - Recording Title: {{rec_title}}\n'
                                                 '    - Recording Description: {{rec_description}}\n'
                                                 '\n'
                                                 '    High-level recorded steps (if present):\n'
                                                 '    {{high_level_steps}}\n'
                                                 '\n'
                                                 '    Raw recorded events (browser-level):\n'
                                                 '    {{raw_events}}\n'
                                                 '\n'
                                                 '    Goal:\n'
                                                 '    - Generate {{count}} test scenarios derived from this '
                                                 'recording and story.\n'
                                                 '    - {{complexity_text}}\n'
                                                 '    - Use the recording to infer realistic user flows, '
                                                 'validations, and edge cases.\n'
                                                 '\n'
                                                 '    Output format:\n'
                                                 '    Return ONLY valid JSON. No markdown, no explanations.\n'
                                                 '\n'
                                                 '    [\n'
                                                 '    {\n'
                                                 '        "title": "Scenario title",\n'
                                                 '        "description": "Short scenario description based '
                                                 'on the recording",\n'
                                                 '        "steps": [\n'
                                                 '        {\n'
                                                 '            "category": "Navigation | Data Input | UI | '
                                                 'Assertion | API | Other",\n'
                                                 '            "action": "Concrete step in natural '
                                                 'language",\n'
                                                 '            "expected": "Expected outcome/result for this '
                                                 'step"\n'
                                                 '        }\n'
                                                 '        ]\n'
                                                 '    }\n'
                                                 '    ]',
                                'template_variables': ['agent_name',
                                                       'project_id',
                                                       'story_id',
                                                       'story_title',
                                                       'story_description',
                                                       'rec_id',
                                                       'rec_title',
                                                       'rec_description',
                                                       'high_level_steps',
                                                       'raw_events',
                                                       'count',
                                                       'complexity_text'],
                                'output_contract': 'LegacyScenarioSteps[]'},
 'LEGACY_TESTCASE': {'system_prompt': 'You are an automation test generator. Convert the scenario into a '
                                      'structured test case.\n'
                                      '\n'
                                      'STRICT RULES:\n'
                                      '- OUTPUT JSON ONLY.\n'
                                      '- DO NOT write code.\n'
                                      '- Steps must be executable by a Playwright StepEngine:\n'
                                      '  * action must be one of: navigate | click | type | fill | '
                                      'assert_text | wait | noop\n'
                                      '  * locator must be a valid CSS/XPath selector OR null for '
                                      'navigation/assert_text\n'
                                      '  * value may be static text OR a dataset variable like {username}\n'
                                      '- Each step must include:\n'
                                      '  step_id, description, action, locator, value\n'
                                      '\n'
                                      'Here is the scenario:\n'
                                      '\n'
                                      '{{scenario_json}}\n'
                                      '\n'
                                      'Return JSON in this format:\n'
                                      '\n'
                                      '{\n'
                                      '  "title": "<string>",\n'
                                      '  "description": "<string>",\n'
                                      '  "steps": [\n'
                                      '    {\n'
                                      '      "step_id": "STEP001",\n'
                                      '      "description": "<Natural Language>",\n'
                                      '      "action": "<action>",\n'
                                      '      "locator": "<selector or null>",\n'
                                      '      "value": "<value or null>"\n'
                                      '    }\n'
                                      '  ]\n'
                                      '}',
                     'template_variables': ['scenario_json'],
                     'output_contract': 'LegacyTestcaseSteps'}}
