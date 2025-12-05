import { Handlers } from "$fresh/server.ts";
import { ConfigStore } from "../../../lib/config-store.ts";
import { uploadToCfbed } from "../../../lib/upload-service.ts";
import { requireAuth } from "../../../lib/auth.ts";

/**
 * 测试上传接口
 * POST /api/upload/test
 */
export const handler: Handlers = {
  async POST(req, _ctx) {
    const kv = await Deno.openKv();

    try {
      // 认证检查
      const authError = await requireAuth(kv, req);
      if (authError) return authError;

      // 获取配置
      const configStore = new ConfigStore(kv);
      const config = await configStore.getConfig();

      if (!config.upload_endpoint || !config.upload_api_token) {
        return Response.json(
          { error: "上传服务未配置" },
          { status: 400 }
        );
      }

      // 解析上传的文件
      const formData = await req.formData();
      const file = formData.get("file") as File;

      if (!file) {
        return Response.json(
          { error: "未找到文件" },
          { status: 400 }
        );
      }

      // 读取文件数据
      const arrayBuffer = await file.arrayBuffer();
      const bytes = new Uint8Array(arrayBuffer);

      // 上传到 cfbed
      const result = await uploadToCfbed({
        endpoint: config.upload_endpoint,
        apiToken: config.upload_api_token,
        file: bytes,
        fileName: file.name,
        mimeType: file.type,
      });

      // 构建完整 URL
      const baseUrl = config.image_base_url ||
        config.upload_endpoint.replace(/\/upload$/, "");
      const fullUrl = `${baseUrl}${result.src}`;

      return Response.json({
        success: true,
        src: result.src,
        url: fullUrl,
        filename: file.name,
        size: bytes.length,
      });
    } catch (error) {
      console.error("Upload test failed:", error);
      return Response.json(
        {
          error: error instanceof Error ? error.message : "上传失败",
          success: false,
        },
        { status: 500 }
      );
    } finally {
      kv.close();
    }
  },
};
