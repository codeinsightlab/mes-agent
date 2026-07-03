const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/health`, {
    method: "GET",
    headers: {
      Accept: "application/json"
    }
  });

  if (!response.ok) {
    throw new Error(`Health check failed with HTTP ${response.status}`);
  }

  return response.json();
}

export async function sendChatMessage(message) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ message })
  });

  const result = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = result?.detail;
    const messageText =
      detail?.message || result?.message || `Chat request failed with HTTP ${response.status}`;
    throw new Error(messageText);
  }

  return result;
}
