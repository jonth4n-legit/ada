import { signal } from "@preact/signals";
import { useEffect } from "preact/hooks";

interface Account {
  id: string;
  team_id: string;
  csesidx: string;
  user_agent: string;
  available: boolean;
  unavailable_reason?: string;
}

interface Stats {
  total: number;
  available: number;
  unavailable: number;
  currentIndex: number;
}

const accounts = signal<Account[]>([]);
const stats = signal<Stats>({ total: 0, available: 0, unavailable: 0, currentIndex: 0 });
const loading = signal(false);
const showAddModal = signal(false);
const jsonInput = signal("");
const jsonError = signal("");

// 表单字段信号
const formFields = {
  team_id: signal(""),
  secure_c_ses: signal(""),
  host_c_oses: signal(""),
  csesidx: signal(""),
  user_agent: signal(""),
};

export default function AccountManager() {
  useEffect(() => {
    loadAccounts();
  }, []);

  async function loadAccounts() {
    loading.value = true;
    try {
      const res = await fetch("/api/accounts", { credentials: "include" });
      const data = await res.json();
      accounts.value = data.accounts || [];
      stats.value = data.stats || {};
    } catch (error) {
      console.error("Failed to load accounts:", error);
    } finally {
      loading.value = false;
    }
  }

  async function deleteAccount(id: string) {
    if (!confirm("确定要删除这个账号吗？")) return;

    try {
      const res = await fetch(`/api/accounts/${id}`, { method: "DELETE", credentials: "include" });
      if (res.ok) {
        await loadAccounts();
        alert("删除成功");
      }
    } catch (error) {
      console.error("Failed to delete:", error);
      alert("删除失败");
    }
  }

  async function toggleAccount(id: string) {
    try {
      const res = await fetch(`/api/accounts/${id}/toggle`, { method: "POST", credentials: "include" });
      if (res.ok) {
        await loadAccounts();
      }
    } catch (error) {
      console.error("Failed to toggle:", error);
    }
  }

  async function testAccount(id: string) {
    try {
      const res = await fetch(`/api/accounts/${id}/test`, { method: "POST", credentials: "include" });
      const data = await res.json();
      if (data.success) {
        alert("测试成功！");
        await loadAccounts();
      } else {
        alert(`测试失败: ${data.error}`);
      }
    } catch (error) {
      console.error("Failed to test:", error);
      alert("测试失败");
    }
  }

  function handleJsonInput(e: Event) {
    const input = (e.target as HTMLTextAreaElement).value;
    jsonInput.value = input;
    jsonError.value = "";

    if (!input.trim()) {
      return;
    }

    try {
      const data = JSON.parse(input);

      // 验证必需字段
      if (!data.team_id || !data.secure_c_ses || !data.csesidx) {
        jsonError.value = "JSON 缺少必需字段 (team_id, secure_c_ses, csesidx)";
        return;
      }

      // 填充表单
      formFields.team_id.value = data.team_id || "";
      formFields.secure_c_ses.value = data.secure_c_ses || "";
      formFields.host_c_oses.value = data.host_c_oses || "";
      formFields.csesidx.value = data.csesidx || "";
      formFields.user_agent.value = data.user_agent || "";

      jsonError.value = "";
    } catch (error) {
      jsonError.value = "JSON 格式错误，请检查";
    }
  }

  function resetForm() {
    formFields.team_id.value = "";
    formFields.secure_c_ses.value = "";
    formFields.host_c_oses.value = "";
    formFields.csesidx.value = "";
    formFields.user_agent.value = "";
    jsonInput.value = "";
    jsonError.value = "";
  }

  function openAddModal() {
    resetForm();
    showAddModal.value = true;
  }

  async function addAccount(event: Event) {
    event.preventDefault();

    const account = {
      team_id: formFields.team_id.value,
      secure_c_ses: formFields.secure_c_ses.value,
      host_c_oses: formFields.host_c_oses.value,
      csesidx: formFields.csesidx.value,
      user_agent: formFields.user_agent.value,
    };

    try {
      const res = await fetch("/api/accounts", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(account),
      });

      if (res.ok) {
        showAddModal.value = false;
        resetForm();
        await loadAccounts();
        alert("添加成功");
      } else {
        const error = await res.json();
        alert(`添加失败: ${error.error}`);
      }
    } catch (error) {
      console.error("Failed to add:", error);
      alert("添加失败");
    }
  }

  return (
    <div class="px-4 py-6">
      {/* 统计卡片 */}
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white p-6 rounded-lg shadow">
          <div class="text-sm text-gray-500">总账号数</div>
          <div class="text-3xl font-bold mt-2">{stats.value.total}</div>
        </div>
        <div class="bg-white p-6 rounded-lg shadow">
          <div class="text-sm text-gray-500">可用账号</div>
          <div class="text-3xl font-bold text-green-600 mt-2">{stats.value.available}</div>
        </div>
        <div class="bg-white p-6 rounded-lg shadow">
          <div class="text-sm text-gray-500">不可用账号</div>
          <div class="text-3xl font-bold text-red-600 mt-2">{stats.value.unavailable}</div>
        </div>
        <div class="bg-white p-6 rounded-lg shadow">
          <div class="text-sm text-gray-500">当前轮训索引</div>
          <div class="text-3xl font-bold text-blue-600 mt-2">{stats.value.currentIndex}</div>
        </div>
      </div>

      {/* 账号列表 */}
      <div class="bg-white rounded-lg shadow">
        <div class="p-6 border-b border-gray-200 flex justify-between items-center">
          <h2 class="text-lg font-semibold">账号列表</h2>
          <button
            onClick={openAddModal}
            class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            添加账号
          </button>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">序号</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Team ID</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">CSESIDX</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              {accounts.value.length === 0 ? (
                <tr>
                  <td colSpan={5} class="px-6 py-12 text-center text-gray-500">
                    暂无账号，请点击"添加账号"按钮创建
                  </td>
                </tr>
              ) : (
                accounts.value.map((acc, index) => (
                  <tr key={acc.id}>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">{index + 1}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-mono">{acc.team_id.slice(0, 20)}...</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-mono">{acc.csesidx}</td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <span
                        class={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          acc.available ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                        }`}
                      >
                        {acc.available ? "可用" : "不可用"}
                      </span>
                      {acc.unavailable_reason && (
                        <span class="ml-2 text-xs text-gray-500">{acc.unavailable_reason}</span>
                      )}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                      <button
                        onClick={() => toggleAccount(acc.id)}
                        class={`px-3 py-1 rounded ${
                          acc.available ? "bg-yellow-100 text-yellow-800" : "bg-green-100 text-green-800"
                        }`}
                      >
                        {acc.available ? "禁用" : "启用"}
                      </button>
                      <button
                        onClick={() => testAccount(acc.id)}
                        class="px-3 py-1 bg-blue-100 text-blue-800 rounded"
                      >
                        测试
                      </button>
                      <button
                        onClick={() => deleteAccount(acc.id)}
                        class="px-3 py-1 bg-red-100 text-red-800 rounded"
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 添加账号模态框 */}
      {showAddModal.value && (
        <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div class="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <h3 class="text-lg font-semibold mb-4">添加账号</h3>

            <form onSubmit={addAccount}>
              {/* JSON 快捷输入 */}
              <div class="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <label class="block text-sm font-medium text-blue-900 mb-2">
                  🚀 快捷输入 (JSON 格式)
                </label>
                <textarea
                  value={jsonInput.value}
                  onInput={handleJsonInput}
                  placeholder={'粘贴 JSON 格式账号信息，例如：\n{\n  "team_id": "...",\n  "secure_c_ses": "...",\n  "host_c_oses": "...",\n  "csesidx": "...",\n  "user_agent": "..."\n}'}
                  rows={6}
                  class="w-full px-3 py-2 border border-blue-300 rounded-md font-mono text-sm"
                />
                {jsonError.value && (
                  <div class="mt-2 text-sm text-red-600">{jsonError.value}</div>
                )}
                {!jsonError.value && jsonInput.value && (
                  <div class="mt-2 text-sm text-green-600">✓ JSON 解析成功，已自动填充表单</div>
                )}
                <div class="mt-2 text-xs text-blue-600">
                  提示：粘贴 JSON 后，下方表单会自动填充。也可以手动填写。
                </div>
              </div>

              <div class="border-t border-gray-200 pt-4">
                <h4 class="text-sm font-medium text-gray-700 mb-4">或手动填写</h4>
                <div class="space-y-4">
                  <div>
                    <label class="block text-sm font-medium text-gray-700">
                      Team ID <span class="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formFields.team_id.value}
                      onInput={(e) => formFields.team_id.value = (e.target as HTMLInputElement).value}
                      required
                      class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                      placeholder="2350088b-ed16-46d2-b512-4876391c5886"
                    />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700">
                      Secure C SES <span class="text-red-500">*</span>
                    </label>
                    <textarea
                      value={formFields.secure_c_ses.value}
                      onInput={(e) => formFields.secure_c_ses.value = (e.target as HTMLTextAreaElement).value}
                      required
                      rows={3}
                      class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
                      placeholder="CSE.ARsLs02l..."
                    />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700">
                      Host C OSES (可选)
                    </label>
                    <textarea
                      value={formFields.host_c_oses.value}
                      onInput={(e) => formFields.host_c_oses.value = (e.target as HTMLTextAreaElement).value}
                      rows={2}
                      class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
                      placeholder="COS.AQH81rgL..."
                    />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700">
                      CSESIDX <span class="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formFields.csesidx.value}
                      onInput={(e) => formFields.csesidx.value = (e.target as HTMLInputElement).value}
                      required
                      class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                      placeholder="1772320590"
                    />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700">
                      User Agent (可选)
                    </label>
                    <input
                      type="text"
                      value={formFields.user_agent.value}
                      onInput={(e) => formFields.user_agent.value = (e.target as HTMLInputElement).value}
                      class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                      placeholder="Mozilla/5.0..."
                    />
                  </div>
                </div>
              </div>

              <div class="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    showAddModal.value = false;
                    resetForm();
                  }}
                  class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  取消
                </button>
                <button
                  type="submit"
                  class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  保存
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
