/**
 * 外卖H5应用 - 工具函数库
 */

// API配置
const API_CONFIG = {
    baseURL: 'http://localhost:8091/api/v1',
    timeout: 10000
};

// 本地存储键名
const STORAGE_KEYS = {
    ACCESS_TOKEN: 'access_token',
    REFRESH_TOKEN: 'refresh_token',
    USER_INFO: 'user_info',
    CART_DATA: 'cart_data',
    CURRENT_ADDRESS: 'current_address'
};

/**
 * HTTP请求工具类
 */
class HttpClient {
    constructor() {
        this.baseURL = API_CONFIG.baseURL;
        this.timeout = API_CONFIG.timeout;
    }

    // 获取认证头
    getAuthHeaders() {
        const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    }

    // 通用请求方法
    async request(url, options = {}) {
        const config = {
            method: 'GET',
            mode: 'cors',
            headers: {
                'Content-Type': 'application/json',
                ...this.getAuthHeaders(),
                ...options.headers
            },
            ...options
        };

        // 处理请求体
        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);
            
            const response = await fetch(`${this.baseURL}${url}`, {
                ...config,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            // 处理业务错误
            if (data.code !== '00000' && data.code !== 200) {
                throw new Error(data.info || data.message || '请求失败');
            }

            return data;
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('请求超时');
            }
            throw error;
        }
    }

    // GET请求
    async get(url, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;
        return this.request(fullUrl);
    }

    // POST请求
    async post(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            body: data
        });
    }

    // PUT请求
    async put(url, data = {}) {
        return this.request(url, {
            method: 'PUT',
            body: data
        });
    }

    // DELETE请求
    async delete(url) {
        return this.request(url, {
            method: 'DELETE'
        });
    }
}

// 创建HTTP客户端实例
const http = new HttpClient();

/**
 * 本地存储工具类
 */
class StorageUtil {
    // 设置数据
    static set(key, value) {
        try {
            const data = typeof value === 'object' ? JSON.stringify(value) : value;
            localStorage.setItem(key, data);
        } catch (error) {
            console.error('存储数据失败:', error);
        }
    }

    // 获取数据
    static get(key, defaultValue = null) {
        try {
            const data = localStorage.getItem(key);
            if (data === null) return defaultValue;
            
            // 尝试解析JSON
            try {
                return JSON.parse(data);
            } catch {
                return data;
            }
        } catch (error) {
            console.error('获取数据失败:', error);
            return defaultValue;
        }
    }

    // 删除数据
    static remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.error('删除数据失败:', error);
        }
    }

    // 清空所有数据
    static clear() {
        try {
            localStorage.clear();
        } catch (error) {
            console.error('清空数据失败:', error);
        }
    }
}

/**
 * 用户认证工具类
 */
class AuthUtil {
    // 保存登录信息
    static saveLoginInfo(data) {
        // 兼容不同的字段命名方式
        const accessToken = data.accessToken || data.access_token;
        const refreshToken = data.refreshToken || data.refresh_token;
        const userInfo = data.user || data.userInfo || data.user_info;
        
        if (accessToken) {
            StorageUtil.set(STORAGE_KEYS.ACCESS_TOKEN, accessToken);
        }
        if (refreshToken) {
            StorageUtil.set(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
        }
        if (userInfo) {
            StorageUtil.set(STORAGE_KEYS.USER_INFO, userInfo);
        }
    }

    // 获取访问令牌
    static getAccessToken() {
        return StorageUtil.get(STORAGE_KEYS.ACCESS_TOKEN);
    }

    // 获取刷新令牌
    static getRefreshToken() {
        return StorageUtil.get(STORAGE_KEYS.REFRESH_TOKEN);
    }

    // 获取用户信息
    static getUserInfo() {
        return StorageUtil.get(STORAGE_KEYS.USER_INFO);
    }

    // 检查是否已登录
    static isLoggedIn() {
        return !!this.getAccessToken();
    }

    // 退出登录
    static logout() {
        StorageUtil.remove(STORAGE_KEYS.ACCESS_TOKEN);
        StorageUtil.remove(STORAGE_KEYS.REFRESH_TOKEN);
        StorageUtil.remove(STORAGE_KEYS.USER_INFO);
    }
}

/**
 * 购物车工具类
 */
class CartUtil {
    // 获取购物车数据
    static getCartData() {
        return StorageUtil.get(STORAGE_KEYS.CART_DATA, []);
    }

