// 全局配置
const API_BASE = '';

// 工具函数：获取 token
function getToken() {
    return localStorage.getItem('token');
}

// 工具函数：检查登录状态
function checkAuth() {
    const token = getToken();
    if (!token) {
        window.location.href = '/static/index.html';
        return false;
    }
    return true;
}

// 工具函数：API 请求
async function apiRequest(url, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers,
    };

    const response = await fetch(API_BASE + url, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        localStorage.removeItem('token');
        window.location.href = '/static/index.html';
        throw new Error('Authentication failed');
    }

    return response;
}

// 工具函数：兼容性复制到剪贴板
function copyToClipboard(text) {
    // 尝试使用现代API
    if (navigator.clipboard && navigator.clipboard.writeText) {
        return navigator.clipboard.writeText(text)
            .then(() => true)
            .catch(() => false);
    }

    // 降级方案：使用传统方法
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();

    try {
        const successful = document.execCommand('copy');
        document.body.removeChild(textarea);
        return Promise.resolve(successful);
    } catch (err) {
        document.body.removeChild(textarea);
        return Promise.resolve(false);
    }
}

// 工具函数：格式化日期
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
    });
}

// 工具函数：获取状态
function getKeyStatus(key) {
    if (!key.is_active) {
        return { text: '已撤销', class: 'status-inactive' };
    }
    const now = new Date();
    const expiresAt = new Date(key.expires_at);
    if (expiresAt < now) {
        return { text: '已过期', class: 'status-expired' };
    }
    return { text: '活跃', class: 'status-active' };
}

