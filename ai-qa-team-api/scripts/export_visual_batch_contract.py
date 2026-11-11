"""Export canonical wire schema without importing API settings or infrastructure."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ai-qa-team-api'))
from app.models.visual_batch_model import BatchManifest, BatchRun, BatchStart


def exported_schema():
    schema = BatchManifest.model_json_schema()
    # Manifests are serialized with defaults expanded; require explicit wire fields.
    for node in [schema, *schema.get('$defs', {}).values()]:
        if node.get('type') == 'object':
            node['required'] = list(node['properties'])
    return json.dumps(schema, indent=2) + '\n'


def typescript_type(node):
    if '$ref' in node:
        return node['$ref'].rsplit('/', 1)[1]
    if 'const' in node:
        return json.dumps(node['const'])
    if 'enum' in node:
        return ' | '.join(json.dumps(value) for value in node['enum'])
    if 'anyOf' in node:
        return ' | '.join(typescript_type(value) for value in node['anyOf'])
    kind = node.get('type')
    if kind == 'object':
        if isinstance(node.get('additionalProperties'), dict):
            return 'Record<string, ' + typescript_type(node['additionalProperties']) + '>'
        fields = [f'  {json.dumps(name)}{"" if name in node.get("required", []) else "?"}: {typescript_type(value)};'
                  for name, value in node.get('properties', {}).items()]
        return '{\n' + '\n'.join(fields) + '\n}'
    if kind == 'array':
        return '(' + typescript_type(node['items']) + ')[]'
    return {'string': 'string', 'integer': 'number', 'number': 'number', 'boolean': 'boolean', 'null': 'null'}[kind]


def exported_typescript():
    schemas = {'VisualBatchStart': BatchStart.model_json_schema(), 'VisualBatchRun': BatchRun.model_json_schema()}
    definitions = {}
    for schema in schemas.values():
        definitions.update(schema.get('$defs', {}))
    output = '// Generated from visual_batch_model.py; run scripts/export_visual_batch_contract.py. Do not edit.\n'
    for name, schema in {**definitions, **schemas}.items():
        output += '\nexport type ' + name + ' = ' + typescript_type(schema) + ';\n'
    return output


if __name__ == '__main__':
    targets = {ROOT / 'visual-runner/linux/batch-manifest.schema.json': exported_schema(),
               ROOT / 'ai-qa-team-ui/src/types/visual-batch.generated.ts': exported_typescript()}
    for target, content in targets.items():
        if '--check' in sys.argv:
            if target.read_text(encoding='utf-8') != content:
                raise SystemExit('Batch contract export drift')
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8')
