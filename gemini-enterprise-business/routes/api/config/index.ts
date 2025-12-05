import { Handlers } from "$fresh/server.ts";
import { ConfigStore } from "../../../lib/config-store.ts";
import { AccountManager } from "../../../lib/account-manager.ts";
import { requireAuth } from "../../../lib/auth.ts";

/**
 * 配置管理 API
 * GET /api/config - 获取完整配置
 * PUT /api/config - 更新配置
 */
export const handler: Handlers = {
  // 获取完整配置
  async GET(_req, _ctx) {
    const kv = await Deno.openKv();
    const store = new ConfigStore(kv);
    const accountManager = new AccountManager(kv);

    try {
      const authError = await requireAuth(kv, _req);
      if (authError) return authError;

      const config = await store.getConfig();
      const accounts = await accountManager.listAccounts();
      const models = await store.listModels();

      return Response.json({
        proxy: config.proxy,
        image_base_url: config.image_base_url,
        upload_api_token: config.upload_api_token,
        upload_endpoint: config.upload_endpoint,
        accounts,
        models,
      });
    } catch (error) {
      console.error("Failed to get config:", error);
      return Response.json({ error: "Failed to get config" }, { status: 500 });
    } finally {
      kv.close();
    }
  },

  // 更新配置
  async PUT(req, _ctx) {
    const kv = await Deno.openKv();
    const store = new ConfigStore(kv);

    try {
      const authError = await requireAuth(kv, req);
      if (authError) return authError;

      const data = await req.json();

      await store.updateConfig({
        proxy: data.proxy,
        image_base_url: data.image_base_url,
        upload_api_token: data.upload_api_token,
        upload_endpoint: data.upload_endpoint,
      });

      return Response.json({ success: true });
    } catch (error) {
      console.error("Failed to update config:", error);
      return Response.json(
        { error: error instanceof Error ? error.message : "Failed to update config" },
        { status: 500 }
      );
    } finally {
      kv.close();
    }
  },
};
