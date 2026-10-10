// 商家端工具函数库

// API 基础配置
const API_CONFIG = {
    baseURL: '/api',
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json'
    }
};

// HTTP 请求工具类
class HttpClient {
    constructor(config = {}) {
        this.config = { ...API_CONFIG, ...config };
    }

    // 获取请求头
    getHeaders() {
        const headers = { ...this.config.headers };
        const token = localStorage.getItem('merchantToken');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    }

    // 处理响应
    async handleResponse(response) {
        if (!response.ok) {
            if (response.status === 401) {
                // 未授权，清除登录状态并跳转到登录页
                this.clearAuth();
                window.location.href = 'login.html';
                throw new Error('登录已过期，请重新登录');
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        }
        return await response.text();
    }

    // 处理错误
    handleError(error) {
        console.error('HTTP请求错误:', error);
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            throw new Error('网络连接失败，请检查网络设置');
        }
        throw error;
    }

    // GET 请求
    async get(url, params = {}) {
        try {
            const queryString = new URLSearchParams(params).toString();
            const fullUrl = `${this.config.baseURL}${url}${queryString ? '?' + queryString : ''}`;
            
            const response = await fetch(fullUrl, {
                method: 'GET',
                headers: this.getHeaders(),
                signal: AbortSignal.timeout(this.config.timeout)
            });

            return await this.handleResponse(response);
        } catch (error) {
            this.handleError(error);
        }
    }

    // POST 请求
    async post(url, data = {}) {
        try {
            const response = await fetch(`${this.config.baseURL}${url}`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(data),
                signal: AbortSignal.timeout(this.config.timeout)
            });

            return await this.handleResponse(response);
        } catch (error) {
            this.handleError(error);
        }
    }

    // PUT 请求
    async put(url, data = {}) {
        try {
            const response = await fetch(`${this.config.baseURL}${url}`, {
                method: 'PUT',
                headers: this.getHeaders(),
                body: JSON.stringify(data),
                signal: AbortSignal.timeout(this.config.timeout)
            });

            return await this.handleResponse(response);
        } catch (error) {
            this.handleError(error);
        }
    }

    // DELETE 请求
    async delete(url) {
        try {
            const response = await fetch(`${this.config.baseURL}${url}`, {
                method: 'DELETE',
                headers: this.getHeaders(),
                signal: AbortSignal.timeout(this.config.timeout)
            });

            return await this.handleResponse(response);
        } catch (error) {
            this.handleError(error);
        }
    }

    // 文件上传
    async upload(url, file, onProgress = null) {
        try {
            const formData = new FormData();
            formData.append('file', file);

            const headers = this.getHeaders();
            delete headers['Content-Type']; // 让浏览器自动设置

            const xhr = new XMLHttpRequest();
            
            return new Promise((resolve, reject) => {
                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable && onProgress) {
                        const percentComplete = (e.loaded / e.total) * 100;
                        onProgress(percentComplete);
                    }
                });

                xhr.addEventListener('load', () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        try {
                            const response = JSON.parse(xhr.responseText);
                            resolve(response);
                        } catch (e) {
                            resolve(xhr.responseText);
                        }
                    } else {
                        reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                    }
                });

                xhr.addEventListener('error', () => {
                    reject(new Error('上传失败'));
                });

                xhr.open('POST', `${this.config.baseURL}${url}`);
                
                // 设置请求头
                Object.keys(headers).forEach(key => {
                    xhr.setRequestHeader(key, headers[key]);
                });

                xhr.send(formData);
            });
        } catch (error) {
            this.handleError(error);
        }
    }

    // 清除认证信息
    clearAuth() {
        localStorage.removeItem('merchantToken');
        localStorage.removeItem('merchantInfo');
    }
}

// 创建全局 HTTP 客户端实例
const http = new HttpClient();

// API 服务类
class ApiService {
    // 商家相关 API
    static merchant = {
        // 登录
        login: (credentials) => http.post('/merchant/login', credentials),
        
        // 获取当前商家信息
        getCurrentInfo: () => http.get('/merchant/current'),
        
        // 更新商家信息
        updateInfo: (data) => http.put('/merchant/info', data),
        
        // 更新商家状态
        updateStatus: (status) => http.put('/merchant/status', { status }),
        
        // 上传商家头像
        uploadAvatar: (file, onProgress) => http.upload('/merchant/avatar', file, onProgress)
    };

