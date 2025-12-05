import { signal } from "@preact/signals";
import { useEffect } from "preact/hooks";

interface Model {
  id: string;
  name: string;
  enabled: boolean;
}

const models = signal<Model[]>([]);
const loading = signal(false);
const showAddModal = signal(false);
const editingModel = signal<Model | null>(null);

export default function ModelManager() {
  useEffect(() => {
    loadModels();
  }, []);

  async function loadModels() {
    loading.value = true;
    try {
      const res = await fetch("/api/models", { credentials: "include" });
      const data = await res.json();
      models.value = data.models || [];
    } catch (error) {
      console.error("Failed to load models:", error);
    } finally {
      loading.value = false;
    }
  }

  async function deleteModel(id: string) {
    if (!confirm("确定要删除这个模型吗？")) return;

    try {
      const res = await fetch(`/api/models/${id}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (res.ok) {
        await loadModels();
        alert("删除成功");
      }
    } catch (error) {
      console.error("Failed to delete:", error);
      alert("删除失败");
    }
  }

  async function toggleModel(id: string) {
    try {
      const model = models.value.find((m) => m.id === id);
      if (!model) return;

      const res = await fetch(`/api/models/${id}`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...model,
          enabled: !model.enabled,
        }),
      });

      if (res.ok) {
        await loadModels();
      }
    } catch (error) {
      console.error("Failed to toggle:", error);
    }
  }

  async function saveModel(event: Event) {
    event.preventDefault();
    const form = event.target as HTMLFormElement;
    const formData = new FormData(form);

    const modelData = {
      id: formData.get("id"),
      name: formData.get("name"),
      enabled: true,
    };

    try {
      const url = editingModel.value
        ? `/api/models/${editingModel.value.id}`
        : "/api/models";
      const method = editingModel.value ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(modelData),
      });

      if (res.ok) {
        showAddModal.value = false;
        editingModel.value = null;
        form.reset();
        await loadModels();
        alert(editingModel.value ? "更新成功" : "添加成功");
      } else {
        const error = await res.json();
        alert(`操作失败: ${error.error}`);
      }
    } catch (error) {
      console.error("Failed to save:", error);
      alert("操作失败");
    }
  }

  function openAddModal() {
    editingModel.value = null;
    showAddModal.value = true;
  }

  function openEditModal(model: Model) {
    editingModel.value = model;
    showAddModal.value = true;
  }

  return (
    <div class="px-4 py-6">
      <div class="bg-white rounded-lg shadow">
        <div class="p-6 border-b border-gray-200 flex justify-between items-center">
          <h2 class="text-lg font-semibold">模型列表</h2>
          <button
            onClick={openAddModal}
            class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            添加模型
          </button>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  模型 ID
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  模型名称
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  状态
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  操作
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              {models.value.length === 0 ? (
                <tr>
                  <td colSpan={4} class="px-6 py-12 text-center text-gray-500">
                    暂无模型，请点击"添加模型"按钮创建
                  </td>
                </tr>
              ) : (
                models.value.map((model) => (
                  <tr key={model.id}>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-mono">
                      {model.id}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                      {model.name}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <span
                        class={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          model.enabled
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {model.enabled ? "启用" : "禁用"}
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                      <button
                        onClick={() => toggleModel(model.id)}
                        class={`px-3 py-1 rounded ${
                          model.enabled
                            ? "bg-yellow-100 text-yellow-800"
                            : "bg-green-100 text-green-800"
                        }`}
                      >
                        {model.enabled ? "禁用" : "启用"}
                      </button>
                      <button
                        onClick={() => openEditModal(model)}
                        class="px-3 py-1 bg-blue-100 text-blue-800 rounded"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => deleteModel(model.id)}
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

      {/* 添加/编辑模型模态框 */}
      {showAddModal.value && (
        <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 class="text-lg font-semibold mb-4">
              {editingModel.value ? "编辑模型" : "添加模型"}
            </h3>
            <form onSubmit={saveModel}>
              <div class="space-y-4">
                <div>
                  <label class="block text-sm font-medium text-gray-700">
                    模型 ID
                  </label>
                  <input
                    type="text"
                    name="id"
                    required
                    value={editingModel.value?.id || ""}
                    disabled={!!editingModel.value}
                    class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-100"
                    placeholder="gemini-enterprise"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700">
                    模型名称
                  </label>
                  <input
                    type="text"
                    name="name"
                    required
                    value={editingModel.value?.name || ""}
                    class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="Gemini Enterprise"
                  />
                </div>
              </div>
              <div class="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    showAddModal.value = false;
                    editingModel.value = null;
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
