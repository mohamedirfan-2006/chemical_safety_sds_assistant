const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

export async function uploadSDS(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/sds/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to upload and index SDS PDF.');
  }

  return response.json();
}

export async function listDocuments() {
  const response = await fetch(`${API_BASE_URL}/sds/documents`);

  if (!response.ok) {
    throw new Error('Failed to retrieve indexed documents list.');
  }

  return response.json();
}

export async function searchSDS(documentId, query) {
  const response = await fetch(`${API_BASE_URL}/sds/search?query=${encodeURIComponent(query)}&k=100`);

  if (!response.ok) {
    throw new Error('Failed to perform semantic search.');
  }

  const data = await response.json();
  
  // Client-side filter to only keep chunks matching the requested document ID
  const filteredResults = (data.results || []).filter(
    (chunk) => chunk.document_id === parseInt(documentId, 10)
  );

  return {
    query,
    results: filteredResults,
  };
}

export async function askSDS(documentId, question) {
  const response = await fetch(`${API_BASE_URL}/sds/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      document_id: parseInt(documentId, 10),
      question: question.trim(),
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to query the RAG pipeline.');
  }

  return response.json();
}

export async function checkBackendHealth() {
  try {
    const response = await fetch('http://127.0.0.1:8000/', { method: 'GET', timeout: 3000 });
    if (response.ok) {
      const data = await response.json();
      return { status: 'healthy', project: data.app || 'ChemSafe AI' };
    }
  } catch (e) {
    // Backend unreachable
  }
  return { status: 'offline' };
}
