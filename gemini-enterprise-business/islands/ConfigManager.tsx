import { signal } from "@preact/signals";
import { useEffect } from "preact/hooks";

interface Config {
  proxy?: string;
  image_base_url?: string;
  upload_api_token?: string;
  upload_endpoint?: string;
}

const config = signal<Config>({});
const loading = signal(false);
const message = signal("");
const testFile = signal<File | null>(null);
const testResult = signal("");

export default function ConfigManager() {
  useEffect(() => {
    loadConfig();
  }, []);

  async function loadConfig() {
    loading.value = true;
    try {
      const res = await fetch("/api/config", {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        config.value = data;
      }
    } catch (error) {
      console.error("Failed to load config:", error);
    } finally {
      loading.value = false;
    }
  }

  async function saveConfig() {
    loading.value = true;
    message.value = "";
    try {
      const res = await fetch("/api/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(config.value),
      });

      if (res.ok) {
        message.value = "配置保存成功";
        setTimeout(() => (message.value = ""), 3000);
      } else {
        message.value = "保存失败";
      }
    } catch (error) {
      message.value = "保存失败: " + error;
    } finally {
      loading.value = false;
    }
  }

  function handleFileSelect(e: Event) {
    const target = e.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      testFile.value = target.files[0];
    }
  }

  async function testUpload() {
    if (!testFile.value) {
      testResult.value = "请先选择文件";
      return;
    }

    if (!config.value.upload_endpoint || !config.value.upload_api_token) {
      testResult.value = "请先保存配置后再测试上传";
      return;
    }

    loading.value = true;
    testResult.value = "上传中...";

    try {
      const formData = new FormData();
      formData.append("file", testFile.value);

      // 通过后端API上传，避免CORS问题
      const res = await fetch("/api/upload/test", {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      const data = await res.json();

      if (res.ok && data.success) {
        testResult.value = `上传成功！\n文件名: ${data.filename}\n大小: ${data.size} bytes\n路径: ${data.src}\n完整URL: ${data.url}`;
      } else {
        testResult.value = `上传失败: ${data.error || "未知错误"}`;
      }
    } catch (error) {
      testResult.value = `上传失败: ${error}`;
    } finally {
      loading.value = false;
    }
  }

  return (
    <div class="max-w-4xl mx-auto p-6">
      <h2 class="text-2xl font-bold mb-6">系统配置</h2>

      {message.value && (
        <div class="mb-4 p-3 bg-green-100 text-green-700 rounded">
          {message.value}
        </div>
      )}

      <div class="space-y-6">
        {/* 代理配置 */}
        <div class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-semibold mb-4">代理设置</h3>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              代理地址 (可选)
            </label>
            <input
              type="text"
              value={config.value.proxy || ""}
              onInput={(e) =>
                (config.value = {
                  ...config.value,
                  proxy: (e.target as HTMLInputElement).value,
                })}
              placeholder="http://proxy.example.com:8080"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* 图片基础 URL */}
        <div class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-semibold mb-4">图片设置</h3>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              图片基础 URL (可选)
            </label>
            <input
              type="text"
              value={config.value.image_base_url || ""}
              onInput={(e) =>
                (config.value = {
                  ...config.value,
                  image_base_url: (e.target as HTMLInputElement).value,
                })}
              placeholder="https://your-domain.com"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* 上传服务配置 */}
        <div class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-semibold mb-4">文件上传服务 (cfbed)</h3>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                上传端点
              </label>
              <input
                type="text"
                value={config.value.upload_endpoint || ""}
                onInput={(e) =>
                  (config.value = {
                    ...config.value,
                    upload_endpoint: (e.target as HTMLInputElement).value,
                  })}
                placeholder="https://cfbed.sanyue.de/upload"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p class="mt-1 text-sm text-gray-500">
                cfbed 上传 API 端点地址
              </p>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                API Token
              </label>
              <input
                type="password"
                value={config.value.upload_api_token || ""}
                onInput={(e) =>
                  (config.value = {
                    ...config.value,
                    upload_api_token: (e.target as HTMLInputElement).value,
                  })}
                placeholder="YOUR_API_TOKEN"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p class="mt-1 text-sm text-gray-500">
                从 cfbed 管理界面获取的 API Token
              </p>
            </div>

            {/* 测试上传 */}
            <div class="border-t pt-4 mt-4">
              <h4 class="text-md font-medium mb-3">测试上传</h4>
              <div class="space-y-3">
                <div>
                  <input
                    type="file"
                    onChange={handleFileSelect}
                    accept="image/*,video/*"
                    class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                  />
                </div>
                <button
                  onClick={testUpload}
                  disabled={loading.value || !testFile.value}
                  class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {loading.value ? "上传中..." : "测试上传"}
                </button>
                {testResult.value && (
                  <pre class="mt-3 p-3 bg-gray-100 rounded text-sm overflow-auto max-h-48">
                    {testResult.value}
                  </pre>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* 保存按钮 */}
        <div class="flex justify-end">
          <button
            onClick={saveConfig}
            disabled={loading.value}
            class="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loading.value ? "保存中..." : "保存配置"}
          </button>
        </div>
      </div>
    </div>
  );
}
