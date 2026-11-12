"""Single-pass substitution, never eval/format or a general template engine."""
import re
from fastapi import HTTPException

SLOT = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}")


def validate_template(template, allowed):
    if set(SLOT.findall(template)) != set(allowed):
        raise HTTPException(422, "Preserve exactly the documented template placeholders.")


def render_template(template, values):
    validate_template(template, values)
    # Substituted user content is never scanned again for placeholders.
    return SLOT.sub(lambda match: str(values[match[1]]), template).strip()
