<script setup>
import { onMounted, ref } from "vue";
import { checkHealth } from "./api";

const status = ref("未连接");
const loading = ref(false);
const errorMessage = ref("");
const healthResult = ref(null);

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
    </section>
  </main>
</template>
