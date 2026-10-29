import sys
from pathlib import Path

workspace_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(workspace_dir))

from fastapi.testclient import TestClient
from backend.app.main import app

def run_tests():
    client = TestClient(app)
    document_id = 1

    questions = [
        "What PPE is required?",
        "What should I do in case of an acetone fire?",
        "How should acetone be stored?",
        "What is the capital of France?"
    ]

    print("=" * 80)
    print("TESTING CONVERSATIONAL CHEMSAFE AI RESPONSES")
    print("=" * 80)

    for q in questions:
        print(f"\n>>> USER: {q}\n")
        resp = client.post("/api/v1/sds/ask", json={"document_id": document_id, "question": q})
        if resp.status_code == 200:
            data = resp.json()
            print(f"Found in SDS: {data.get('found_in_sds')}")
            print(f"ASSISTANT RESPONSE:\n{data.get('answer')}")
            print(f"Sources Count: {len(data.get('sources', []))}")
        else:
            print(f"ERROR: {resp.status_code} - {resp.text}")
        print("-" * 80)

if __name__ == "__main__":
    run_tests()
