import { Head } from "$fresh/runtime.ts";
import { Handlers, PageProps } from "$fresh/server.ts";

interface LoginData {
  error?: string;
}

const errorMessages: Record<string, string> = {
  missing_password: "请输入密码",
  invalid_password: "密码错误，请重试",
  server_error: "服务器错误，请稍后再试",
};

export const handler: Handlers<LoginData> = {
  GET(req, ctx) {
    const url = new URL(req.url);
    const errorCode = url.searchParams.get("error");
    const error = errorCode ? errorMessages[errorCode] : undefined;
    
    return ctx.render({ error });
  },
};

export default function LoginPage({ data }: PageProps<LoginData>) {
  return (
    <>
      <Head>
        <title>登录 - Business Gemini Pool</title>
        <script src="https://cdn.tailwindcss.com"></script>
      </Head>
      <div class="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div class="max-w-md w-full bg-white rounded-lg shadow-md p-8">
          <div class="text-center mb-8">
            <h1 class="text-3xl font-bold text-gray-900">Business Gemini Pool</h1>
            <p class="text-gray-600 mt-2">管理控制台登录</p>
          </div>

          {data.error && (
            <div class="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded">
              {data.error}
            </div>
          )}

          <form method="POST" action="/api/auth/login" class="space-y-4">
            <div>
              <label for="password" class="block text-sm font-medium text-gray-700 mb-2">
                访问密码
              </label>
              <input
                type="password"
                id="password"
                name="password"
                required
                autofocus
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="请输入访问密码"
              />
            </div>

            <button
              type="submit"
              class="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              登录
            </button>
          </form>

          <div class="mt-6 text-center text-sm text-gray-500">
            <p>提示：使用环境变量 <code class="bg-gray-100 px-1 rounded">ADMIN_PASSWORD</code> 设置访问密码</p>
          </div>
        </div>
      </div>
    </>
  );
}
