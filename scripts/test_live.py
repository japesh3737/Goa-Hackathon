import urllib.request
import json

base_url = 'https://goa-hackathon-jotw.onrender.com'

print('1. Testing /health...')
req = urllib.request.Request(f'{base_url}/health')
with urllib.request.urlopen(req) as resp:
    print('Health Status Code:', resp.status)
    health = json.loads(resp.read().decode('utf-8'))
    print('Health Details:', json.dumps(health, indent=2))

print('\n2. Testing /api/ask with live query...')
payload = json.dumps({'question': 'What are the famous dishes in Goan cuisine?', 'top_k': 3}).encode('utf-8')
ask_req = urllib.request.Request(f'{base_url}/api/ask', data=payload, headers={'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(ask_req) as resp:
    print('Ask Status Code:', resp.status)
    data = json.loads(resp.read().decode('utf-8'))
    print('\nQuestion:', data.get('question'))
    print('\nAnswer:\n', data.get('answer'))
    print('\nMetadata:', json.dumps(data.get('metadata', {}), indent=2))
    print('\nSources count:', len(data.get('sources', [])))
    for s in data.get('sources', []):
        print(f"  - [{s.get('id')}] {s.get('title')} (Score: {s.get('score')})")
