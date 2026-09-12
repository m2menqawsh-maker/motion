import json
with open('schemas/blueprint.schema.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

d['$defs']['scene']['properties']['effects'] = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'effect': {'type': 'string'},
            'params': {'type': 'object'},
            'apply': {'type': 'string', 'enum': ['scene', 'overlay']}
        },
        'required': ['effect'],
        'additionalProperties': False
    }
}

with open('schemas/blueprint.schema.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
print('Updated blueprint.schema.json')