    // 菜品相关 API
    static product = {
        // 获取商家菜品列表
        getList: (params) => http.get('/product/merchant', params),
        
        // 创建菜品
        create: (data) => http.post('/product', data),
        
        // 获取菜品详情
        getDetail: (id) => http.get(`/product/${id}`),
        
        // 更新菜品
        update: (id, data) => http.put(`/product/${id}`, data),
        
        // 删除菜品
        delete: (id) => http.delete(`/product/${id}`),
        
        // 更新菜品状态
        updateStatus: (id, status) => http.put(`/product/${id}/status`, { status }),
        
        // 更新菜品库存
        updateStock: (id, stock) => http.put(`/product/${id}/stock`, { stock }),
        
        // 上传菜品图片
        uploadImage: (file, onProgress) => http.upload('/product/image', file, onProgress)
    };

    // 菜品分类相关 API
    static category = {
        // 获取分类列表
        getList: () => http.get('/product/categories'),
        
        // 创建分类
        create: (data) => http.post('/product/category', data),
        
        // 更新分类
        update: (id, data) => http.put(`/product/category/${id}`, data),
        
        // 删除分类
        delete: (id) => http.delete(`/product/category/${id}`)
    };

    // 订单相关 API
    static order = {
        // 获取商家订单列表
        getList: (params) => http.get('/order/merchant', params),
        
        // 获取订单详情
        getDetail: (id) => http.get(`/order/${id}`),
        
        // 更新订单状态
        updateStatus: (id, status) => http.put(`/order/${id}/status`, { status }),
        
        // 取消订单
        cancel: (id, reason) => http.put(`/order/${id}/cancel`, { reason })
    };

    // 统计相关 API
    static stats = {
        // 获取概览数据
        getOverview: () => http.get('/stats/overview'),
        
        // 获取销售数据
        getSales: (params) => http.get('/stats/sales', params),
        
        // 获取订单统计
        getOrders: (params) => http.get('/stats/orders', params),
        
        // 获取热销商品
        getTopProducts: (params) => http.get('/stats/top-products', params),
        
        // 获取最近订单
        getRecentOrders: (params) => http.get('/stats/recent-orders', params),
        
        // 获取营业额趋势
        getRevenueTrend: (params) => http.get('/stats/revenue-trend', params),
        
        // 获取订单状态分布
        getOrderStatusDistribution: (params) => http.get('/stats/order-status', params)
    };
}

// 工具函数
class Utils {
    // 格式化金额
    static formatMoney(amount, currency = '¥') {
        if (amount == null || isNaN(amount)) return `${currency}0.00`;
        return `${currency}${Number(amount).toFixed(2)}`;
    }

