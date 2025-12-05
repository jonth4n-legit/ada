import { Handlers } from "$fresh/server.ts";
import { getSessionToken, destroySession, clearSessionCookie } from "../../../lib/auth.ts";

export const handler: Handlers = {
  async POST(req, _ctx) {
    const kv = await Deno.openKv();
    try {
      const token = getSessionToken(req);
      if (token) {
        await destroySession(kv, token);
      }

      const headers = new Headers({ Location: "/login" });
      clearSessionCookie(headers);

      return new Response(null, {
        status: 302,
        headers,
      });
    } finally {
      kv.close();
    }
  },
};
