const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export async function checkHealth() {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/health`, {
      method: "GET",
      headers: {
        Accept: "application/json"
      }
    });
  } catch (error) {
    throw new Error("无法连接后端健康检查接口，请确认后端服务已启动。");
  }

  if (!response.ok) {
    throw new Error(`Health check failed with HTTP ${response.status}`);
  }

  return response.json();
}

export async function sendChatMessage(message) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ message })
    });
  } catch (error) {
    throw new Error("无法连接后端聊天接口，请确认后端服务已启动。");
  }

  const result = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = result?.detail;
    const messageText =
      detail?.message || result?.message || `Chat request failed with HTTP ${response.status}`;
    throw new Error(messageText);
  }

  return result;
}
