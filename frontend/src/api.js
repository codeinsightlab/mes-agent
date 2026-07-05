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

export async function sendAgentMessage(message, context = undefined) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/agent/query`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        message,
        ...(context ? { context } : {})
      })
    });
  } catch (error) {
    throw new Error("无法连接 Agent 执行接口，请确认后端服务已启动。");
  }

  const result = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = result?.detail;
    const messageText =
      detail?.message || result?.error_message || result?.message || `Agent request failed with HTTP ${response.status}`;
    throw new Error(messageText);
  }

  return result;
}

export async function submitFeedback({
  responseMessageKey,
  visitorId,
  feedbackType,
  reasonType = null,
  comment = null
}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/feedback`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        response_message_key: responseMessageKey,
        visitor_id: visitorId,
        feedback_type: feedbackType,
        reason_type: reasonType,
        comment
      })
    });
  } catch (error) {
    throw new Error("无法连接后端反馈接口，请确认后端服务已启动。");
  }

  const result = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = result?.detail;
    const messageText =
      detail?.message || result?.message || `Feedback request failed with HTTP ${response.status}`;
    throw new Error(messageText);
  }

  return result;
}

async function requestJson(path, options = {}, fallbackMessage = "请求失败。") {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {})
      },
      ...options
    });
  } catch (error) {
    throw new Error(fallbackMessage);
  }

  const result = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = result?.detail;
    const messageText =
      detail?.message || result?.message || `${fallbackMessage} HTTP ${response.status}`;
    throw new Error(messageText);
  }
  return result;
}

function queryString(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, value);
    }
  });
  const text = search.toString();
  return text ? `?${text}` : "";
}

export function listDislikedFeedbacks(params = {}) {
  return requestJson(
    `/admin/feedbacks/disliked${queryString(params)}`,
    { method: "GET" },
    "无法查询差评列表，请确认后端服务已启动。"
  );
}

export function getDislikedFeedbackDetail(feedbackKey) {
  return requestJson(
    `/admin/feedbacks/${encodeURIComponent(feedbackKey)}`,
    { method: "GET" },
    "无法查询差评详情，请确认后端服务已启动。"
  );
}

export function createIssue(feedbackKey, priority = 2) {
  return requestJson(
    "/admin/issues",
    {
      method: "POST",
      body: JSON.stringify({ feedback_key: feedbackKey, priority })
    },
    "无法创建问题，请确认后端服务已启动。"
  );
}

export function listIssues(params = {}) {
  return requestJson(
    `/admin/issues${queryString(params)}`,
    { method: "GET" },
    "无法查询问题列表，请确认后端服务已启动。"
  );
}

export function getIssue(issueKey) {
  return requestJson(
    `/admin/issues/${encodeURIComponent(issueKey)}`,
    { method: "GET" },
    "无法查询问题详情，请确认后端服务已启动。"
  );
}

export function updateIssue(issueKey, payload) {
  return requestJson(
    `/admin/issues/${encodeURIComponent(issueKey)}`,
    {
      method: "PUT",
      body: JSON.stringify(payload)
    },
    "无法保存问题处理结果，请确认后端服务已启动。"
  );
}
