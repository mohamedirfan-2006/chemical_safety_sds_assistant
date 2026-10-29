import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests
import json
import time

questions = [
    "What PPE should I wear?",
    "What should I do in case of an acetone fire?",
    "What should I do if it gets in my eyes?",
    "What is the capital of France?"
]

doc_id = 9

for q in questions:
    print(f"\n==========================================")
    print(f"QUESTION: {q}")
    print(f"==========================================")
    t0 = time.time()
    unicode_error = "None"
    try:
        res = requests.post(
            "http://127.0.0.1:8000/api/v1/sds/ask",
            json={"document_id": doc_id, "question": q},
            timeout=180
        )
        duration = time.time() - t0
        print(f"HTTP Status: {res.status_code} (took {duration:.2f}s)")
        
        if res.status_code == 200:
            try:
                data = res.json()
            except Exception as e:
                unicode_error = f"JSON decode error: {e}"
                data = {}

            print(f"found_in_sds: {data.get('found_in_sds')}")
            
            sources = data.get("sources", [])
            print(f"sources: {len(sources)} chunks")
            for s in sources:
                print(f"  - Section {s.get('section_number')} ({s.get('section_name')}), Page {s.get('page_number')}")
            
            answer = data.get("answer", "")
            try:
                answer.encode("utf-8")
            except Exception as e:
                unicode_error = f"Unicode error: {e}"
                
            print(f"Unicode Error: {unicode_error}")
            print(f"\nFINAL ANSWER:\n{answer}")
        else:
            if "charmap" in res.text or "UnicodeEncodeError" in res.text:
                unicode_error = "Unicode charmap error on backend!"
            print(f"Unicode Error: {unicode_error}")
            print(f"Error Response: {res.text}")
            
    except Exception as e:
        print(f"Exception: {e}")
        if isinstance(e, (UnicodeEncodeError, UnicodeDecodeError)):
            print(f"Unicode Error: {e}")
