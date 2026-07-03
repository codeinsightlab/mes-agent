import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiBaseUrl = env.VITE_API_BASE_URL || "/api";

  return {
    plugins: [vue()],
    server: {
      proxy: {
        [apiBaseUrl]: {
          target: "http://127.0.0.1:8000",
          changeOrigin: true
        }
      }
    }
  };
});
