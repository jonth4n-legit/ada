import { Handlers } from "$fresh/server.ts";
import { AccountManager } from "../../../../lib/account-manager.ts";

import { requireAuth } from "../../../../lib/auth.ts";
/**
 * 切换账号可用状态
 * POST /api/accounts/:id/toggle
 */
export const handler: Handlers = {
  async POST(_req, ctx) {
    const kv = await Deno.openKv();
    const manager = new AccountManager(kv);
    const { id } = ctx.params;

    try {
      const authError = await requireAuth(kv, _req);
      if (authError) return authError;

      const account = await manager.getAccount(id);
      if (!account) {
        return Response.json({ error: "Account not found" }, { status: 404 });
      }

      const newAvailable = await manager.toggleAvailability(id);

      return Response.json({
        success: true,
        available: newAvailable,
      });
    } catch (error) {
      console.error("Failed to toggle account:", error);
      return Response.json({ error: "Failed to toggle account" }, { status: 500 });
    } finally {
      kv.close();
    }
  },
};
