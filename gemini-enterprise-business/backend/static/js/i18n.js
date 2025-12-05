/**
 * Gemini Ultra Gateway - Frontend Internationalization (i18n)
 * Supports English (en) and Chinese (zh) languages
 */

const I18n = {
    // Current language
    currentLang: localStorage.getItem('language') || 'en',
    
    // Translations
    translations: {
        en: {
            // General
            app_name: "Gemini Ultra Gateway",
            loading: "Loading...",
            save: "Save",
            cancel: "Cancel",
            delete: "Delete",
            edit: "Edit",
            create: "Create",
            refresh: "Refresh",
            confirm: "Confirm",
            close: "Close",
            back: "Back",
            next: "Next",
            submit: "Submit",
            search: "Search",
            filter: "Filter",
            clear: "Clear",
            reset: "Reset",
            yes: "Yes",
            no: "No",
            ok: "OK",
            error: "Error",
            success: "Success",
            warning: "Warning",
            info: "Info",
            
            // Status
            valid: "Valid",
            invalid: "Invalid",
            unknown: "Unknown",
            active: "Active",
            inactive: "Inactive",
            enabled: "Enabled",
            disabled: "Disabled",
            online: "Online",
            offline: "Offline",
            available: "Available",
            unavailable: "Unavailable",
            expired: "Expired",
            pending: "Pending",
            running: "Running",
            completed: "Completed",
            failed: "Failed",
            cancelled: "Cancelled",
            
            // Time
            never_executed: "Never executed",
            last_run: "Last run",
            last_used: "Last used",
            created_at: "Created at",
            updated_at: "Updated at",
            expires_at: "Expires at",
            start_time: "Start time",
            end_time: "End time",
            duration: "Duration",
            
            // Account
            account: "Account",
            accounts: "Accounts",
            account_name: "Account Name",
            account_status: "Account Status",
            cookie_status: "Cookie Status",
            remaining_cooldown: "Remaining Cooldown",
            fail_count: "Fail Count",
            last_error: "Last Error",
            reset_cooldown: "Reset Cooldown",
            check_cookie: "Check Cookie",
            refresh_cookie: "Refresh Cookie",
            
            // API Keys
            api_key: "API Key",
            api_keys: "API Keys",
            create_api_key: "Create API Key",
            key_name: "Key Name",
            key_prefix: "Key Prefix",
            rate_limit: "Rate Limit",
            requests_per_minute: "Requests/Min",
            requests_per_day: "Requests/Day",
            total_requests: "Total Requests",
            copy_key: "Copy Key",
            key_copied: "Key copied to clipboard",
            key_warning: "Save this key! It will only be shown once.",
            never_expires: "Never expires",
            
            // Chat
            chat: "Chat",
            message: "Message",
            send: "Send",
            clear_chat: "Clear Chat",
            new_conversation: "New Conversation",
            conversation_history: "Conversation History",
            model: "Model",
            temperature: "Temperature",
            max_tokens: "Max Tokens",
            streaming: "Streaming",
            
            // Media
            image: "Image",
            images: "Images",
            video: "Video",
            videos: "Videos",
            generate_image: "Generate Image",
            generate_video: "Generate Video",
            upload_image: "Upload Image",
            upload_video: "Upload Video",
            download: "Download",
            preview: "Preview",
            prompt: "Prompt",
            style: "Style",
            aspect_ratio: "Aspect Ratio",
            quality: "Quality",
            duration_seconds: "Duration (sec)",
            
            // Keep Alive
            keep_alive: "Keep Alive",
            keep_alive_tasks: "Keep Alive Tasks",
            create_task: "Create Task",
            task_name: "Task Name",
            cron_expression: "Cron Expression",
            run_now: "Run Now",
            stop_task: "Stop",
            task_logs: "Task Logs",
            execution_history: "Execution History",
            
            // Dashboard
            dashboard: "Dashboard",
            overview: "Overview",
            statistics: "Statistics",
            total_accounts: "Total Accounts",
            available_accounts: "Available",
            total_api_keys: "Total API Keys",
            active_api_keys: "Active Keys",
            requests_today: "Requests Today",
            tokens_today: "Tokens Today",
            
            // Admin
            admin: "Admin",
            admin_panel: "Admin Panel",
            login: "Login",
            logout: "Logout",
            username: "Username",
            password: "Password",
            remember_me: "Remember Me",
            forgot_password: "Forgot Password",
            settings: "Settings",
            account_settings: "Account Settings",
            
            // Logs
            logs: "Logs",
            api_logs: "API Logs",
            endpoint: "Endpoint",
            method: "Method",
            status_code: "Status",
            response_time: "Response Time",
            client_ip: "Client IP",
            user_agent: "User Agent",
            
            // Messages
            request_failed: "Request failed",
            upload_successful: "Upload successful",
            upload_failed: "Upload failed",
            saved_successfully: "Saved successfully",
            deleted_successfully: "Deleted successfully",
            operation_successful: "Operation successful",
            operation_failed: "Operation failed",
            invalid_input: "Invalid input",
            required_field: "This field is required",
            no_data: "No data available",
            no_results: "No results found",
            confirm_delete: "Are you sure you want to delete this?",
            session_expired: "Session expired. Please login again.",
            unauthorized: "Unauthorized access",
            
            // Language
            language: "Language",
            english: "English",
            chinese: "中文",
            switch_language: "Switch Language",
            
            // Navigation
            nav_dashboard: "Dashboard",
            nav_chat: "Chat",
            nav_accounts: "Accounts",
            nav_api_keys: "API Keys",
            nav_keep_alive: "Keep Alive",
            nav_logs: "Logs",
            nav_settings: "Settings",
            
            // Chat Page
            chat_page_title: "Online Chat - Gemini Ultra Gateway",
            online_chat: "Online Chat",
            back_to_dashboard: "Back to Dashboard",
            chat_empty_state: "Start chatting! Type a message and press Enter or click Send.",
            chat_input_placeholder: "Type a message... (Shift+Enter for new line, Enter to send)",
            upload_file: "Upload File",
            pause: "Pause",
            paused: "Paused",
            no_reply: "No reply",
            thinking_process: "Thinking Process",
            confirm_clear_chat: "Are you sure you want to clear all messages?",
            file_read_failed: "File read failed",
            
            // Account Management
            account_management: "Account Management",
            back_to_keys: "Back to API Keys",
            batch_check: "Batch Check",
            auto_check: "Auto Check",
            batch_copy: "Batch Copy",
            batch_delete: "Batch Delete",
            batch_add: "Batch Add",
            add_account: "Add Account",
            index: "Index",
            name: "Name",
            last_check: "Last Check",
            operation: "Operation",
            copy: "Copy",
            check: "Check",
            default_account: "Default",
            checking: "Checking...",
            no_accounts: "No accounts, please add",
            load_failed: "Load failed, please refresh",
            important_notice: "Important Notice",
            account_notice_text: "Changes to account configuration will automatically reload, no need to restart the service. Please backup .env file before modification.",
            
            // Keep Alive
            enable_keep_alive: "Enable Keep Alive Task",
            execution_time: "Execution Time (Beijing)",
            save_settings: "Save Settings",
            execute_now: "Execute Now",
            cancel_keep_alive: "Cancel Keep Alive",
            last_execution_time: "Last Execution Time",
            last_execution_result: "Last Execution Result",
            execution_history: "Execution History",
            select_all: "Select All",
            status: "Status",
            account_count: "Account Count",
            success_fail: "Success/Fail",
            view_details: "View Details",
            log_details: "Log Details",
            
            // Account Settings
            change_username: "Change Username",
            change_password: "Change Password",
            new_username: "New Username",
            current_password: "Current Password",
            old_password: "Old Password",
            new_password: "New Password",
            confirm_password: "Confirm Password",
            username_empty: "Username cannot be empty",
            username_too_long: "Username cannot exceed 50 characters",
            password_mismatch: "Passwords do not match",
            password_too_short: "Password must be at least 6 characters",
            username_changed: "Username changed successfully, please login again",
            password_changed: "Password changed successfully, please login again",
            
            // Auto Check
            auto_check_config: "Auto Check Configuration",
            enable_auto_check: "Enable Auto Check",
            check_interval: "Check Interval",
            minutes: "minutes",
            interval_hint: "Range: 5-1440 minutes (recommended: 30-120)",
            auto_fix: "Auto fix when invalid cookies detected",
            auto_fix_hint: "When enabled, system will automatically call browser keep-alive to update expired accounts",
            feature_description: "Feature Description",
            auto_check_desc_1: "System will automatically check all account cookie status at set intervals",
            auto_check_desc_2: "When invalid cookies are detected, browser keep-alive will be called to update",
            auto_check_desc_3: "Only expired accounts will be updated, valid accounts won't be processed",
            auto_check_desc_4: "All operations are logged, viewable on keep-alive page",
            execute_immediately: "Execute Now",
            save_config: "Save Config",
            config_saved: "Configuration saved",
            
            // Bulk Operations
            bulk_add_accounts: "Bulk Add Accounts",
            format_description: "Format Description",
            format_hint: "Paste text containing account info, system will auto-detect: NAME, SECURE_C_SES, CSESIDX, CONFIG_ID, HOST_C_OSES",
            account_data: "Account Data",
            account_data_placeholder: "Enter account data, one account per line...",
            created_count: "Created",
            skipped_count: "Skipped",
            
            // Development
            in_development: "In Development",
            not_checked: "Not Checked",
            rate_limited: "Rate Limited",
            forbidden: "Forbidden",
            
            // More Keep Alive
            click_to_view_logs: "Click \"View Details\" in execution history to view logs",
            no_logs: "No logs yet",
        },
        
        zh: {
            // General
            app_name: "Gemini 超级网关",
            loading: "加载中...",
            save: "保存",
            cancel: "取消",
            delete: "删除",
            edit: "编辑",
            create: "创建",
            refresh: "刷新",
            confirm: "确认",
            close: "关闭",
            back: "返回",
            next: "下一步",
            submit: "提交",
            search: "搜索",
            filter: "筛选",
            clear: "清除",
            reset: "重置",
            yes: "是",
            no: "否",
            ok: "确定",
            error: "错误",
            success: "成功",
            warning: "警告",
            info: "信息",
            
            // Status
            valid: "有效",
            invalid: "无效",
            unknown: "未知",
            active: "活跃",
            inactive: "不活跃",
            enabled: "已启用",
            disabled: "已禁用",
            online: "在线",
            offline: "离线",
            available: "可用",
            unavailable: "不可用",
            expired: "已过期",
            pending: "等待中",
            running: "运行中",
            completed: "已完成",
            failed: "失败",
            cancelled: "已取消",
            
            // Time
            never_executed: "从未执行",
            last_run: "上次运行",
            last_used: "上次使用",
            created_at: "创建时间",
            updated_at: "更新时间",
            expires_at: "过期时间",
            start_time: "开始时间",
            end_time: "结束时间",
            duration: "持续时间",
            
            // Account
            account: "账号",
            accounts: "账号管理",
            account_name: "账号名称",
            account_status: "账号状态",
            cookie_status: "Cookie 状态",
            remaining_cooldown: "剩余冷却",
            fail_count: "失败次数",
            last_error: "最后错误",
            reset_cooldown: "重置冷却",
            check_cookie: "检查 Cookie",
            refresh_cookie: "刷新 Cookie",
            
            // API Keys
            api_key: "API 密钥",
            api_keys: "API 密钥",
            create_api_key: "创建密钥",
            key_name: "密钥名称",
            key_prefix: "密钥前缀",
            rate_limit: "速率限制",
            requests_per_minute: "请求/分钟",
            requests_per_day: "请求/天",
            total_requests: "总请求数",
            copy_key: "复制密钥",
            key_copied: "密钥已复制",
            key_warning: "请保存此密钥！只显示一次。",
            never_expires: "永不过期",
            
            // Chat
            chat: "聊天",
            message: "消息",
            send: "发送",
            clear_chat: "清除聊天",
            new_conversation: "新对话",
            conversation_history: "对话历史",
            model: "模型",
            temperature: "温度",
            max_tokens: "最大令牌",
            streaming: "流式输出",
            
            // Media
            image: "图片",
            images: "图片",
            video: "视频",
            videos: "视频",
            generate_image: "生成图片",
            generate_video: "生成视频",
            upload_image: "上传图片",
            upload_video: "上传视频",
            download: "下载",
            preview: "预览",
            prompt: "提示词",
            style: "风格",
            aspect_ratio: "宽高比",
            quality: "质量",
            duration_seconds: "时长（秒）",
            
            // Keep Alive
            keep_alive: "保活",
            keep_alive_tasks: "保活任务",
            create_task: "创建任务",
            task_name: "任务名称",
            cron_expression: "Cron 表达式",
            run_now: "立即运行",
            stop_task: "停止",
            task_logs: "任务日志",
            execution_history: "执行历史",
            
            // Dashboard
            dashboard: "仪表盘",
            overview: "概览",
            statistics: "统计",
            total_accounts: "总账号数",
            available_accounts: "可用账号",
            total_api_keys: "总密钥数",
            active_api_keys: "活跃密钥",
            requests_today: "今日请求",
            tokens_today: "今日令牌",
            
            // Admin
            admin: "管理员",
            admin_panel: "管理面板",
            login: "登录",
            logout: "退出",
            username: "用户名",
            password: "密码",
            remember_me: "记住我",
            forgot_password: "忘记密码",
            settings: "设置",
            account_settings: "账号设置",
            
            // Logs
            logs: "日志",
            api_logs: "API 日志",
            endpoint: "端点",
            method: "方法",
            status_code: "状态码",
            response_time: "响应时间",
            client_ip: "客户端 IP",
            user_agent: "用户代理",
            
            // Messages
            request_failed: "请求失败",
            upload_successful: "上传成功",
            upload_failed: "上传失败",
            saved_successfully: "保存成功",
            deleted_successfully: "删除成功",
            operation_successful: "操作成功",
            operation_failed: "操作失败",
            invalid_input: "输入无效",
            required_field: "必填项",
            no_data: "暂无数据",
            no_results: "未找到结果",
            confirm_delete: "确定要删除吗？",
            session_expired: "会话已过期，请重新登录",
            unauthorized: "未授权访问",
            
            // Language
            language: "语言",
            english: "English",
            chinese: "中文",
            switch_language: "切换语言",
            
            // Navigation
            nav_dashboard: "仪表盘",
            nav_chat: "聊天",
            nav_accounts: "账号",
            nav_api_keys: "API 密钥",
            nav_keep_alive: "保活",
            nav_logs: "日志",
            nav_settings: "设置",
            
            // Chat Page
            chat_page_title: "在线对话 - Gemini 超级网关",
            online_chat: "在线对话",
            back_to_dashboard: "返回管理",
            chat_empty_state: "开始对话吧！输入消息后按 Enter 或点击发送按钮。",
            chat_input_placeholder: "输入消息... (Shift+Enter 换行，Enter 发送)",
            upload_file: "上传文件",
            pause: "暂停",
            paused: "已暂停",
            no_reply: "暂无回复",
            thinking_process: "思考过程",
            confirm_clear_chat: "确定要清空所有对话吗？",
            file_read_failed: "文件读取失败",
            
            // Account Management
            account_management: "账号管理",
            back_to_keys: "返回密钥管理",
            batch_check: "批量检查",
            auto_check: "自动检查",
            batch_copy: "批量复制",
            batch_delete: "批量删除",
            batch_add: "批量添加",
            add_account: "添加账号",
            index: "索引",
            name: "名称",
            last_check: "最后检查",
            operation: "操作",
            copy: "复制",
            check: "检查",
            default_account: "默认",
            checking: "检查中...",
            no_accounts: "暂无账号，请添加",
            load_failed: "加载失败，请刷新重试",
            important_notice: "重要提示",
            account_notice_text: "修改账号配置后会自动重新加载，无需重启服务。请确保在修改前备份 .env 文件。",
            
            // Keep Alive
            enable_keep_alive: "启用保活任务",
            execution_time: "执行时间（北京时间）",
            save_settings: "保存设置",
            execute_now: "立即执行",
            cancel_keep_alive: "中断保活",
            last_execution_time: "上次执行时间",
            last_execution_result: "上次执行结果",
            execution_history: "执行历史",
            select_all: "全选",
            status: "状态",
            account_count: "账号数",
            success_fail: "成功/失败",
            view_details: "查看详情",
            log_details: "日志详情",
            
            // Account Settings
            change_username: "修改用户名",
            change_password: "修改密码",
            new_username: "新用户名",
            current_password: "当前密码",
            old_password: "当前密码",
            new_password: "新密码",
            confirm_password: "确认新密码",
            username_empty: "用户名不能为空",
            username_too_long: "用户名长度不能超过 50 个字符",
            password_mismatch: "新密码和确认密码不一致，请重新输入",
            password_too_short: "新密码长度至少为 6 位",
            username_changed: "用户名修改成功，请使用新用户名重新登录",
            password_changed: "密码修改成功，请使用新密码重新登录",
            
            // Auto Check
            auto_check_config: "自动检查配置",
            enable_auto_check: "启用自动检查",
            check_interval: "检查间隔",
            minutes: "分钟",
            interval_hint: "范围：5-1440 分钟（建议 30-120 分钟）",
            auto_fix: "检测到无效 Cookie 时自动修复",
            auto_fix_hint: "启用后，系统会自动调用浏览器保活来更新失效的账号",
            feature_description: "功能说明",
            auto_check_desc_1: "系统会按设定间隔自动检查所有账号的 Cookie 状态",
            auto_check_desc_2: "检测到无效 Cookie 时，会自动调用浏览器保活来更新",
            auto_check_desc_3: "只有失效的账号会被更新，有效的账号不会处理",
            auto_check_desc_4: "所有操作都会记录在日志中，可在保活页面查看",
            execute_immediately: "立即执行",
            save_config: "保存配置",
            config_saved: "配置已保存",
            
            // Bulk Operations
            bulk_add_accounts: "批量添加账号",
            format_description: "格式说明",
            format_hint: "请粘贴包含账号信息的文本，系统会自动识别：NAME、SECURE_C_SES、CSESIDX、CONFIG_ID、HOST_C_OSES",
            account_data: "账号数据",
            account_data_placeholder: "请输入账号数据，每行一个账号...",
            created_count: "成功创建",
            skipped_count: "跳过",
            
            // Development
            in_development: "开发中",
            not_checked: "未检查",
            rate_limited: "限流",
            forbidden: "被禁止",
            
            // More Keep Alive
            click_to_view_logs: "点击执行历史中的\"查看详情\"查看日志",
            no_logs: "暂无日志",
        }
    },
    
    /**
     * Get translation for a key
     * @param {string} key - Translation key
     * @returns {string} - Translated text
     */
    t(key) {
        const lang = this.currentLang;
        return this.translations[lang]?.[key] || this.translations['en']?.[key] || key;
    },
    
    /**
     * Set current language
     * @param {string} lang - Language code ('en' or 'zh')
     */
    setLanguage(lang) {
        if (this.translations[lang]) {
            this.currentLang = lang;
            localStorage.setItem('language', lang);
            this.updatePage();
            return true;
        }
        return false;
    },
    
    /**
     * Toggle between languages
     */
    toggleLanguage() {
        const newLang = this.currentLang === 'en' ? 'zh' : 'en';
        this.setLanguage(newLang);
    },
    
    /**
     * Get current language
     * @returns {string} - Current language code
     */
    getLanguage() {
        return this.currentLang;
    },
    
    /**
     * Update all elements with data-i18n attribute
     */
    updatePage() {
        // Update text content
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            el.textContent = this.t(key);
        });
        
        // Update placeholders
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            el.placeholder = this.t(key);
        });
        
        // Update titles
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            el.title = this.t(key);
        });
        
        // Update document title if set
        const titleKey = document.querySelector('title[data-i18n]')?.getAttribute('data-i18n');
        if (titleKey) {
            document.title = this.t(titleKey);
        }
        
        // Update html lang attribute
        document.documentElement.lang = this.currentLang === 'zh' ? 'zh-CN' : 'en';
        
        // Dispatch event for custom handlers
        window.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: this.currentLang } }));
    },
    
    /**
     * Format date according to current language
     * @param {string|Date} dateString - Date to format
     * @param {object} options - Intl.DateTimeFormat options
     * @returns {string} - Formatted date
     */
    formatDate(dateString, options = {}) {
        if (!dateString) return this.t('unknown');
        
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return this.t('invalid');
        
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            ...options
        };
        
        const locale = this.currentLang === 'zh' ? 'zh-CN' : 'en-US';
        return date.toLocaleString(locale, defaultOptions);
    },
    
    /**
     * Format number according to current language
     * @param {number} num - Number to format
     * @returns {string} - Formatted number
     */
    formatNumber(num) {
        if (num === null || num === undefined) return '0';
        const locale = this.currentLang === 'zh' ? 'zh-CN' : 'en-US';
        return num.toLocaleString(locale);
    },
    
    /**
     * Initialize i18n on page load
     */
    init() {
        // Set initial language from localStorage or default
        const savedLang = localStorage.getItem('language');
        if (savedLang && this.translations[savedLang]) {
            this.currentLang = savedLang;
        }
        
        // Update page on DOM ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.updatePage());
        } else {
            this.updatePage();
        }
    }
};

// Initialize on load
I18n.init();

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = I18n;
}
