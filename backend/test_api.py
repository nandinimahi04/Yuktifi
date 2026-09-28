import urllib.request
import json
import sys

with open("test_api_log.txt", "w") as f:
    req = urllib.request.Request(
        'http://localhost:8000/analyze-market', 
        data=json.dumps({
            'session_id': 'b9edff9c-5d0f-4889-8d76-8095b597405e', 
            'location_id': '17.6699734,75.9008118', 
            'category_id': 'retail_kirana'
        }).encode('utf-8'), 
        headers={'Content-Type': 'application/json'}
    )

    try:
        res = urllib.request.urlopen(req)
        f.write(f"STATUS: {res.status}\n")
        f.write(res.read().decode())
    except Exception as e:
        f.write(f"ERROR: {e}\n")
        if hasattr(e, 'read'): 
            f.write(e.read().decode())
