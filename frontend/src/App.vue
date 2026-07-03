<script setup>
import { onMounted, ref } from "vue";
import { checkHealth, sendChatMessage } from "./api";

const status = ref("未连接");
const loading = ref(false);
const errorMessage = ref("");
const healthResult = ref(null);
const chatMessage = ref("");
const chatLoading = ref(false);
const chatErrorMessage = ref("");
const chatResult = ref(null);

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

  try {
    chatResult.value = await sendChatMessage(message);
  } catch (error) {
    chatErrorMessage.value =
      error instanceof Error ? error.message : "未知聊天请求错误";
  } finally {
    chatLoading.value = false;
  }
}

onMounted(() => {
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
      </section>
    </section>
  </main>
</template>
