"""Run from backend: uv run python evaluation/benchmark-api.py."""
import json
from io import BytesIO
from pathlib import Path
import platform
import sys
from time import perf_counter

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app

buffer=BytesIO()
Image.new('RGB',(4000,3000),(140,110,90)).save(buffer,format='JPEG',quality=95)
data=buffer.getvalue()
data+=b'\0'*(15728640-len(data))
runs=[]
with TestClient(app) as client:
    for _ in range(5):
        start=perf_counter()
        response=client.post('/api/generate',files={'referenceFile':('15MB.jpg',data,'image/jpeg')})
        assert response.status_code==200,response.text
        runs.append((perf_counter()-start)*1000)
result={'host':platform.platform(),'cpu':next(line.strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),
        'input_dimensions':[4000,3000],'bytes':len(data),'endpoint_ms':runs,
        'method':'TestClient ASGI multipart request to response; padded synthetic JPEG; cloud host, not laptop qualification'}
Path(__file__).with_name('api-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
