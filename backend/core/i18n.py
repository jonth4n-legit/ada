"""
Gemini Ultra Gateway - Internationalization (i18n) Module
Supports English (en) and Chinese (zh) languages
"""

from typing import Dict, Optional
import os

# Default language
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")

# Translation dictionary
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # General
        "app_name": "Gemini Ultra Gateway",
        "loading": "Loading...",
        "save": "Save",
        "cancel": "Cancel",
        "delete": "Delete",
        "edit": "Edit",
        "create": "Create",
        "refresh": "Refresh",
        "confirm": "Confirm",
        "close": "Close",
        "back": "Back",
        "next": "Next",
        "submit": "Submit",
        "search": "Search",
        "filter": "Filter",
        "clear": "Clear",
        "reset": "Reset",
        "yes": "Yes",
        "no": "No",
        "ok": "OK",
        "error": "Error",
        "success": "Success",
        "warning": "Warning",
        "info": "Info",
        
        # Status
        "valid": "Valid",
        "invalid": "Invalid",
        "unknown": "Unknown",
        "active": "Active",
        "inactive": "Inactive",
        "enabled": "Enabled",
        "disabled": "Disabled",
        "online": "Online",
        "offline": "Offline",
        "available": "Available",
        "unavailable": "Unavailable",
        "expired": "Expired",
        "pending": "Pending",
        "running": "Running",
        "completed": "Completed",
        "failed": "Failed",
        "cancelled": "Cancelled",
        
        # Time
        "never_executed": "Never executed",
        "last_run": "Last run",
        "last_used": "Last used",
        "created_at": "Created at",
        "updated_at": "Updated at",
        "expires_at": "Expires at",
        "start_time": "Start time",
        "end_time": "End time",
        "duration": "Duration",
        
        # Account
        "account": "Account",
        "accounts": "Accounts",
        "account_name": "Account Name",
        "account_status": "Account Status",
        "cookie_status": "Cookie Status",
        "remaining_cooldown": "Remaining Cooldown",
        "fail_count": "Fail Count",
        "last_error": "Last Error",
        "reset_cooldown": "Reset Cooldown",
        "check_cookie": "Check Cookie",
        "refresh_cookie": "Refresh Cookie",
        
        # API Keys
        "api_key": "API Key",
        "api_keys": "API Keys",
        "create_api_key": "Create API Key",
        "key_name": "Key Name",
        "key_prefix": "Key Prefix",
        "rate_limit": "Rate Limit",
        "requests_per_minute": "Requests/Minute",
        "requests_per_day": "Requests/Day",
        "total_requests": "Total Requests",
        "copy_key": "Copy Key",
        "key_copied": "Key copied to clipboard",
        "key_warning": "Save this key! It will only be shown once.",
        
        # Chat
        "chat": "Chat",
        "message": "Message",
        "send": "Send",
        "clear_chat": "Clear Chat",
        "new_conversation": "New Conversation",
        "conversation_history": "Conversation History",
        "model": "Model",
        "temperature": "Temperature",
        "max_tokens": "Max Tokens",
        "streaming": "Streaming",
        
        # Media
        "image": "Image",
        "images": "Images",
        "video": "Video",
        "videos": "Videos",
        "generate_image": "Generate Image",
        "generate_video": "Generate Video",
        "upload_image": "Upload Image",
        "upload_video": "Upload Video",
        "download": "Download",
        "preview": "Preview",
        "prompt": "Prompt",
        "style": "Style",
        "aspect_ratio": "Aspect Ratio",
        "quality": "Quality",
        "duration_seconds": "Duration (seconds)",
        
        # Video Studio
        "video_studio": "Video Studio",
        "text_to_video": "Text to Video",
        "image_to_video": "Image to Video",
        "extend_video": "Extend Video",
        "interpolate_frames": "Interpolate Frames",
        "start_frame": "Start Frame",
        "end_frame": "End Frame",
        "extension_duration": "Extension Duration",
        "transition_style": "Transition Style",
        
        # Image Studio
        "image_studio": "Image Studio",
        "text_to_image": "Text to Image",
        "edit_image": "Edit Image",
        "remix_image": "Remix Image",
        "from_ingredients": "From Ingredients",
        "subject": "Subject",
        "scene": "Scene",
        "mood": "Mood",
        "blend_mode": "Blend Mode",
        "style_strength": "Style Strength",
        "negative_prompt": "Negative Prompt",
        
        # Keep Alive
        "keep_alive": "Keep Alive",
        "keep_alive_tasks": "Keep Alive Tasks",
        "create_task": "Create Task",
        "task_name": "Task Name",
        "cron_expression": "Cron Expression",
        "run_now": "Run Now",
        "execute_now": "Execute Now",
        "stop_task": "Stop Task",
        "cancel_task": "Cancel Task",
        "task_logs": "Task Logs",
        "execution_history": "Execution History",
        "enable_keep_alive": "Enable Keep Alive Task",
        "execution_time": "Execution Time (Beijing Time)",
        "save_settings": "Save Settings",
        "last_execution_time": "Last Execution Time",
        "last_execution_result": "Last Execution Result",
        "no_execution_logs": "No execution logs",
        "success_count": "Success",
        "fail_count_label": "Failed",
        "view_details": "View Details",
        "bulk_delete": "Bulk Delete",
        "confirm_execute": "Are you sure you want to execute the keep-alive task now?",
        "confirm_cancel": "Are you sure you want to cancel the running keep-alive task?",
        "confirm_bulk_delete": "Are you sure you want to delete the selected {count} logs? This cannot be undone.",
        "task_started": "Keep-alive task has started. Please check logs later.",
        "task_cancelled": "Task cancelled",
        "log_details": "Log Details",
        "click_to_view_logs": "Click 'View Details' in execution history to view logs",
        "load_failed": "Load failed",
        "load_failed_retry": "Load failed, please refresh to retry",
        "select_logs_to_delete": "Please select logs to delete",
        
        # Dashboard
        "dashboard": "Dashboard",
        "overview": "Overview",
        "statistics": "Statistics",
        "total_accounts": "Total Accounts",
        "available_accounts": "Available Accounts",
        "total_api_keys": "Total API Keys",
        "active_api_keys": "Active API Keys",
        "requests_today": "Requests Today",
        "tokens_today": "Tokens Today",
        
        # Admin
        "admin": "Admin",
        "admin_panel": "Admin Panel",
        "login": "Login",
        "logout": "Logout",
        "username": "Username",
        "password": "Password",
        "remember_me": "Remember Me",
        "forgot_password": "Forgot Password",
        "settings": "Settings",
        "account_settings": "Account Settings",
        
        # Logs
        "logs": "Logs",
        "api_logs": "API Logs",
        "endpoint": "Endpoint",
        "method": "Method",
        "status_code": "Status Code",
        "response_time": "Response Time",
        "client_ip": "Client IP",
        "user_agent": "User Agent",
        
        # Messages
        "request_failed": "Request failed",
        "upload_successful": "Upload successful",
        "upload_failed": "Upload failed",
        "saved_successfully": "Saved successfully",
        "deleted_successfully": "Deleted successfully",
        "operation_successful": "Operation successful",
        "operation_failed": "Operation failed",
        "invalid_input": "Invalid input",
        "required_field": "This field is required",
        "no_data": "No data available",
        "no_results": "No results found",
        "confirm_delete": "Are you sure you want to delete this?",
        "session_expired": "Session expired. Please login again.",
        "unauthorized": "Unauthorized access",
        "forbidden": "Access forbidden",
        "not_found": "Not found",
        "server_error": "Server error occurred",
        
        # Language
        "language": "Language",
        "english": "English",
        "chinese": "Chinese",
        "switch_language": "Switch Language",
    },
    
    "zh": {
        # General
        "app_name": "Gemini 超级网关",
        "loading": "加载中...",
        "save": "保存",
        "cancel": "取消",
        "delete": "删除",
        "edit": "编辑",
        "create": "创建",
        "refresh": "刷新",
        "confirm": "确认",
        "close": "关闭",
        "back": "返回",
        "next": "下一步",
        "submit": "提交",
        "search": "搜索",
        "filter": "筛选",
        "clear": "清除",
        "reset": "重置",
        "yes": "是",
        "no": "否",
        "ok": "确定",
        "error": "错误",
        "success": "成功",
        "warning": "警告",
        "info": "信息",
        
        # Status
        "valid": "有效",
        "invalid": "无效",
        "unknown": "未知",
        "active": "活跃",
        "inactive": "不活跃",
        "enabled": "已启用",
        "disabled": "已禁用",
        "online": "在线",
        "offline": "离线",
        "available": "可用",
        "unavailable": "不可用",
        "expired": "已过期",
        "pending": "等待中",
        "running": "运行中",
        "completed": "已完成",
        "failed": "失败",
        "cancelled": "已取消",
        
        # Time
        "never_executed": "从未执行",
        "last_run": "上次运行",
        "last_used": "上次使用",
        "created_at": "创建时间",
        "updated_at": "更新时间",
        "expires_at": "过期时间",
        "start_time": "开始时间",
        "end_time": "结束时间",
        "duration": "持续时间",
        
        # Account
        "account": "账号",
        "accounts": "账号管理",
        "account_name": "账号名称",
        "account_status": "账号状态",
        "cookie_status": "Cookie 状态",
        "remaining_cooldown": "剩余冷却",
        "fail_count": "失败次数",
        "last_error": "最后错误",
        "reset_cooldown": "重置冷却",
        "check_cookie": "检查 Cookie",
        "refresh_cookie": "刷新 Cookie",
        
        # API Keys
        "api_key": "API 密钥",
        "api_keys": "API 密钥管理",
        "create_api_key": "创建 API 密钥",
        "key_name": "密钥名称",
        "key_prefix": "密钥前缀",
        "rate_limit": "速率限制",
        "requests_per_minute": "每分钟请求数",
        "requests_per_day": "每天请求数",
        "total_requests": "总请求数",
        "copy_key": "复制密钥",
        "key_copied": "密钥已复制到剪贴板",
        "key_warning": "请保存此密钥！它只会显示一次。",
        
        # Chat
        "chat": "聊天",
        "message": "消息",
        "send": "发送",
        "clear_chat": "清除聊天",
        "new_conversation": "新对话",
        "conversation_history": "对话历史",
        "model": "模型",
        "temperature": "温度",
        "max_tokens": "最大令牌数",
        "streaming": "流式输出",
        
        # Media
        "image": "图片",
        "images": "图片",
        "video": "视频",
        "videos": "视频",
        "generate_image": "生成图片",
        "generate_video": "生成视频",
        "upload_image": "上传图片",
        "upload_video": "上传视频",
        "download": "下载",
        "preview": "预览",
        "prompt": "提示词",
        "style": "风格",
        "aspect_ratio": "宽高比",
        "quality": "质量",
        "duration_seconds": "时长（秒）",
        
        # Video Studio
        "video_studio": "视频工作室",
        "text_to_video": "文字生成视频",
        "image_to_video": "图片生成视频",
        "extend_video": "延长视频",
        "interpolate_frames": "帧插值",
        "start_frame": "起始帧",
        "end_frame": "结束帧",
        "extension_duration": "延长时长",
        "transition_style": "过渡风格",
        
        # Image Studio
        "image_studio": "图片工作室",
        "text_to_image": "文字生成图片",
        "edit_image": "编辑图片",
        "remix_image": "混合图片",
        "from_ingredients": "从素材生成",
        "subject": "主体",
        "scene": "场景",
        "mood": "氛围",
        "blend_mode": "混合模式",
        "style_strength": "风格强度",
        "negative_prompt": "负面提示词",
        
        # Keep Alive
        "keep_alive": "保活",
        "keep_alive_tasks": "保活任务",
        "create_task": "创建任务",
        "task_name": "任务名称",
        "cron_expression": "Cron 表达式",
        "run_now": "立即运行",
        "execute_now": "立即执行",
        "stop_task": "停止任务",
        "cancel_task": "中断保活",
        "task_logs": "任务日志",
        "execution_history": "执行历史",
        "enable_keep_alive": "启用保活任务",
        "execution_time": "执行时间（北京时间）",
        "save_settings": "保存设置",
        "last_execution_time": "上次执行时间",
        "last_execution_result": "上次执行结果",
        "no_execution_logs": "暂无执行日志",
        "success_count": "成功",
        "fail_count_label": "失败",
        "view_details": "查看详情",
        "bulk_delete": "批量删除",
        "confirm_execute": "确定要立即执行保活任务吗？",
        "confirm_cancel": "确定要中断正在执行的保活任务吗？",
        "confirm_bulk_delete": "确定要删除选中的 {count} 条日志吗？删除后无法恢复。",
        "task_started": "保活任务已开始执行，请稍后查看日志",
        "task_cancelled": "任务已中断",
        "log_details": "日志详情",
        "click_to_view_logs": "点击执行历史中的"查看详情"查看日志",
        "load_failed": "加载失败",
        "load_failed_retry": "加载失败，请刷新重试",
        "select_logs_to_delete": "请选择要删除的日志",
        
        # Dashboard
        "dashboard": "仪表盘",
        "overview": "概览",
        "statistics": "统计",
        "total_accounts": "总账号数",
        "available_accounts": "可用账号数",
        "total_api_keys": "总 API 密钥数",
        "active_api_keys": "活跃 API 密钥数",
        "requests_today": "今日请求数",
        "tokens_today": "今日令牌数",
        
        # Admin
        "admin": "管理员",
        "admin_panel": "管理面板",
        "login": "登录",
        "logout": "退出",
        "username": "用户名",
        "password": "密码",
        "remember_me": "记住我",
        "forgot_password": "忘记密码",
        "settings": "设置",
        "account_settings": "账号设置",
        
        # Logs
        "logs": "日志",
        "api_logs": "API 日志",
        "endpoint": "端点",
        "method": "方法",
        "status_code": "状态码",
        "response_time": "响应时间",
        "client_ip": "客户端 IP",
        "user_agent": "用户代理",
        
        # Messages
        "request_failed": "请求失败",
        "upload_successful": "上传成功",
        "upload_failed": "上传失败",
        "saved_successfully": "保存成功",
        "deleted_successfully": "删除成功",
        "operation_successful": "操作成功",
        "operation_failed": "操作失败",
        "invalid_input": "输入无效",
        "required_field": "此字段为必填项",
        "no_data": "暂无数据",
        "no_results": "未找到结果",
        "confirm_delete": "确定要删除吗？",
        "session_expired": "会话已过期，请重新登录。",
        "unauthorized": "未授权访问",
        "forbidden": "禁止访问",
        "not_found": "未找到",
        "server_error": "服务器错误",
        
        # Language
        "language": "语言",
        "english": "英语",
        "chinese": "中文",
        "switch_language": "切换语言",
    }
}


def get_text(key: str, lang: Optional[str] = None) -> str:
    """Get translated text for a key"""
    language = lang or DEFAULT_LANGUAGE
    if language not in TRANSLATIONS:
        language = "en"
    
    return TRANSLATIONS[language].get(key, key)


def get_all_translations(lang: Optional[str] = None) -> Dict[str, str]:
    """Get all translations for a language"""
    language = lang or DEFAULT_LANGUAGE
    if language not in TRANSLATIONS:
        language = "en"
    
    return TRANSLATIONS[language].copy()


def t(key: str, lang: Optional[str] = None) -> str:
    """Shorthand for get_text"""
    return get_text(key, lang)


class I18n:
    """I18n helper class for templates"""
    
    def __init__(self, lang: str = DEFAULT_LANGUAGE):
        self.lang = lang if lang in TRANSLATIONS else "en"
    
    def __call__(self, key: str) -> str:
        return get_text(key, self.lang)
    
    def get(self, key: str) -> str:
        return get_text(key, self.lang)
    
    def all(self) -> Dict[str, str]:
        return get_all_translations(self.lang)
    
    def set_language(self, lang: str) -> None:
        self.lang = lang if lang in TRANSLATIONS else "en"