// Dashboard 页面逻辑
if (window.location.pathname.includes('dashboard.html')) {
    checkAuth();

    // 退出登录
    document.getElementById('logoutBtn').addEventListener('click', () => {
        localStorage.removeItem('token');
        window.location.href = '/static/index.html';
    });

    // 加载统计数据
    async function loadStats() {
        try {
            const response = await apiRequest('/admin/stats');
            const data = await response.json();

            document.getElementById('activeKeys').textContent = data.active_keys;
            document.getElementById('totalUsage').textContent = data.total_usage.toLocaleString();
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    // 加载密钥列表
    async function loadKeys() {
        try {
            const response = await apiRequest('/admin/api-keys');
            const keys = await response.json();

            const tbody = document.getElementById('keysTableBody');

            if (keys.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="loading">暂无密钥</td></tr>';
                document.getElementById('batchDeleteBtn').style.display = 'none';
                document.getElementById('batchCopyBtn').style.display = 'none';
                return;
            }

            tbody.innerHTML = keys.map((key, index) => {
                const status = getKeyStatus(key);
                const displayId = index + 1; // 基于当前活跃密钥数量的序号

                return `
                    <tr>
                        <td><input type="checkbox" class="key-checkbox" value="${key.id}" onchange="updateBatchDeleteBtn()"></td>
                        <td>${displayId}</td>
                        <td>${formatDate(key.created_at)}</td>
                        <td>${formatDate(key.expires_at)}</td>
                        <td><span class="status-badge ${status.class}">${status.text}</span></td>
                        <td>${key.usage_count}</td>
                        <td>${formatDate(key.last_used_at)}</td>
                        <td style="display: flex; gap: 6px;">
                            <button class="btn-info" onclick="viewKeyLogs(${key.id}, 'API Key #${displayId}')" style="padding: 6px 8px;" title="查看详情">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
                            </button>
                            <button class="btn-secondary" onclick="viewAndCopyKey(${key.id})" style="padding: 6px 8px;" title="查看复制">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                            </button>
                            <button class="btn-danger" onclick="revokeKey(${key.id})" style="padding: 6px 8px;" title="撤销">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');

            updateBatchDeleteBtn();
        } catch (error) {
            console.error('Failed to load keys:', error);
        }
    }

    // 生成密钥
    document.getElementById('generateForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const count = parseInt(document.getElementById('count').value);
        const expiresDays = parseInt(document.getElementById('expiresDays').value);
        const namePrefix = document.getElementById('namePrefix').value;

        try {
            const response = await apiRequest('/admin/api-keys', {
                method: 'POST',
                body: JSON.stringify({
                    count,
                    expires_days: expiresDays,
                    name_prefix: namePrefix,
                }),
            });

            const keys = await response.json();
            showKeysModal(keys);

            // 刷新列表和统计
            loadStats();
            loadKeys();

            // 重置表单
            e.target.reset();
            document.getElementById('count').value = 1;
            document.getElementById('expiresDays').value = 30;
            document.getElementById('namePrefix').value = 'API Key';
        } catch (error) {
            alert('生成密钥失败: ' + error.message);
        }
    });

    // 显示密钥模态框
    function showKeysModal(keys) {
        const modal = document.getElementById('keysModal');
        const keysContainer = document.getElementById('generatedKeys');

        keysContainer.innerHTML = keys.map(key => `
            <div class="key-item" onclick="copyKey('${key.key}')">
                <div class="key-name">${key.name}</div>
                <div class="key-value">${key.key}</div>
            </div>
        `).join('');

        modal.classList.add('active');

        // 保存密钥以便复制
        window.generatedKeys = keys.map(k => k.key);
    }

    // 关闭模态框
    window.closeModal = function () {
        document.getElementById('keysModal').classList.remove('active');
    };

    // 复制单个密钥
    window.copyKey = async function (key) {
        const success = await copyToClipboard(key);
        if (success) {
            alert('密钥已复制到剪贴板');
        } else {
            alert('复制失败，请手动复制:\n' + key);
        }
    };

    // 复制所有密钥
    window.copyAllKeys = async function () {
        const allKeys = window.generatedKeys.join('\n');
        const success = await copyToClipboard(allKeys);
        if (success) {
            alert('所有密钥已复制到剪贴板');
        } else {
            alert('复制失败，请手动复制:\n' + allKeys);
        }
    };

    // 查看并复制密钥
    window.viewAndCopyKey = async function (keyId) {
        try {
            const response = await apiRequest(`/admin/api-keys/${keyId}/view`);
            const data = await response.json();

            const success = await copyToClipboard(data.key);
            if (success) {
                alert(`密钥已复制到剪贴板:\n${data.key}`);
            } else {
                alert('请手动复制密钥:\n' + data.key);
            }
        } catch (error) {
            alert('获取密钥失败: ' + error.message);
        }
    };

    // 撤销密钥
    window.revokeKey = async function (keyId) {
        if (!confirm('确定要撤销这个密钥吗？此操作不可逆！')) {
            return;
        }

        try {
            await apiRequest(`/admin/api-keys/${keyId}`, {
                method: 'DELETE',
            });

            alert('密钥已撤销');
            loadStats();
            loadKeys();
        } catch (error) {
            alert('撤销失败: ' + error.message);
        }
    };

    // 全选/取消全选
    window.toggleSelectAll = function (checkbox) {
        const checkboxes = document.querySelectorAll('.key-checkbox');
        checkboxes.forEach(cb => cb.checked = checkbox.checked);
        updateBatchDeleteBtn();
    };

    // 更新批量操作按钮状态
    window.updateBatchDeleteBtn = function () {
        const checkedBoxes = document.querySelectorAll('.key-checkbox:checked');
        const deleteBtn = document.getElementById('batchDeleteBtn');
        const copyBtn = document.getElementById('batchCopyBtn');
        const selectAll = document.getElementById('selectAll');

        if (checkedBoxes.length > 0) {
            deleteBtn.style.display = 'inline-block';
            deleteBtn.textContent = `批量删除选中项 (${checkedBoxes.length})`;
            copyBtn.style.display = 'inline-block';
            copyBtn.textContent = `批量复制选中项 (${checkedBoxes.length})`;
        } else {
            deleteBtn.style.display = 'none';
            copyBtn.style.display = 'none';
            selectAll.checked = false;
        }
    };

    // 批量删除密钥
    window.batchDeleteKeys = async function () {
        const checkedBoxes = document.querySelectorAll('.key-checkbox:checked');
        const keyIds = Array.from(checkedBoxes).map(cb => cb.value);

        if (keyIds.length === 0) {
            alert('请先选择要删除的密钥');
            return;
        }

        if (!confirm(`确定要撤销选中的 ${keyIds.length} 个密钥吗？此操作不可逆！`)) {
            return;
        }

        try {
            let successCount = 0;
            let failCount = 0;

            for (const keyId of keyIds) {
                try {
                    await apiRequest(`/admin/api-keys/${keyId}`, {
                        method: 'DELETE',
                    });
                    successCount++;
                } catch (error) {
                    failCount++;
                    console.error(`Failed to delete key ${keyId}:`, error);
                }
            }

            alert(`批量删除完成：成功 ${successCount} 个，失败 ${failCount} 个`);
            loadStats();
            loadKeys();
        } catch (error) {
            alert('批量删除失败: ' + error.message);
        }
    };

    // 批量复制密钥
    window.batchCopyKeys = async function () {
        const checkedBoxes = document.querySelectorAll('.key-checkbox:checked');
        const keyIds = Array.from(checkedBoxes).map(cb => cb.value);

        if (keyIds.length === 0) {
            alert('请先选择要复制的密钥');
            return;
        }

        try {
            const keys = [];
            for (const keyId of keyIds) {
                try {
                    const response = await apiRequest(`/admin/api-keys/${keyId}/view`);
                    const data = await response.json();
                    keys.push(data.key);
                } catch (error) {
                    console.error(`Failed to get key ${keyId}:`, error);
                }
            }

            if (keys.length > 0) {
                const allKeys = keys.join('\n');
                const success = await copyToClipboard(allKeys);
                if (success) {
                    alert(`已复制 ${keys.length} 个密钥到剪贴板`);
                } else {
                    alert('请手动复制:\n' + allKeys);
                }
            } else {
                alert('未能获取任何密钥');
            }
        } catch (error) {
            alert('批量复制失败: ' + error.message);
        }
    };

    // 查看密钥调用日志
    window.viewKeyLogs = async function (keyId, keyName) {
        window.currentViewingKeyId = keyId;
        window.currentViewingKeyName = keyName;
        try {
            // 加载统计数据
            const statsResponse = await apiRequest(`/admin/api-keys/${keyId}/stats`);
            const stats = await statsResponse.json();

            // 显示统计信息
            document.getElementById('logsModalTitle').textContent = `${keyName} - 调用详情`;
            document.getElementById('statTotalCalls').textContent = stats.total_calls;
            document.getElementById('statSuccessRate').textContent = stats.success_rate + '%';
            document.getElementById('statAvgResponse').textContent = stats.avg_response_time + 'ms';
            document.getElementById('statErrorCalls').textContent = stats.error_calls;

            // 显示按模型统计
            const modelStatsContainer = document.getElementById('modelStatsContainer');
            if (stats.model_stats && stats.model_stats.length > 0) {
                modelStatsContainer.innerHTML = stats.model_stats.map(m => `
                    <div class="model-stat-item">
                        <span class="model-name">${m.model}</span>
                        <span class="model-count">${m.count} 次</span>
                        <div class="model-bar">
                            <div class="model-bar-fill" style="width: ${(m.count / stats.total_calls * 100)}%"></div>
                        </div>
                    </div>
                `).join('');
            } else {
                modelStatsContainer.innerHTML = '<p class="no-data">暂无数据</p>';
            }

            // 显示每日趋势图
            renderDailyChart(stats.daily_stats);

            // 加载调用日志
            await loadKeyLogs(keyId, 1);

            // 显示模态框
            document.getElementById('logsModal').classList.add('active');
        } catch (error) {
            alert('加载调用详情失败: ' + error.message);
        }
    };

    // 加载调用日志
    async function loadKeyLogs(keyId, page = 1) {
        try {
            const response = await apiRequest(`/admin/api-keys/${keyId}/logs?page=${page}&page_size=20`);
            const data = await response.json();

            const tbody = document.getElementById('logsTableBody');

            if (data.logs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="loading">暂无调用记录</td></tr>';
                document.getElementById('logsPagination').innerHTML = '';
                return;
            }

            tbody.innerHTML = data.logs.map(log => {
                const statusClass = log.status === 'success' ? 'status-active' : 'status-inactive';
                const statusIcon = log.status === 'success' 
                    ? '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px"><polyline points="20 6 9 17 4 12"></polyline></svg>' 
                    : '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
                const statusText = log.status === 'success' ? '成功' : '失败';

                return `
                    <tr>
                        <td>${formatDate(log.timestamp)}</td>
                        <td><code>${log.model || '-'}</code></td>
                        <td><span class="status-badge ${statusClass}">${statusIcon}${statusText}</span></td>
                        <td>${log.response_time ? log.response_time + 'ms' : '-'}</td>
                        <td>${log.ip_address || '-'}</td>
                        <td><code>${log.endpoint || '-'}</code></td>
                    </tr>
                `;
            }).join('');

            // 渲染分页
            renderPagination(keyId, data.page, Math.ceil(data.total / data.page_size));
        } catch (error) {
            console.error('Failed to load logs:', error);
        }
    }

    // 渲染分页
    function renderPagination(keyId, currentPage, totalPages) {
        const pagination = document.getElementById('logsPagination');

        if (totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }

        let html = '<div class="pagination-buttons">';

        // 上一页
        if (currentPage > 1) {
            html += `<button class="btn-page" onclick="loadKeyLogs(${keyId}, ${currentPage - 1})">« 上一页</button>`;
        }

        // 页码
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);

        if (startPage > 1) {
            html += `<button class="btn-page" onclick="loadKeyLogs(${keyId}, 1)">1</button>`;
            if (startPage > 2) html += '<span class="pagination-ellipsis">...</span>';
        }

        for (let i = startPage; i <= endPage; i++) {
            const activeClass = i === currentPage ? 'active' : '';
            html += `<button class="btn-page ${activeClass}" onclick="loadKeyLogs(${keyId}, ${i})">${i}</button>`;
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) html += '<span class="pagination-ellipsis">...</span>';
            html += `<button class="btn-page" onclick="loadKeyLogs(${keyId}, ${totalPages})">${totalPages}</button>`;
        }

        // 下一页
        if (currentPage < totalPages) {
            html += `<button class="btn-page" onclick="loadKeyLogs(${keyId}, ${currentPage + 1})">下一页 »</button>`;
        }

        html += '</div>';
        pagination.innerHTML = html;
    }

    // 渲染每日趋势图（简单的条形图）
    function renderDailyChart(dailyStats) {
        const chartContainer = document.getElementById('dailyStatsChart');

        if (!dailyStats || dailyStats.length === 0) {
            chartContainer.innerHTML = '<p class="no-data">暂无数据</p>';
            return;
        }

        const maxCount = Math.max(...dailyStats.map(d => d.count));

        chartContainer.innerHTML = dailyStats.map(stat => {
            const height = maxCount > 0 ? (stat.count / maxCount * 100) : 0;
            return `
                <div class="chart-bar-wrapper">
                    <div class="chart-bar" style="height: ${height}%">
                        <span class="chart-value">${stat.count}</span>
                    </div>
                    <div class="chart-label">${formatShortDate(stat.date)}</div>
                </div>
            `;
        }).join('');
    }

    // 格式化短日期
    function formatShortDate(dateString) {
        const date = new Date(dateString);
        return (date.getMonth() + 1) + '/' + date.getDate();
    }

    // 关闭调用日志模态框
    window.closeLogsModal = function () {
        document.getElementById('logsModal').classList.remove('active');
        window.currentViewingKeyId = null;
        window.currentViewingKeyName = null;
    };

    // 点击模态框外部关闭
    document.getElementById('keysModal').addEventListener('click', (e) => {
        if (e.target.id === 'keysModal') {
            closeModal();
        }
    });

    document.getElementById('logsModal').addEventListener('click', (e) => {
        if (e.target.id === 'logsModal') {
            closeLogsModal();
        }
    });

    // 初始加载
    loadStats();
    loadKeys();

    // 定时刷新统计（每30秒）
    // setInterval(loadStats, 30000);

    // WebSocket 实时刷新
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.host}/ws/admin/events`);

        ws.onmessage = function (event) {
            if (event.data === 'update') {
                loadStats();
                // 只有在没有复选框被选中的情况下才刷新列表，以免打断用户操作
                const checkedBoxes = document.querySelectorAll('.key-checkbox:checked');
                if (checkedBoxes.length === 0) {
                    loadKeys();
                } else {
                    // 如果有选中的，可以考虑只更新数据但不重新渲染整个表格，或者暂时忽略
                    // 为了简单，这里选择如果用户正在操作就不刷新列表，以免丢失选中状态
                    console.log('User is interacting with list, skipping list refresh');
                }
                
                // 如果日志模态框打开，刷新日志
                if (document.getElementById('logsModal').classList.contains('active')) {
                    const title = document.getElementById('logsModalTitle').textContent;
                    // 从标题尝试反推 keyId 或从其他地方获取，这里简化处理：
                    // 由于目前没有全局保存当前查看的 keyId，暂时无法自动刷新日志列表
                    // 可以考虑将 currentKeyId 保存到 window 对象
                    if (window.currentViewingKeyId) {
                        viewKeyLogs(window.currentViewingKeyId, window.currentViewingKeyName);
                    }
                }
            }
        };

        ws.onclose = function () {
            // 断线重连
            setTimeout(connectWebSocket, 5000);
        };
        
        ws.onerror = function (err) {
            console.error('WebSocket error:', err);
            ws.close();
        };
    }
    
    connectWebSocket();
}
