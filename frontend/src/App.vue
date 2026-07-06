<script setup>
import { computed, onMounted, ref } from "vue";
import {
  checkHealth,
  createIssue,
  getDislikedFeedbackDetail,
  listDislikedFeedbacks,
  sendAgentMessage,
  submitFeedback,
  updateIssue
} from "./api";

const VISITOR_ID_STORAGE_KEY = "mes_agent_visitor_id";
const FEEDBACK_LIKE = 1;
const FEEDBACK_DISLIKE = 2;
const FEEDBACK_REASONS = [
  { value: 1, label: "答非所问" },
  { value: 2, label: "事实或数据错误" },
  { value: 3, label: "理解错误" },
  { value: 4, label: "遗漏关键信息" },
  { value: 5, label: "表达不清" },
  { value: 6, label: "响应过慢" },
  { value: 7, label: "其他" }
];
const ISSUE_STATUSES = [
  { value: 1, label: "待处理" },
  { value: 2, label: "分析中" },
  { value: 3, label: "已定位" },
  { value: 4, label: "已修复" },
  { value: 5, label: "忽略" },
  { value: 6, label: "关闭" }
];
const ISSUE_PRIORITIES = [
  { value: 1, label: "低" },
  { value: 2, label: "中" },
  { value: 3, label: "高" },
  { value: 4, label: "紧急" }
];
const ROOT_CAUSE_TYPES = [
  { value: 1, label: "Prompt 问题" },
  { value: 2, label: "模型能力问题" },
  { value: 3, label: "上下文问题" },
  { value: 4, label: "工具选择问题" },
  { value: 5, label: "工具数据问题" },
  { value: 6, label: "业务规则问题" },
  { value: 7, label: "前端展示问题" },
  { value: 8, label: "系统异常" },
  { value: 9, label: "用户输入不明确" },
  { value: 10, label: "其他" }
];

const activeView = ref("chat");
const status = ref("未连接");
const loading = ref(false);
const errorMessage = ref("");
const healthResult = ref(null);
const chatMessage = ref("");
const chatLoading = ref(false);
const chatErrorMessage = ref("");
const chatResult = ref(null);
const visitorId = ref("");
const currentFeedbackType = ref(null);
const selectedReasonType = ref(null);
const feedbackComment = ref("");
const feedbackSubmitting = ref(false);
const feedbackError = ref("");
const feedbackSaved = ref(null);
const dislikedItems = ref([]);
const dislikedPage = ref(1);
const dislikedTotal = ref(0);
const dislikedLoading = ref(false);
const dislikedError = ref("");
const filterReasonType = ref("");
const filterHasIssue = ref("");
const filterIssueStatus = ref("");
const selectedFeedback = ref(null);
const issueSaving = ref(false);
const issueError = ref("");
const issueForm = ref({
  process_status: 1,
  priority: 2,
  root_cause_type: "",
  root_cause: "",
  solution: "",
  processed_by: ""
});

const agentView = computed(() => normalizeAgentResult(chatResult.value));

function createVisitorId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }
  const randomPart = Array.from(window.crypto?.getRandomValues?.(new Uint32Array(4)) || [])
    .map((value) => value.toString(16).padStart(8, "0"))
    .join("");
  if (randomPart) {
    return randomPart;
  }
  return `${Math.random().toString(36).slice(2)}${Math.random().toString(36).slice(2)}`;
}

function getOrCreateVisitorId() {
  const existing = window.localStorage.getItem(VISITOR_ID_STORAGE_KEY);
  if (existing) {
    return existing;
  }
  const nextVisitorId = createVisitorId();
  window.localStorage.setItem(VISITOR_ID_STORAGE_KEY, nextVisitorId);
  return nextVisitorId;
}

function resetFeedbackState() {
  currentFeedbackType.value = null;
  selectedReasonType.value = null;
  feedbackComment.value = "";
  feedbackSubmitting.value = false;
  feedbackError.value = "";
  feedbackSaved.value = null;
}

async function testConnection() {
  loading.value = true;
  errorMessage.value = "";

  try {
    const result = await checkHealth();
    healthResult.value = result;
    status.value = result.status === "ok" ? "连接成功" : "返回异常";
  } catch (error) {
    healthResult.value = null;
    status.value = "连接失败";
    errorMessage.value =
      error instanceof Error ? error.message : "未知连接错误";
  } finally {
    loading.value = false;
  }
}

