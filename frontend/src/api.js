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
