import { Head } from "$fresh/runtime.ts";
import { Handlers } from "$fresh/server.ts";
import { requireAuthRedirect } from "../lib/auth.ts";
import TabManager from "../islands/TabManager.tsx";

export const handler: Handlers = {
  async GET(req, ctx) {
    const kv = await Deno.openKv();
    try {
      const authError = await requireAuthRedirect(kv, req);
      if (authError) return authError;

      return ctx.render();
    } finally {
      kv.close();
    }
  },
};

export default function Home() {
  return (
    <>
      <Head>
        <title>Business Gemini Pool - 管理控制台</title>
        <script src="https://cdn.tailwindcss.com"></script>
      </Head>
      <div class="min-h-screen bg-gray-50">
        <header class="bg-white shadow">
          <div class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 flex justify-between items-center">
            <h1 class="text-3xl font-bold text-gray-900">
              Business Gemini Pool
              <span class="text-sm font-normal text-gray-500 ml-4">管理控制台</span>
            </h1>
            <form method="POST" action="/api/auth/logout">
              <button
                type="submit"
                class="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
              >
                登出
              </button>
            </form>
          </div>
        </header>
        <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <TabManager />
        </main>
      </div>
    </>
  );
}