async function submitChat() {
  const message = chatMessage.value.trim();
  if (!message || chatLoading.value) {
    return;
  }

  chatLoading.value = true;
  chatErrorMessage.value = "";
  chatResult.value = null;
  resetFeedbackState();

  try {
    chatResult.value = await sendAgentMessage(message);
  } catch (error) {
    chatErrorMessage.value =
      error instanceof Error ? error.message : "未知 Agent 执行错误";
  } finally {
    chatLoading.value = false;
  }
}

function normalizeAgentResult(result) {
  if (!result) {
    return null;
  }
  if (result.trace_id && result.final_result) {
    return normalizeOrchestratorResult(result);
  }
  if (typeof result.content === "string") {
    return {
      route: "legacy_chat",
      title: "Legacy Chat Result",
      message: result.content,
      raw: result,
      debug: {
        route: "legacy_chat",
        capability_name: null,
        execution_time: result.duration_ms || null,
        sql: null,
        tool_name: null
      }
    };
  }

  const route = result.route || "error";
  const toolResult = result.tool_result || result.final_result || {};
  const sqlResult = result.sql_result || (route === "text_to_sql" ? toolResult : {});
  const generatedSql = result.generated_sql || sqlResult.generated_sql || toolResult.generated_sql;
  const validatedSql = result.validated_sql || sqlResult.validated_sql || toolResult.validated_sql;
  const rows = Array.isArray(sqlResult.rows)
    ? sqlResult.rows
    : Array.isArray(toolResult.rows)
      ? toolResult.rows
      : [];
  const columns = Array.isArray(sqlResult.columns)
    ? sqlResult.columns
    : Array.isArray(toolResult.columns)
      ? toolResult.columns
      : deriveColumns(rows);
  const message =
    result.final_message ||
    result.message ||
    toolResult.message ||
    result.error_message ||
    result.error ||
    toolResult.error?.message ||
    "";

  return {
    route,
    title: routeTitle(route),
    capabilityName: result.capability_name || null,
    toolResult,
    sql: generatedSql || validatedSql || "",
    generatedSql,
    validatedSql,
    rows,
    columns,
    executionStatus: result.execution_status || sqlResult.execution_status || sqlResult.status || toolResult.status || "",
    message,
    raw: result,
    debug: {
      route,
      capability_name: result.capability_name || null,
      execution_time:
        result.execution_time ||
        result.duration_ms ||
        sqlResult.duration_ms ||
        toolResult.duration_ms ||
        null,
      sql: generatedSql || validatedSql || null,
      tool_name: result.tool_name || result.capability_name || null
    }
  };
}

function normalizeOrchestratorResult(result) {
  const route = result.debug?.route || result.plan_trace?.initial_plan?.intent || "unknown";
  const finalData = result.final_result?.data || {};
  const lastResult = finalData.last_result || finalData;
  const sqlPayload = findSqlPayload(result) || lastResult;
  const rows = Array.isArray(sqlPayload.rows) ? sqlPayload.rows : [];
  const columns = Array.isArray(sqlPayload.columns) ? sqlPayload.columns : deriveColumns(rows);
  const generatedSql = sqlPayload.generated_sql || null;
  const validatedSql = sqlPayload.validated_sql || null;
  const firstToolStep = findToolStep(result);
  const message =
    result.final_result?.error?.message ||
    lastResult.final_message ||
    result.debug?.failure_analysis?.reason ||
    "";

  return {
    route,
    title: routeTitle(route),
    capabilityName: firstToolStep?.name || null,
    toolResult: firstToolStep?.observation?.data?.tool_result || finalData,
    sql: generatedSql || validatedSql || "",
    generatedSql,
    validatedSql,
    rows,
    columns,
    executionStatus: result.final_result?.status || "",
    message,
    raw: result,
    debug: {
      route,
      capability_name: firstToolStep?.name || null,
      execution_time: result.debug?.execution_summary?.execution_loops ?? null,
      sql: generatedSql || validatedSql || null,
      tool_name: firstToolStep?.name || null
    }
  };
}

function findSqlPayload(result) {
  const traces = result.execution_trace || [];
  for (let traceIndex = traces.length - 1; traceIndex >= 0; traceIndex -= 1) {
    const stepResults = traces[traceIndex]?.result?.data?.step_results || [];
    for (let index = stepResults.length - 1; index >= 0; index -= 1) {
      const data = stepResults[index]?.observation?.data;
      if (data?.generated_sql || data?.validated_sql || Array.isArray(data?.rows)) {
        return data;
      }
    }
  }
  return null;
}

