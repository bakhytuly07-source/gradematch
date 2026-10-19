"""Focused contract regression check using backend's existing dev dependencies."""
import re
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
contract = yaml.safe_load((ROOT / 'openapi.yaml').read_text())
audit = (ROOT / '_docs/contract-audit.md').read_text()
interface = (ROOT / 'frontend/src/services/types.ts').read_text().split('export interface GradeMatchService {')[1]
methods = re.findall(r'^  (\w+)\(', interface, re.M)
# operationId: HTTP, route, request, success, response, errors, bearer
expected = {
 'register': ('post','/api/auth/register','RegisterInput','201','AuthResult',{'409','422','500'},False),
 'login': ('post','/api/auth/login','LoginInput','200','AuthResult',{'401','422','500'},False),
 'logout': ('post','/api/auth/logout',None,'204',None,{'401','500'},True),
 'getMe': ('get','/api/auth/me',None,'200','User',{'401','500'},True),
 'generateLook': ('post','/api/generate','GenerateInput','200','StyleParams',{'413','415','422','500'},False),
 'renderLut': ('post','/api/render-lut','LutSettings','200','LutData',{'422','500'},False),
 'saveLook': ('post','/api/looks','SaveLookInput','201','Look',{'401','422','500'},True),
 'listLooks': ('get','/api/looks',None,'200','Look[]',{'401','500'},True),
 'getLook': ('get','/api/looks/{id}',None,'200','Look',{'401','404','500'},True),
 'renameLook': ('patch','/api/looks/{id}','RenameLookInput','200','Look',{'401','404','422','500'},True),
 'toggleFavorite': ('post','/api/looks/{id}/favorite',None,'200','Look',{'401','404','500'},True),
 'deleteLook': ('delete','/api/looks/{id}',None,'204',None,{'401','404','500'},True),
 'downloadLutCube': ('post','/api/download.cube','LutSettings','200','text',{'422','500'},False),
}

def resolve(ref):
    assert ref.startswith('#/'), f'Non-local reference: {ref}'
    node = contract
    for part in ref[2:].split('/'):
        node = node[part.replace('~1', '/').replace('~0', '~')]
    return node

refs = []
def walk(node):
    if isinstance(node, dict):
        if '$ref' in node:
            refs.append(node['$ref'])
            resolve(node['$ref'])
        for value in node.values():
            walk(value)
    elif isinstance(node, list):
        for value in node:
            walk(value)
walk(contract)
assert contract['openapi'] == '3.1.0'
for schema in contract['components']['schemas'].values():
    Draft202012Validator.check_schema(schema)
operations = [(path, method, op) for path, item in contract['paths'].items()
              for method, op in item.items() if method in {'get','post','patch','put','delete','options','head','trace'}]
ids = [op['operationId'] for _, _, op in operations]
assert len(ids) == len(set(ids)) == len(methods) == 13
assert set(ids) == set(methods) == set(expected)
for path, method, op in operations:
    name = op['operationId']
    verb, route, request, success, response, errors, protected = expected[name]
    assert (method, path) == (verb, route), name
    assert op['security'] == ([{'bearerAuth': []}] if protected else []), name
    assert set(op['responses']) == errors | {success}, name
    row = next(line for line in audit.splitlines() if line.startswith(f'| {name} |'))
    cells = [cell.strip() for cell in row.split('|')[1:-1]]
    assert cells[1:3] == [verb.upper(), route], name
    assert cells[-1] == ('Bearer' if protected else 'Guest'), name
    assert cells[-2] == ', '.join(sorted(errors)), name
    assert cells[4].startswith(success + ' '), name
    if request is None:
        assert 'requestBody' not in op, name
    else:
        body = op['requestBody']
        assert body['required'] is True
        media = 'multipart/form-data' if name == 'generateLook' else 'application/json'
        assert body['content'][media]['schema']['$ref'] == f'#/components/schemas/{request}'
        assert request in cells[3]
    result = op['responses'][success]
    if response is None:
        assert 'content' not in result
    elif response == 'text':
        assert result['content']['text/plain']['schema']['type'] == 'string'
    else:
        schema = result['content']['application/json']['schema']
        if response == 'Look[]':
            assert schema['type'] == 'array'
            schema = schema['items']
            response = 'Look'
        assert schema['$ref'] == f'#/components/schemas/{response}'
    for status in errors:
        error = resolve(op['responses'][status]['$ref'])
        assert error['content']['application/json']['schema']['$ref'] == '#/components/schemas/Error'
    if '{id}' in path:
        assert any(p['name'] == 'id' and p['in'] == 'path' and p['required'] for p in contract['paths'][path]['parameters'])
schemas = contract['components']['schemas']
for name, schema in schemas.items():
    if schema.get('type') == 'object':
        assert set(schema['required']) == set(schema['properties']), name
lut = schemas['LutData']['properties']
assert lut['size']['const'] == 33
assert lut['data']['minItems'] == lut['data']['maxItems'] == 33**3 * 3
assert schemas['GenerateInput']['properties']['referenceFile']['x-maxBytes'] == 15_728_640
assert schemas['GenerateInput']['properties']['referenceFile']['format'] == 'binary'
assert schemas['AuthResult']['properties']['token_type']['const'] == 'bearer'
assert contract['components']['securitySchemes']['bearerAuth']['scheme'] == 'bearer'
print(f'PASS: 13 service/operation/audit mappings; {len(refs)} resolved refs; {len(schemas)} valid schemas; explicit security, bodies and responses')