    // 保存购物车数据
    static saveCartData(cartData) {
        StorageUtil.set(STORAGE_KEYS.CART_DATA, cartData);
    }

    // 添加商品到购物车
    static addToCart(product, quantity = 1) {
        const cartData = this.getCartData();
        const existingItem = cartData.find(item => item.productId === product.productId);
        
        if (existingItem) {
            existingItem.quantity += quantity;
        } else {
            cartData.push({
                productId: product.productId,
                productName: product.productName,
                productPrice: product.productPrice,
                productImage: product.productImage,
                merchantId: product.merchantId,
                merchantName: product.merchantName,
                skuId: product.skuId || product.productId, // 如果没有skuId，使用productId作为默认值
                skuName: product.skuName || product.productName, // 如果没有skuName，使用productName作为默认值
                quantity: quantity
            });
        }
        
        this.saveCartData(cartData);
        return cartData;
    }

    // 更新购物车商品数量
    static updateCartItem(productId, quantity) {
        const cartData = this.getCartData();
        const itemIndex = cartData.findIndex(item => item.productId === productId);
        
        if (itemIndex !== -1) {
            if (quantity <= 0) {
                cartData.splice(itemIndex, 1);
            } else {
                cartData[itemIndex].quantity = quantity;
            }
            this.saveCartData(cartData);
        }
        
        return cartData;
    }

    // 删除购物车商品
    static removeFromCart(productId) {
        const cartData = this.getCartData();
        const filteredData = cartData.filter(item => item.productId !== productId);
        this.saveCartData(filteredData);
        return filteredData;
    }

    // 清空购物车
    static clearCart() {
        this.saveCartData([]);
    }

    // 获取购物车商品总数
    static getCartItemCount() {
        const cartData = this.getCartData();
        return cartData.reduce((total, item) => total + item.quantity, 0);
    }

    // 获取购物车总金额
    static getCartTotalAmount() {
        const cartData = this.getCartData();
        return cartData.reduce((total, item) => total + (item.productPrice * item.quantity), 0);
    }
}

/**
 * 表单验证工具类
 */
class ValidateUtil {
    // 验证手机号
    static validatePhone(phone) {
        const phoneRegex = /^1[3-9]\d{9}$/;
        return phoneRegex.test(phone);
    }

    // 验证验证码
    static validateCode(code) {
        const codeRegex = /^\d{6}$/;
        return codeRegex.test(code);
    }

    // 验证邮箱
    static validateEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // 验证密码强度
    static validatePassword(password) {
        return password && password.length >= 6;
    }

    // 验证非空
    static validateRequired(value) {
        return value !== null && value !== undefined && value.toString().trim() !== '';
    }
}

/**
 * 格式化工具类
 */
class FormatUtil {
    // 格式化金额
    static formatMoney(amount, decimals = 2) {
        if (isNaN(amount)) return '0.00';
        return Number(amount).toFixed(decimals);
    }

    // 格式化手机号
    static formatPhone(phone) {
        if (!phone) return '';
        const phoneStr = phone.toString();
        if (phoneStr.length === 11) {
            return phoneStr.replace(/(\d{3})(\d{4})(\d{4})/, '$1****$3');
        }
        return phone;
    }

    // 格式化时间
    static formatTime(timestamp, format = 'YYYY-MM-DD HH:mm:ss') {
        if (!timestamp) return '';
        
        const date = new Date(timestamp);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        
        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes)
            .replace('ss', seconds);
    }