    // 格式化日期
    static formatDate(date, format = 'YYYY-MM-DD HH:mm:ss') {
        if (!date) return '';
        
        const d = new Date(date);
        if (isNaN(d.getTime())) return '';

        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const hours = String(d.getHours()).padStart(2, '0');
        const minutes = String(d.getMinutes()).padStart(2, '0');
        const seconds = String(d.getSeconds()).padStart(2, '0');

        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes)
            .replace('ss', seconds);
    }

    // 格式化相对时间
    static formatRelativeTime(date) {
        if (!date) return '';
        
        const now = new Date();
        const target = new Date(date);
        const diff = now - target;
        
        const minute = 60 * 1000;
        const hour = 60 * minute;
        const day = 24 * hour;
        
        if (diff < minute) {
            return '刚刚';
        } else if (diff < hour) {
            return `${Math.floor(diff / minute)}分钟前`;
        } else if (diff < day) {
            return `${Math.floor(diff / hour)}小时前`;
        } else if (diff < 7 * day) {
            return `${Math.floor(diff / day)}天前`;
        } else {
            return this.formatDate(date, 'MM-DD HH:mm');
        }
    }

    // 防抖函数
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // 节流函数
    static throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    // 深拷贝
    static deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj.getTime());
        if (obj instanceof Array) return obj.map(item => this.deepClone(item));
        if (typeof obj === 'object') {
            const clonedObj = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    clonedObj[key] = this.deepClone(obj[key]);
                }
            }
            return clonedObj;
        }
    }

    // 生成唯一ID
    static generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    // 验证手机号
    static validatePhone(phone) {
        const phoneRegex = /^1[3-9]\d{9}$/;
        return phoneRegex.test(phone);
    }

    // 验证邮箱
    static validateEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // 获取文件大小描述
    static formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // 获取图片预览URL
    static getImagePreviewUrl(file) {
        return new Promise((resolve, reject) => {
            if (!file || !file.type.startsWith('image/')) {
                reject(new Error('不是有效的图片文件'));
                return;
            }
            
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = () => reject(new Error('读取文件失败'));
            reader.readAsDataURL(file);
        });
    }

    // 下载文件
    static downloadFile(url, filename) {
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // 复制到剪贴板
    static async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            // 降级方案
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            const success = document.execCommand('copy');
            document.body.removeChild(textArea);
            return success;
        }
    }

    // 获取URL参数
    static getUrlParams() {
        const params = {};
        const urlSearchParams = new URLSearchParams(window.location.search);
        for (const [key, value] of urlSearchParams) {
            params[key] = value;
        }
        return params;
    }

    // 设置URL参数
    static setUrlParams(params) {
        const url = new URL(window.location);
        Object.keys(params).forEach(key => {
            if (params[key] != null) {
                url.searchParams.set(key, params[key]);
            } else {
                url.searchParams.delete(key);
            }
        });
        window.history.replaceState({}, '', url);
    }

    // 本地存储封装
    static storage = {
        set(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
            } catch (e) {
                console.error('存储数据失败:', e);
            }
        },
        
        get(key, defaultValue = null) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch (e) {
                console.error('读取数据失败:', e);
                return defaultValue;
            }
        },
        
        remove(key) {
            try {
                localStorage.removeItem(key);
            } catch (e) {
                console.error('删除数据失败:', e);
            }
        },
        
        clear() {
            try {
                localStorage.clear();
            } catch (e) {
                console.error('清空数据失败:', e);
            }
        }
    };
}

// 消息提示工具
class Message {
    static show(text, type = 'info', duration = 3000) {
        const messageEl = document.createElement('div');
        messageEl.className = `message message-${type}`;
        messageEl.innerHTML = `
            <div class="message-content">
                <span class="message-icon">${this.getIcon(type)}</span>
                <span class="message-text">${text}</span>
            </div>
        `;

        // 添加样式
        if (!document.getElementById('message-styles')) {
            const styles = document.createElement('style');
            styles.id = 'message-styles';
            styles.textContent = `
                .message {
                    position: fixed;
                    top: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    z-index: 9999;
                    padding: 12px 20px;
                    border-radius: 6px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    animation: messageSlideDown 0.3s ease-out;
                }
                .message-content {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 14px;
                    font-weight: 500;
                }
                .message-success {
                    background: var(--success-light);
                    color: var(--success-color);
                    border: 1px solid rgba(6, 199, 85, 0.2);
                }
                .message-error {
                    background: var(--danger-light);
                    color: var(--danger-color);
                    border: 1px solid rgba(255, 23, 68, 0.2);
                }
                .message-warning {
                    background: var(--warning-light);
                    color: var(--warning-color);
                    border: 1px solid rgba(255, 102, 0, 0.2);
                }
                .message-info {
                    background: var(--info-light);
                    color: var(--info-color);
                    border: 1px solid rgba(25, 118, 210, 0.2);
                }
                @keyframes messageSlideDown {
                    from {
                        opacity: 0;
                        transform: translateX(-50%) translateY(-20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateX(-50%) translateY(0);
                    }
                }
                @keyframes messageSlideUp {
                    from {
                        opacity: 1;
                        transform: translateX(-50%) translateY(0);
                    }
                    to {
                        opacity: 0;
                        transform: translateX(-50%) translateY(-20px);
                    }
                }
            `;
            document.head.appendChild(styles);
        }

        document.body.appendChild(messageEl);

        // 自动移除
        setTimeout(() => {
            messageEl.style.animation = 'messageSlideUp 0.3s ease-out';
            setTimeout(() => {
                if (messageEl.parentNode) {
                    messageEl.parentNode.removeChild(messageEl);
                }
            }, 300);
        }, duration);
    }

