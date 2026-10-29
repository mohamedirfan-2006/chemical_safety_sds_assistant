import os
import sys
from pathlib import Path

# Add project root to sys.path so backend imports resolve
workspace_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(workspace_dir))

from fastapi.testclient import TestClient
from backend.app.main import app

def run_rag_tests():
    client = TestClient(app)
    
    document_id = 1
    
    test_cases = [
        {
            "name": "Eye First Aid Measures",
            "question": "What first aid measures should be taken if acetone gets in the eyes?"
        },
        {
            "name": "Flammability",
            "question": "Is acetone highly flammable?"
        },
        {
            "name": "Storage Safety",
            "question": "How should acetone be stored safely?"
        },
        {
            "name": "PPE Requirements",
            "question": "What PPE is required when handling acetone?"
        },
        {
            "name": "Unrelated Question (Safety Grounding)",
            "question": "What is the capital of France?"
        }
    ]

    print("=" * 70)
    print("RUNNING CHEMSAFE AI RAG QUESTION ANSWERING INTEGRATION TESTS")
    print("=" * 70)

    for tc in test_cases:
        print(f"\n[Test Case] {tc['name']}")
        print(f"Question: '{tc['question']}'")
        
        payload = {
            "document_id": document_id,
            "question": tc["question"]
        }
        
        try:
            response = client.post("/api/v1/sds/ask", json=payload)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Found in SDS: {data.get('found_in_sds')}")
                print(f"Answer:\n{data.get('answer')}")
                print("Sources Cited:")
                sources = data.get("sources", [])
                if not sources:
                    print("  None")
                for src in sources:
                    print(f"  - Chunk {src.get('chunk_id')}: Section {src.get('section_number')} '{src.get('section_name')}' (Page {src.get('page_number')}) [Distance: {src.get('retrieval_distance'):.4f}]")
            else:
                print(f"Error Response: {response.text}")
                
        except Exception as e:
            print(f"Test failed with exception: {e}")
        print("-" * 70)

    # 6. Test Error: Document ID does not exist
    print("\n[Test Case] Invalid Document ID (Error Handling)")
    invalid_payload = {
        "document_id": 9999,
        "question": "Is acetone flammable?"
    }
    try:
        response = client.post("/api/v1/sds/ask", json=invalid_payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Test failed with exception: {e}")
    print("=" * 70)

if __name__ == "__main__":
    run_rag_tests()
