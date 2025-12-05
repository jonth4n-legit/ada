import { signal } from "@preact/signals";
import AccountManager from "./AccountManager.tsx";
import ModelManager from "./ModelManager.tsx";
import ConfigManager from "./ConfigManager.tsx";

type Tab = "accounts" | "models" | "config";

const activeTab = signal<Tab>("accounts");

export default function TabManager() {
  return (
    <div>
      {/* 标签页导航 */}
      <div class="border-b border-gray-200">
        <nav class="-mb-px flex space-x-8 px-4">
          <button
            onClick={() => (activeTab.value = "accounts")}
            class={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab.value === "accounts"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            账号管理
          </button>
          <button
            onClick={() => (activeTab.value = "models")}
            class={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab.value === "models"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            模型管理
          </button>
          <button
            onClick={() => (activeTab.value = "config")}
            class={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab.value === "config"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            系统配置
          </button>
          <a
            href="/chat"
            class="py-4 px-1 border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 font-medium text-sm"
          >
            在线聊天
          </a>
        </nav>
      </div>

      {/* 标签页内容 */}
      <div class="mt-6">
        {activeTab.value === "accounts" && <AccountManager />}
        {activeTab.value === "models" && <ModelManager />}
        {activeTab.value === "config" && <ConfigManager />}
      </div>
    </div>
  );
}
