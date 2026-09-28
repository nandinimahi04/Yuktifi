from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BACKEND=ROOT/'backend'
checks=[]

def check(name, path, required=False):
    ok=Path(path).exists()
    checks.append({"name":name,"path":str(Path(path).relative_to(ROOT)) if Path(path).exists() else str(path),"present":ok,"required":required})

check('SQLite database', BACKEND/'yukti.db')
check('Location master manifest', BACKEND/'data/reference/location_master_manifest.json', True)
check('Census raw directory', BACKEND/'data/raw/census')
check('Livestock raw directory', BACKEND/'data/raw/livestock')

manifest=BACKEND/'data/reference/location_master_manifest.json'
if manifest.exists():
    try:
        data=json.loads(manifest.read_text())
        master=data.get('master_path')
        checks.append({"name":"Location master file","path":master,"present":bool(master and (ROOT/master).exists()),"required":False})
    except Exception as e:
        checks.append({"name":"Location master manifest JSON","present":False,"required":True,"error":str(e)})

required_fail=[x for x in checks if x.get('required') and not x.get('present')]
print(json.dumps({"ready":not required_fail,"checks":checks},indent=2))
raise SystemExit(1 if required_fail else 0)