function findToolStep(result) {
  const traces = result.execution_trace || [];
  for (const trace of traces) {
    const stepResults = trace?.result?.data?.step_results || [];
    const found = stepResults.find((step) => step.type === "tool");
    if (found) {
      return found;
    }
  }
  return null;
}

function deriveColumns(rows) {
  if (!rows.length || typeof rows[0] !== "object" || rows[0] === null) {
    return [];
  }
  return Object.keys(rows[0]);
}

function routeTitle(route) {
  const titles = {
    tool: "Tool Result",
    sql: "SQL Execution Result",
    text_to_sql: "SQL Execution Result",
    mixed: "Mixed Execution Result",
    clarification: "Clarification",
    error: "Execution Error",
    legacy_chat: "Legacy Chat Result"
  };
  return titles[route] || "Execution Result";
}

function formatCell(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

async function sendFeedback(feedbackType) {
  if (!chatResult.value?.response_message_key || feedbackSubmitting.value) {
    return;
  }

  feedbackError.value = "";
  feedbackSubmitting.value = true;

  try {
    const result = await submitFeedback({
      responseMessageKey: chatResult.value.response_message_key,
      visitorId: visitorId.value,
      feedbackType,
      reasonType: feedbackType === FEEDBACK_DISLIKE ? selectedReasonType.value : null,
      comment: feedbackType === FEEDBACK_DISLIKE ? feedbackComment.value : null
    });
    feedbackSaved.value = result;
    currentFeedbackType.value = result.feedback_type;
    selectedReasonType.value = result.reason_type;
    feedbackComment.value = result.comment || "";
  } catch (error) {
    feedbackError.value =
      error instanceof Error ? error.message : "未知反馈提交错误";
  } finally {
    feedbackSubmitting.value = false;
  }
}

function chooseDislike() {
  currentFeedbackType.value = FEEDBACK_DISLIKE;
  feedbackError.value = "";
  feedbackSaved.value = null;
}

async function showIssueManager() {
  activeView.value = "issues";
  if (!dislikedItems.value.length) {
    await loadDislikedFeedbacks(1);
  }
}

async function loadDislikedFeedbacks(page = 1) {
  dislikedLoading.value = true;
  dislikedError.value = "";
  dislikedPage.value = page;
  try {
    const result = await listDislikedFeedbacks({
      page,
      page_size: 10,
      reason_type: filterReasonType.value || undefined,
      has_issue: filterHasIssue.value || undefined,
      issue_status: filterIssueStatus.value || undefined
    });
    dislikedItems.value = result.items;
    dislikedTotal.value = result.total;
  } catch (error) {
    dislikedError.value =
      error instanceof Error ? error.message : "未知差评查询错误";
  } finally {
    dislikedLoading.value = false;
  }
}

async function openFeedbackDetail(feedbackKey) {
  dislikedLoading.value = true;
  dislikedError.value = "";
  issueError.value = "";
  try {
    selectedFeedback.value = await getDislikedFeedbackDetail(feedbackKey);
    syncIssueForm(selectedFeedback.value.issue);
  } catch (error) {
    dislikedError.value =
      error instanceof Error ? error.message : "未知差评详情错误";
  } finally {
    dislikedLoading.value = false;
  }
}

function syncIssueForm(issue) {
  issueForm.value = {
    process_status: issue?.process_status || 1,
    priority: issue?.priority || 2,
    root_cause_type: issue?.root_cause_type || "",
    root_cause: issue?.root_cause || "",
    solution: issue?.solution || "",
    processed_by: issue?.processed_by || ""
  };
}

async function createIssueForSelected() {
  if (!selectedFeedback.value || issueSaving.value) {
    return;
  }
  issueSaving.value = true;
  issueError.value = "";
  try {
    const issue = await createIssue(selectedFeedback.value.feedback_key, issueForm.value.priority);
    selectedFeedback.value.issue = issue;
    selectedFeedback.value.has_issue = true;
    syncIssueForm(issue);
    await loadDislikedFeedbacks(dislikedPage.value);
  } catch (error) {
    issueError.value = error instanceof Error ? error.message : "未知问题创建错误";
  } finally {
    issueSaving.value = false;
  }
}

async function saveIssue() {
  if (!selectedFeedback.value?.issue?.issue_key || issueSaving.value) {
    return;
  }
  issueSaving.value = true;
  issueError.value = "";
  try {
    const payload = {
      process_status: Number(issueForm.value.process_status),
      priority: Number(issueForm.value.priority),
      root_cause_type: issueForm.value.root_cause_type ? Number(issueForm.value.root_cause_type) : null,
      root_cause: issueForm.value.root_cause,
      solution: issueForm.value.solution,
      processed_by: issueForm.value.processed_by
    };
    const issue = await updateIssue(selectedFeedback.value.issue.issue_key, payload);
    selectedFeedback.value.issue = issue;
    syncIssueForm(issue);
    await loadDislikedFeedbacks(dislikedPage.value);
  } catch (error) {
    issueError.value = error instanceof Error ? error.message : "未知问题保存错误";
  } finally {
    issueSaving.value = false;
  }
}

onMounted(() => {
  visitorId.value = getOrCreateVisitorId();
  testConnection();
});
</script>

<template>
  <main class="page-shell">
    <section class="panel">
      <div class="header">
        <div>
          <p class="eyebrow">Research Workspace</p>
          <h1>MES Agent</h1>
        </div>
        <button type="button" :disabled="loading" @click="testConnection">
          {{ loading ? "连接中..." : "测试连接" }}
        </button>
      </div>

      <div class="view-tabs">
        <button
          type="button"
          class="secondary-button"
          :class="{ selected: activeView === 'chat' }"
          @click="activeView = 'chat'"
        >
          聊天
        </button>
        <button
          type="button"
          class="secondary-button"
          :class="{ selected: activeView === 'issues' }"
          @click="showIssueManager"
        >
          差评管理
        </button>
      </div>

      <div v-if="activeView === 'chat'" class="status-row">
        <span class="label">后端连接状态</span>
        <strong :class="{ success: status === '连接成功', failure: status === '连接失败' }">
          {{ status }}
        </strong>
      </div>

      <template v-if="activeView === 'chat'">
      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

      <pre class="result-box">{{ healthResult ? JSON.stringify(healthResult, null, 2) : "暂无后端返回结果" }}</pre>

      <form class="chat-form" @submit.prevent="submitChat">
        <label for="chat-message">Agent 输入</label>
        <textarea
          id="chat-message"
          v-model="chatMessage"
          maxlength="4000"
          rows="5"
          placeholder="输入问题，发送到 Agent 执行接口"
        />
        <button type="submit" :disabled="chatLoading || !chatMessage.trim()">
          {{ chatLoading ? "执行中..." : "执行" }}
        </button>
      </form>

      <p v-if="chatErrorMessage" class="error-message">{{ chatErrorMessage }}</p>

      <section class="answer-box">
        <span class="label">Agent 执行结果</span>
        <p v-if="!agentView">暂无 Agent 执行结果</p>

        <section v-else class="agent-result">
          <div class="result-heading">
            <strong>{{ agentView.title }}</strong>
            <span>{{ agentView.route }}</span>
          </div>

          <p v-if="agentView.message" class="execution-message">{{ agentView.message }}</p>

          <section v-if="agentView.route === 'tool'" class="structured-section">
            <span class="label">Capability</span>
            <p class="inline-value">{{ agentView.capabilityName || "-" }}</p>
            <details open>
              <summary>Tool Result JSON</summary>
              <pre class="result-box">{{ JSON.stringify(agentView.toolResult, null, 2) }}</pre>
            </details>
          </section>

          <section v-else-if="agentView.route === 'text_to_sql' || agentView.route === 'sql'" class="structured-section">
            <div class="meta-row">
              <span>Execution Status: {{ agentView.executionStatus || "-" }}</span>
              <span>Rows: {{ agentView.rows.length }}</span>
            </div>

            <details v-if="agentView.generatedSql || agentView.validatedSql" open>
              <summary>SQL</summary>
              <pre class="sql-box">{{ agentView.validatedSql || agentView.generatedSql }}</pre>
            </details>

            <div v-if="agentView.rows.length && agentView.columns.length" class="table-scroll">
              <table class="result-table">
                <thead>
                  <tr>
                    <th v-for="column in agentView.columns" :key="column">{{ column }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, rowIndex) in agentView.rows" :key="rowIndex">
                    <td v-for="column in agentView.columns" :key="column">
                      {{ formatCell(row[column]) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-else class="empty-state">暂无 SQL 返回行数据</p>

            <details>
              <summary>Structured SQL Result JSON</summary>
              <pre class="result-box">{{ JSON.stringify(agentView.toolResult, null, 2) }}</pre>
            </details>
          </section>

          <section v-else-if="agentView.route === 'clarification'" class="structured-section">
            <p class="execution-message">{{ agentView.message || "Agent 需要补充信息。" }}</p>
          </section>

          <section v-else-if="agentView.route === 'legacy_chat'" class="structured-section">
            <p class="execution-message">{{ agentView.message }}</p>
          </section>

          <section v-else-if="agentView.route === 'mixed'" class="structured-section">
            <details open>
              <summary>Mixed Execution Result JSON</summary>
              <pre class="result-box">{{ JSON.stringify(agentView.toolResult, null, 2) }}</pre>
            </details>
          </section>

          <section v-else class="structured-section">
            <p class="error-message">{{ agentView.message || "Agent 执行失败。" }}</p>
          </section>

          <details class="debug-panel" open>
            <summary>Debug</summary>
            <dl>
              <div>
                <dt>route</dt>
                <dd>{{ agentView.debug.route || "-" }}</dd>
              </div>
              <div>
                <dt>capability_name</dt>
                <dd>{{ agentView.debug.capability_name || "-" }}</dd>
              </div>
              <div>
                <dt>execution_time</dt>
                <dd>{{ agentView.debug.execution_time ?? "-" }}</dd>
              </div>
              <div>
                <dt>tool_name</dt>
                <dd>{{ agentView.debug.tool_name || "-" }}</dd>
              </div>
            </dl>
            <pre v-if="agentView.debug.sql" class="sql-box">{{ agentView.debug.sql }}</pre>
          </details>

          <details>
            <summary>Raw Agent Result JSON</summary>
            <pre class="result-box">{{ JSON.stringify(agentView.raw, null, 2) }}</pre>
          </details>
        </section>

        <section v-if="chatResult?.response_message_key" class="feedback-panel">
          <div class="feedback-actions">
            <button
              type="button"
              class="secondary-button"
              :class="{ selected: currentFeedbackType === FEEDBACK_LIKE }"
              :disabled="feedbackSubmitting"
              @click="sendFeedback(FEEDBACK_LIKE)"
            >
              喜欢
            </button>
            <button
              type="button"
              class="secondary-button"
              :class="{ selected: currentFeedbackType === FEEDBACK_DISLIKE }"
              :disabled="feedbackSubmitting"
              @click="chooseDislike"
            >
              不喜欢
            </button>
          </div>

          <div v-if="currentFeedbackType === FEEDBACK_DISLIKE" class="dislike-form">
            <span class="label">点踩原因</span>
            <div class="reason-options">
              <label v-for="reason in FEEDBACK_REASONS" :key="reason.value" class="reason-option">
                <input
                  v-model="selectedReasonType"
                  type="radio"
                  name="feedback-reason"
                  :value="reason.value"
                  :disabled="feedbackSubmitting"
                />
                <span>{{ reason.label }}</span>
              </label>
            </div>
            <textarea
              v-model="feedbackComment"
              maxlength="1000"
              rows="3"
              placeholder="可选备注"
              :disabled="feedbackSubmitting"
            />
            <button
              type="button"
              :disabled="feedbackSubmitting || !selectedReasonType"
              @click="sendFeedback(FEEDBACK_DISLIKE)"
            >
              {{ feedbackSubmitting ? "提交中..." : "提交反馈" }}
            </button>
          </div>

          <p v-if="feedbackSaved" class="feedback-status">
            已保存：{{ feedbackSaved.feedback_type_label }}
            <span v-if="feedbackSaved.reason_type_label">，{{ feedbackSaved.reason_type_label }}</span>
          </p>
          <p v-if="feedbackError" class="error-message">{{ feedbackError }}</p>
        </section>
      </section>
      </template>

      <section v-else class="admin-panel">
        <div class="filter-row">
          <select v-model="filterReasonType">
            <option value="">全部原因</option>
            <option v-for="reason in FEEDBACK_REASONS" :key="reason.value" :value="reason.value">
              {{ reason.label }}
            </option>
          </select>
          <select v-model="filterHasIssue">
            <option value="">全部状态</option>
            <option value="true">已转问题</option>
            <option value="false">未转问题</option>
          </select>
          <select v-model="filterIssueStatus">
            <option value="">全部问题状态</option>
            <option v-for="item in ISSUE_STATUSES" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
          <button type="button" :disabled="dislikedLoading" @click="loadDislikedFeedbacks(1)">
            {{ dislikedLoading ? "查询中..." : "查询" }}
          </button>
        </div>

        <p v-if="dislikedError" class="error-message">{{ dislikedError }}</p>

        <div class="feedback-list">
          <article v-for="item in dislikedItems" :key="item.feedback_key" class="feedback-item">
            <div>
              <strong>{{ item.reason_type_label || "未选择原因" }}</strong>
              <span class="muted">{{ new Date(item.created_at).toLocaleString() }}</span>
            </div>
            <p>{{ item.user_message_content_summary || "暂无用户问题摘要" }}</p>
            <p>{{ item.assistant_content_summary || "暂无助手回答摘要" }}</p>
            <div class="meta-row">
              <span>{{ item.model || "-" }}</span>
              <span>Prompt {{ item.prompt_version || "-" }}</span>
              <span>{{ item.has_issue ? item.issue_status_label : "未转问题" }}</span>
            </div>
            <button type="button" class="secondary-button" @click="openFeedbackDetail(item.feedback_key)">
              查看详情
            </button>
          </article>
        </div>

        <div class="pagination-row">
          <button type="button" class="secondary-button" :disabled="dislikedPage <= 1" @click="loadDislikedFeedbacks(dislikedPage - 1)">
            上一页
          </button>
          <span>第 {{ dislikedPage }} 页 / 共 {{ dislikedTotal }} 条</span>
          <button type="button" class="secondary-button" :disabled="dislikedPage * 10 >= dislikedTotal" @click="loadDislikedFeedbacks(dislikedPage + 1)">
            下一页
          </button>
        </div>

        <section v-if="selectedFeedback" class="detail-panel">
          <h2>反馈现场</h2>
          <div class="scene-grid">
            <section>
              <span class="label">用户问题</span>
              <p class="text-box">{{ selectedFeedback.user_message?.content || "暂无" }}</p>
            </section>
            <section>
              <span class="label">助手回答</span>
              <p class="text-box">{{ selectedFeedback.assistant_message.content }}</p>
            </section>
          </div>

          <div class="meta-row">
            <span>原因：{{ selectedFeedback.reason_type_label || "未选择" }}</span>
            <span>模型：{{ selectedFeedback.model_call?.model || "-" }}</span>
            <span>Provider：{{ selectedFeedback.model_call?.provider || "-" }}</span>
            <span>耗时：{{ selectedFeedback.model_call?.duration_ms || "-" }}ms</span>
          </div>
          <p class="text-box">{{ selectedFeedback.comment || "暂无用户备注" }}</p>

          <details>
            <summary>模型调用现场</summary>
            <pre class="result-box">{{ JSON.stringify(selectedFeedback.model_call, null, 2) }}</pre>
          </details>

          <section class="issue-form">
            <h2>问题处理</h2>
            <button
              v-if="!selectedFeedback.has_issue"
              type="button"
              :disabled="issueSaving"
              @click="createIssueForSelected"
            >
              {{ issueSaving ? "创建中..." : "转为问题" }}
            </button>

            <template v-else>
              <div class="form-grid">
                <label>
                  状态
                  <select v-model="issueForm.process_status">
                    <option v-for="item in ISSUE_STATUSES" :key="item.value" :value="item.value">
                      {{ item.label }}
                    </option>
                  </select>
                </label>
                <label>
                  优先级
                  <select v-model="issueForm.priority">
                    <option v-for="item in ISSUE_PRIORITIES" :key="item.value" :value="item.value">
                      {{ item.label }}
                    </option>
                  </select>
                </label>
                <label>
                  根因类型
                  <select v-model="issueForm.root_cause_type">
                    <option value="">未选择</option>
                    <option v-for="item in ROOT_CAUSE_TYPES" :key="item.value" :value="item.value">
                      {{ item.label }}
                    </option>
                  </select>
                </label>
                <label>
                  处理人
                  <input v-model="issueForm.processed_by" maxlength="64" />
                </label>
              </div>
              <label>
                根因说明
                <textarea v-model="issueForm.root_cause" maxlength="4000" rows="4" />
              </label>
              <label>
                解决方案
                <textarea v-model="issueForm.solution" maxlength="4000" rows="4" />
              </label>
              <button type="button" :disabled="issueSaving" @click="saveIssue">
                {{ issueSaving ? "保存中..." : "保存处理结果" }}
              </button>
            </template>
            <p v-if="issueError" class="error-message">{{ issueError }}</p>
          </section>
        </section>
      </section>
    </section>
  </main>
</template>