    // 格式化日期时间
    static formatDateTime(timestamp, format = 'YYYY-MM-DD HH:mm') {
        return this.formatTime(timestamp, format);
    }

    // 格式化相对时间
    static formatRelativeTime(timestamp) {
        if (!timestamp) return '';
        
        const now = new Date();
        const date = new Date(timestamp);
        const diff = now - date;
        
        const minutes = Math.floor(diff / (1000 * 60));
        const hours = Math.floor(diff / (1000 * 60 * 60));
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        
        if (minutes < 1) return '刚刚';
        if (minutes < 60) return `${minutes}分钟前`;
        if (hours < 24) return `${hours}小时前`;
        if (days < 7) return `${days}天前`;
        
        return this.formatTime(timestamp, 'MM-DD HH:mm');
    }

    // 截断文本
    static truncateText(text, maxLength = 50) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }
}

/**
 * UI工具类
 */
class UIUtil {
    // 显示加载状态
    static showLoading(message = '加载中...') {
        const existingLoading = document.querySelector('.global-loading');
        if (existingLoading) {
            existingLoading.remove();
        }
        
        const loading = document.createElement('div');
        loading.className = 'global-loading';
        loading.innerHTML = `
            <div class="modal">
                <div class="modal-content">
                    <div class="loading">
                        <div class="loading-spinner"></div>
                        <span>${message}</span>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(loading);
    }

    // 隐藏加载状态
    static hideLoading() {
        const loading = document.querySelector('.global-loading');
        if (loading) {
            loading.remove();
        }
    }

    // 显示提示消息
    static showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: ${type === 'success' ? '#27ae60' : type === 'error' ? '#e74c3c' : '#333'};
            color: white;
            padding: 12px 24px;
            border-radius: 6px;
            z-index: 3000;
            font-size: 14px;
            max-width: 300px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // 添加动画
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-50%) translateY(-20px)';
        
        setTimeout(() => {
            toast.style.transition = 'all 0.3s ease';
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(-50%) translateY(0)';
        }, 10);
        
        // 自动移除
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(-50%) translateY(-20px)';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, duration);
    }

    // 显示确认对话框
    static showConfirm(title, message, onConfirm, onCancel) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-title">${title}</div>
                <div class="modal-body">${message}</div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" data-action="cancel">取消</button>
                    <button class="btn btn-primary" data-action="confirm">确定</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // 绑定事件
        modal.addEventListener('click', (e) => {
            const action = e.target.dataset.action;
            if (action === 'confirm') {
                onConfirm && onConfirm();
                modal.remove();
            } else if (action === 'cancel') {
                onCancel && onCancel();
                modal.remove();
            } else if (e.target === modal) {
                onCancel && onCancel();
                modal.remove();
            }
        });
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
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

/**
 * 页面路由工具类
 */
class RouterUtil {
    // 跳转到指定页面
    static navigateTo(page, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${page}.html?${queryString}` : `${page}.html`;
        window.location.href = url;
    }

    // 返回上一页
    static goBack() {
        if (window.history.length > 1) {
            window.history.back();
        } else {
            this.navigateTo('index');
        }
    }

    // 获取URL参数
    static getUrlParams() {
        const params = new URLSearchParams(window.location.search);
        const result = {};
        for (const [key, value] of params) {
            result[key] = value;
        }
        return result;
    }

    // 获取单个URL参数
    static getUrlParam(name, defaultValue = null) {
        const params = new URLSearchParams(window.location.search);
        return params.get(name) || defaultValue;
    }
}

// 导出工具类
window.http = http;
window.StorageUtil = StorageUtil;
window.AuthUtil = AuthUtil;
window.CartUtil = CartUtil;
window.ValidateUtil = ValidateUtil;
window.FormatUtil = FormatUtil;
window.UIUtil = UIUtil;
window.RouterUtil = RouterUtil;
window.STORAGE_KEYS = STORAGE_KEYS;