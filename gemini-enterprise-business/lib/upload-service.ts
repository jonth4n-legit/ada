/**
 * cfbed 上传服务工具类
 * 文档: https://cfbed.sanyue.de/api/upload.html
 */

export interface UploadOptions {
  endpoint: string;
  apiToken: string;
  file: Uint8Array;
  fileName: string;
  mimeType: string;
  uploadChannel?: "telegram" | "cfr2" | "s3";
  serverCompress?: boolean;
  autoRetry?: boolean;
  uploadNameType?: "default" | "index" | "origin" | "short";
  returnFormat?: "default" | "full";
  uploadFolder?: string;
}

export interface UploadResponse {
  src: string; // 返回的文件路径（不包含域名）
}

/**
 * 上传文件到 cfbed
 */
export async function uploadToCfbed(
  options: UploadOptions
): Promise<UploadResponse> {
  const {
    endpoint,
    apiToken,
    file,
    fileName,
    mimeType,
    uploadChannel = "telegram",
    serverCompress = true,
    autoRetry = true,
    uploadNameType = "default",
    returnFormat = "default",
    uploadFolder,
  } = options;

  // 构建查询参数
  const params = new URLSearchParams();
  params.append("authCode", apiToken); // 使用 authCode 查询参数传递 API Token
  params.append("uploadChannel", uploadChannel);
  params.append("serverCompress", String(serverCompress));
  params.append("autoRetry", String(autoRetry));
  params.append("uploadNameType", uploadNameType);
  params.append("returnFormat", returnFormat);
  if (uploadFolder) {
    params.append("uploadFolder", uploadFolder);
  }

  const url = `${endpoint}?${params.toString()}`;

  // 创建 FormData
  const formData = new FormData();
  const blob = new Blob([file], { type: mimeType });
  formData.append("file", blob, fileName);

  // 发送请求
  const response = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Upload failed (${response.status}): ${errorText}`
    );
  }

  const data = await response.json();

  // cfbed 返回格式: [{ src: "/file/abc123_image.jpg" }]
  if (Array.isArray(data) && data.length > 0 && data[0].src) {
    return data[0];
  }

  throw new Error("Invalid response format from upload service");
}

/**
 * 从 base64 上传文件
 */
export async function uploadBase64ToCfbed(
  endpoint: string,
  apiToken: string,
  base64Data: string,
  fileName: string,
  mimeType: string
): Promise<UploadResponse> {
  // 将 base64 转为 Uint8Array
  const binaryString = atob(base64Data);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  return uploadToCfbed({
    endpoint,
    apiToken,
    file: bytes,
    fileName,
    mimeType,
  });
}

