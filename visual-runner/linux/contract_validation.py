"""Validate the generated canonical manifest schema with a fail-closed subset.

No API imports or extra runner dependencies. Unsupported schema keywords fail the
build/tests rather than silently broadening accepted input. Not a general validator.
"""
import json
from pathlib import Path
import re


def validate(value, schema, root):
    supported = {'$defs', '$ref', 'title', 'description', 'default', 'type', 'const', 'enum',
                 'properties', 'required', 'additionalProperties', 'items', 'minItems', 'maxItems',
                 'minimum', 'maximum', 'pattern'}
    if set(schema) - supported:
        raise ValueError('UNSUPPORTED_MANIFEST_SCHEMA')
    if '$ref' in schema:
        prefix = '#/$defs/'
        if not schema['$ref'].startswith(prefix):
            raise ValueError('INVALID_SCHEMA_REFERENCE')
        return validate(value, root['$defs'][schema['$ref'][len(prefix):]], root)
    if 'const' in schema and value != schema['const'] or 'enum' in schema and value not in schema['enum']:
        raise ValueError('INVALID_MANIFEST_LITERAL')
    kind = schema.get('type')
    if kind == 'object':
        if type(value) is not dict or set(schema.get('required', [])) - set(value):
            raise ValueError('INVALID_MANIFEST_OBJECT')
        props = schema.get('properties', {})
        if schema.get('additionalProperties') is False and set(value) - set(props):
            raise ValueError('UNKNOWN_MANIFEST_FIELDS')
        for key in value:
            validate(value[key], props[key], root)
    elif kind == 'array':
        if type(value) is not list or not schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', len(value)):
            raise ValueError('INVALID_MANIFEST_ARRAY')
        for item in value:
            validate(item, schema['items'], root)
    elif kind == 'integer':
        if type(value) is not int or not schema.get('minimum', value) <= value <= schema.get('maximum', value):
            raise ValueError('INVALID_MANIFEST_INTEGER')
    elif kind == 'string':
        if type(value) is not str or 'pattern' in schema and not re.search(schema['pattern'], value):
            raise ValueError('INVALID_MANIFEST_STRING')
    else:
        raise ValueError('UNSUPPORTED_MANIFEST_TYPE')


def validate_manifest(value):
    schema = json.loads((Path(__file__).parent / 'batch-manifest.schema.json').read_text(encoding='utf-8'))
    validate(value, schema, schema)
    if len({c['case_run_id'] for c in value['cases']}) != len(value['cases']) or value['batch_timeout_seconds'] != len(value['cases'])*110:
        raise ValueError('INVALID_BATCH_IDENTITIES_OR_BUDGET')