    static getIcon(type) {
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        return icons[type] || icons.info;
    }

    static success(text, duration) {
        this.show(text, 'success', duration);
    }

    static error(text, duration) {
        this.show(text, 'error', duration);
    }

    static warning(text, duration) {
        this.show(text, 'warning', duration);
    }

    static info(text, duration) {
        this.show(text, 'info', duration);
    }
}

// 确认对话框
class Confirm {
    static show(options = {}) {
        const {
            title = '确认',
            message = '确定要执行此操作吗？',
            confirmText = '确定',
            cancelText = '取消',
            type = 'warning'
        } = options;

        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'confirm-overlay';
            overlay.innerHTML = `
                <div class="confirm-dialog">
                    <div class="confirm-header">
                        <span class="confirm-icon">${this.getIcon(type)}</span>
                        <h3 class="confirm-title">${title}</h3>
                    </div>
                    <div class="confirm-body">
                        <p class="confirm-message">${message}</p>
                    </div>
                    <div class="confirm-footer">
                        <button class="btn btn-outline confirm-cancel">${cancelText}</button>
                        <button class="btn btn-${type} confirm-ok">${confirmText}</button>
                    </div>
                </div>
            `;

            // 添加样式
            if (!document.getElementById('confirm-styles')) {
                const styles = document.createElement('style');
                styles.id = 'confirm-styles';
                styles.textContent = `
                    .confirm-overlay {
                        position: fixed;
                        top: 0;
                        left: 0;
                        right: 0;
                        bottom: 0;
                        background: rgba(0, 0, 0, 0.5);
                        z-index: 9999;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        animation: fadeIn 0.3s ease-out;
                    }
                    .confirm-dialog {
                        background: var(--white);
                        border-radius: 8px;
                        box-shadow: 0 8px 32px rgba(0,0,0,0.2);
                        max-width: 400px;
                        width: 90%;
                        animation: slideUp 0.3s ease-out;
                    }
                    .confirm-header {
                        padding: 20px 20px 0;
                        display: flex;
                        align-items: center;
                        gap: 12px;
                    }
                    .confirm-icon {
                        font-size: 24px;
                    }
                    .confirm-title {
                        font-size: 18px;
                        font-weight: 600;
                        margin: 0;
                        color: var(--text-primary);
                    }
                    .confirm-body {
                        padding: 16px 20px;
                    }
                    .confirm-message {
                        margin: 0;
                        color: var(--text-secondary);
                        line-height: 1.5;
                    }
                    .confirm-footer {
                        padding: 0 20px 20px;
                        display: flex;
                        gap: 12px;
                        justify-content: flex-end;
                    }
                `;
                document.head.appendChild(styles);
            }

            // 绑定事件
            const cancelBtn = overlay.querySelector('.confirm-cancel');
            const okBtn = overlay.querySelector('.confirm-ok');

            const close = (result) => {
                overlay.style.animation = 'fadeOut 0.3s ease-out';
                setTimeout(() => {
                    if (overlay.parentNode) {
                        overlay.parentNode.removeChild(overlay);
                    }
                }, 300);
                resolve(result);
            };

            cancelBtn.addEventListener('click', () => close(false));
            okBtn.addEventListener('click', () => close(true));
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) close(false);
            });

            document.body.appendChild(overlay);
        });
    }

    static getIcon(type) {
        const icons = {
            warning: '⚠️',
            danger: '🚨',
            info: 'ℹ️',
            success: '✅'
        };
        return icons[type] || icons.warning;
    }
}

// 导出到全局
window.ApiService = ApiService;
window.Utils = Utils;
window.Message = Message;
window.Confirm = Confirm;
window.http = http;

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', () => {
    // 检查登录状态
    const token = localStorage.getItem('merchantToken');
    const currentPage = window.location.pathname.split('/').pop();
    
    if (!token && currentPage !== 'login.html') {
        window.location.href = 'login.html';
        return;
    }
    
    if (token && currentPage === 'login.html') {
        window.location.href = 'index.html';
        return;
    }
});