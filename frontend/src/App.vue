<script setup>
import { onMounted, ref } from "vue";
import { checkHealth, sendChatMessage, submitFeedback } from "./api";

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
    chatResult.value = await sendChatMessage(message);
  } catch (error) {
    chatErrorMessage.value =
      error instanceof Error ? error.message : "未知聊天请求错误";
  } finally {
    chatLoading.value = false;
  }
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

      <div class="status-row">
        <span class="label">后端连接状态</span>
        <strong :class="{ success: status === '连接成功', failure: status === '连接失败' }">
          {{ status }}
        </strong>
      </div>

      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

      <pre class="result-box">{{ healthResult ? JSON.stringify(healthResult, null, 2) : "暂无后端返回结果" }}</pre>

      <form class="chat-form" @submit.prevent="submitChat">
        <label for="chat-message">聊天输入</label>
        <textarea
          id="chat-message"
          v-model="chatMessage"
          maxlength="4000"
          rows="5"
          placeholder="输入一段文本，发送到后端模型接入层"
        />
        <button type="submit" :disabled="chatLoading || !chatMessage.trim()">
          {{ chatLoading ? "发送中..." : "发送" }}
        </button>
      </form>

      <p v-if="chatErrorMessage" class="error-message">{{ chatErrorMessage }}</p>

      <section class="answer-box">
        <span class="label">模型回答</span>
        <p>{{ chatResult?.content || "暂无模型回答" }}</p>
        <pre v-if="chatResult" class="result-box">{{ JSON.stringify(chatResult, null, 2) }}</pre>

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
    </section>
  </main>
</template>
