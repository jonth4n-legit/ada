import { getCookies, setCookie } from "$std/http/cookie.ts";

// 从环境变量获取管理员密码（同时作为 API Key）
export function getAdminPassword(): string {
  const password = Deno.env.get("ADMIN_PASSWORD");
  if (!password) {
    console.warn("⚠️  ADMIN_PASSWORD 环境变量未设置，使用默认密码 'admin'");
    return "admin";
  }
  return password;
}

// 从请求头获取 API Key (Bearer Token)
export function getApiKeyFromRequest(req: Request): string | undefined {
  try {
    const authHeader = req.headers.get("Authorization");
    if (!authHeader) return undefined;

    // 支持 "Bearer <token>" 格式（OpenAI 标准）
    const match = authHeader.match(/^Bearer\s+(.+)$/i);
    if (match) {
      return match[1];
    }

    // 也支持直接传递 token
    return authHeader;
  } catch (error) {
    console.error("Error getting API key:", error);
    return undefined;
  }
}

// 验证 API Key
export function verifyApiKey(apiKey: string): boolean {
  return apiKey === getAdminPassword();
}

// 检查 API 请求是否已认证（通过 Bearer Token）
export function isApiAuthenticated(req: Request): boolean {
  try {
    const apiKey = getApiKeyFromRequest(req);
    if (!apiKey) return false;
    return verifyApiKey(apiKey);
  } catch (error) {
    console.error("Error in API authentication:", error);
    return false;
  }
}

// 生成简单的会话令牌
function generateSessionToken(): string {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return Array.from(array, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

// 验证密码
export function verifyPassword(password: string): boolean {
  return password === getAdminPassword();
}

// 创建会话 - 存储到 Deno KV（持久化）
export async function createSession(kv: Deno.Kv): Promise<string> {
  const token = generateSessionToken();
  await kv.set(
    ["sessions", token],
    {
      created_at: Date.now(),
      expires_at: Date.now() + 604800000, // 7天
    },
    {
      expireIn: 604800000, // 7天后自动删除
    }
  );
  return token;
}

// 验证会话 - 从 Deno KV 读取
export async function isValidSession(
  kv: Deno.Kv,
  token: string
): Promise<boolean> {
  try {
    const entry = await kv.get(["sessions", token]);
    return entry.value !== null;
  } catch (error) {
    console.error("Error validating session:", error);
    return false;
  }
}

// 销毁会话 - 从 Deno KV 删除
export async function destroySession(
  kv: Deno.Kv,
  token: string
): Promise<void> {
  try {
    await kv.delete(["sessions", token]);
  } catch (error) {
    console.error("Error destroying session:", error);
  }
}

// 从请求中获取会话令牌
export function getSessionToken(req: Request): string | undefined {
  try {
    const cookies = getCookies(req.headers);
    return cookies.session;
  } catch (error) {
    console.error("Error getting session token:", error);
    return undefined;
  }
}

// 检查请求是否已认证（通过 Cookie）
export async function isAuthenticated(
  kv: Deno.Kv,
  req: Request
): Promise<boolean> {
  try {
    const token = getSessionToken(req);
    if (!token) return false;
    return await isValidSession(kv, token);
  } catch (error) {
    console.error("Error in authentication:", error);
    return false;
  }
}

// 检查请求是否已认证（支持 Cookie 或 API Key）
export async function isAuthenticatedAny(
  kv: Deno.Kv,
  req: Request
): Promise<boolean> {
  try {
    const cookieAuth = await isAuthenticated(kv, req);
    const apiAuth = isApiAuthenticated(req);
    return cookieAuth || apiAuth;
  } catch (error) {
    console.error("Error in isAuthenticatedAny:", error);
    return false;
  }
}

// 设置会话 Cookie（7天有效期）
export function setSessionCookie(headers: Headers, token: string): void {
  const isDeploy = Deno.env.get("DENO_DEPLOYMENT_ID") !== undefined;
  
  setCookie(headers, {
    name: "session",
    value: token,
    maxAge: 60 * 60 * 24 * 7, // 7天 = 604800秒
    path: "/",
    httpOnly: true,
    secure: isDeploy, // Deno Deploy 上使用 HTTPS，本地开发可能用 HTTP
    sameSite: "Lax",
  });
}

// 清除会话 Cookie
export function clearSessionCookie(headers: Headers): void {
  setCookie(headers, {
    name: "session",
    value: "",
    maxAge: 0,
    path: "/",
  });
}

// 重定向到登录页面
export function redirectToLogin(): Response {
  return new Response(null, {
    status: 302,
    headers: { Location: "/login" },
  });
}

// API 认证中间件：检查 Bearer Token，未通过则返回 401
export function requireApiAuth(req: Request): Response | null {
  try {
    if (!isApiAuthenticated(req)) {
      return new Response(JSON.stringify({ 
        error: {
          message: "Invalid API key. Please provide a valid API key in the Authorization header.",
          type: "invalid_request_error",
          code: "invalid_api_key"
        }
      }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }
    return null;
  } catch (error) {
    console.error("Error in requireApiAuth:", error);
    return new Response(JSON.stringify({ 
      error: {
        message: "Authentication error",
        type: "server_error"
      }
    }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}

// 管理 API 认证中间件：支持 Cookie 或 Bearer Token
export async function requireAuth(
  kv: Deno.Kv,
  req: Request
): Promise<Response | null> {
  try {
    const authenticated = await isAuthenticatedAny(kv, req);
    if (!authenticated) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }
    return null;
  } catch (error) {
    console.error("Error in requireAuth:", error);
    return new Response(JSON.stringify({
      error: "Authentication error",
      details: error instanceof Error ? error.message : "Unknown error"
    }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}

// 页面认证中间件：仅支持 Cookie，未登录则重定向
export async function requireAuthRedirect(
  kv: Deno.Kv,
  req: Request
): Promise<Response | null> {
  try {
    const authenticated = await isAuthenticated(kv, req);
    if (!authenticated) {
      return redirectToLogin();
    }
    return null;
  } catch (error) {
    console.error("Error in requireAuthRedirect:", error);
    return redirectToLogin();
  }
}
