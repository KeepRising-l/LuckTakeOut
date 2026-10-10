/**
 * 骑手端API接口封装
 * 基于后端DeliveryController提供的接口
 */

// API基础配置
const API_CONFIG = {
    baseURL: 'http://localhost:8091/api/v1/delivery',
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
};

// 当前骑手ID（实际项目中应该从登录状态获取）
let CURRENT_RIDER_ID = 1001;

/**
 * HTTP请求封装
 */
class HttpClient {
    static async request(url, options = {}) {
        const config = {
            method: 'GET',
            headers: { ...API_CONFIG.headers },
            ...options
        };

        try {
            const response = await fetch(`${API_CONFIG.baseURL}${url}`, config);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // 检查业务状态码
            if (data.code !== '00000') {
                throw new Error(data.info || '请求失败');
            }
            
            return data;
        } catch (error) {
            console.error('API请求失败:', error);
            throw error;
        }
    }

    static async get(url, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;
        return this.request(fullUrl);
    }

    static async post(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async put(url, data = {}) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    static async delete(url) {
        return this.request(url, {
            method: 'DELETE'
        });
    }
}

/**
 * 骑手相关API
 */
class RiderAPI {
    /**
     * 获取骑手信息
     * @param {number} riderId 骑手ID
     */
    static async getRiderInfo(riderId = CURRENT_RIDER_ID) {
        return HttpClient.get(`/riders/${riderId}`);
    }

    /**
     * 更新骑手工作状态
     * @param {number} riderId 骑手ID
     * @param {number} workStatus 工作状态 1-在线 3-离线 4-休息
     */
    static async updateWorkStatus(riderId = CURRENT_RIDER_ID, workStatus) {
        return HttpClient.post(`/riders/${riderId}/status?workStatus=${workStatus}`);
    }

    /**
     * 更新骑手位置
     * @param {number} riderId 骑手ID
     * @param {string} location 位置坐标 "经度,纬度"
     */
    static async updateLocation(riderId = CURRENT_RIDER_ID, location) {
        return HttpClient.post(`/riders/${riderId}/location?location=${encodeURIComponent(location)}`);
    }

    /**
     * 获取骑手配送任务列表
     * @param {number} riderId 骑手ID
     * @param {number} status 任务状态（可选）
     * @param {number} pageNum 页码
     * @param {number} pageSize 每页大小
     */
    static async getDeliveryTasks(riderId = CURRENT_RIDER_ID, status = null, pageNum = 1, pageSize = 10) {
        const params = { pageNum, pageSize };
        if (status !== null) {
            params.status = status;
        }
        return HttpClient.get(`/riders/${riderId}/tasks`, params);
    }
}

/**
 * 配送任务相关API
 */
class DeliveryTaskAPI {
    /**
     * 获取配送任务详情
     * @param {number} taskId 任务ID
     */
    static async getTaskDetail(taskId) {
        return HttpClient.get(`/tasks/${taskId}`);
    }

    /**
     * 接受配送任务
     * @param {number} taskId 任务ID
     * @param {number} riderId 骑手ID
     */
    static async acceptTask(taskId, riderId = CURRENT_RIDER_ID) {
        return HttpClient.post(`/tasks/${taskId}/accept?riderId=${riderId}`);
    }

    /**
     * 拒绝配送任务
     * @param {number} taskId 任务ID
     * @param {number} riderId 骑手ID
     * @param {string} reason 拒绝原因
     */
    static async rejectTask(taskId, riderId = CURRENT_RIDER_ID, reason = '暂时无法配送') {
        return HttpClient.post(`/tasks/${taskId}/reject?riderId=${riderId}&reason=${encodeURIComponent(reason)}`);
    }

    /**
     * 更新配送状态
     * @param {number} taskId 任务ID
     * @param {object} statusData 状态数据
     */
    static async updateStatus(taskId, statusData) {
        return HttpClient.post(`/tasks/${taskId}/status`, statusData);
    }

    /**
     * 开始取餐
     * @param {number} taskId 任务ID
     */
    static async startPickup(taskId) {
        return this.updateStatus(taskId, {
            status: 4, // 取餐中
            currentLocation: await getCurrentLocation(),
            reason: '开始取餐',
            operateTime: new Date().toISOString()
        });
    }

    /**
     * 开始配送
     * @param {number} taskId 任务ID
     */
    static async startDelivery(taskId) {
        return this.updateStatus(taskId, {
            status: 5, // 配送中
            currentLocation: await getCurrentLocation(),
            reason: '开始配送',
            operateTime: new Date().toISOString()
        });
    }

    /**
     * 确认送达
     * @param {number} taskId 任务ID
     */
    static async confirmDelivery(taskId) {
        return this.updateStatus(taskId, {
            status: 6, // 已送达
            currentLocation: await getCurrentLocation(),
            reason: '确认送达',
            operateTime: new Date().toISOString()
        });
    }

    /**
     * 获取待分配的配送任务
     * @param {string} area 区域（可选）
     * @param {number} pageNum 页码
     * @param {number} pageSize 每页大小
     */
    static async getPendingTasks(area = null, pageNum = 1, pageSize = 10) {
        const params = { pageNum, pageSize };
        if (area) {
            params.area = area;
        }
        return HttpClient.get('/tasks/pending', params);
    }

    /**
     * 取消配送任务
     * @param {number} taskId 任务ID
     * @param {string} reason 取消原因
     */
    static async cancelTask(taskId, reason) {
        return HttpClient.post(`/tasks/${taskId}/cancel?reason=${encodeURIComponent(reason)}`);
    }
}

/**
 * 统计相关API
 */
class StatisticsAPI {
    /**
     * 获取配送统计信息
     * @param {number} riderId 骑手ID
     * @param {string} startTime 开始时间
     * @param {string} endTime 结束时间
     */
    static async getDeliveryStatistics(riderId = CURRENT_RIDER_ID, startTime, endTime) {
        const params = { riderId, startTime, endTime };
        return HttpClient.get('/statistics', params);
    }

    /**
     * 获取今日统计
     * @param {number} riderId 骑手ID
     */
    static async getTodayStatistics(riderId = CURRENT_RIDER_ID) {
        const today = new Date();
        const startTime = new Date(today.getFullYear(), today.getMonth(), today.getDate()).toISOString();
        const endTime = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1).toISOString();
        return this.getDeliveryStatistics(riderId, startTime, endTime);
    }
}

/**
 * 工具函数
 */

/**
 * 获取当前位置
 * @returns {Promise<string>} 位置坐标字符串
 */
function getCurrentLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            // 如果不支持地理位置，返回默认位置
            resolve('116.397428,39.90923'); // 北京天安门坐标
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const { longitude, latitude } = position.coords;
                resolve(`${longitude},${latitude}`);
            },
            (error) => {
                console.warn('获取位置失败:', error);
                // 返回默认位置
                resolve('116.397428,39.90923');
            },
            {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 60000
            }
        );
    });
}

/**
 * 格式化时间
 * @param {Date|string} date 日期
 * @returns {string} 格式化后的时间字符串
 */
function formatDateTime(date) {
    if (!date) return '';
    
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const seconds = String(d.getSeconds()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

/**
 * 获取配送状态文本
 * @param {number} status 状态码
 * @returns {string} 状态文本
 */
function getDeliveryStatusText(status) {
    const statusMap = {
        1: '待分配',
        2: '已分配',
        3: '已接单',
        4: '取餐中',
        5: '配送中',
        6: '已送达',
        7: '异常',
        8: '已取消'
    };
    return statusMap[status] || '未知状态';
}

/**
 * 获取工作状态文本
 * @param {number} status 状态码
 * @returns {string} 状态文本
 */
function getWorkStatusText(status) {
    const statusMap = {
        1: '在线',
        2: '忙碌',
        3: '离线',
        4: '休息'
    };
    return statusMap[status] || '未知状态';
}

/**
 * 显示提示消息
 * @param {string} message 消息内容
 * @param {string} type 消息类型 success|error|warning|info
 */
function showMessage(message, type = 'info') {
    // 创建消息元素
    const messageEl = document.createElement('div');
    messageEl.className = `message message-${type}`;
    messageEl.textContent = message;
    
    // 添加样式
    messageEl.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: ${getMessageColor(type)};
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        font-size: 14px;
        z-index: 9999;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        animation: slideDown 0.3s ease;
    `;
    
    // 添加动画样式
    if (!document.querySelector('#message-styles')) {
        const style = document.createElement('style');
        style.id = 'message-styles';
        style.textContent = `
            @keyframes slideDown {
                from { transform: translateX(-50%) translateY(-100%); opacity: 0; }
                to { transform: translateX(-50%) translateY(0); opacity: 1; }
            }
            @keyframes slideUp {
                from { transform: translateX(-50%) translateY(0); opacity: 1; }
                to { transform: translateX(-50%) translateY(-100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(messageEl);
    
    // 3秒后自动移除
    setTimeout(() => {
        messageEl.style.animation = 'slideUp 0.3s ease';
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.parentNode.removeChild(messageEl);
            }
        }, 300);
    }, 3000);
}

/**
 * 获取消息颜色
 * @param {string} type 消息类型
 * @returns {string} 颜色值
 */
function getMessageColor(type) {
    const colors = {
        success: '#06C755',
        error: '#FF1744',
        warning: '#FF9800',
        info: '#1976D2'
    };
    return colors[type] || colors.info;
}

/**
 * 设置当前骑手ID
 * @param {number} riderId 骑手ID
 */
function setCurrentRiderId(riderId) {
    CURRENT_RIDER_ID = riderId;
}

/**
 * 获取当前骑手ID
 * @returns {number} 骑手ID
 */
function getCurrentRiderId() {
    return CURRENT_RIDER_ID;
}

// 导出API类和工具函数
window.RiderAPI = RiderAPI;
window.DeliveryTaskAPI = DeliveryTaskAPI;
window.StatisticsAPI = StatisticsAPI;
window.getCurrentLocation = getCurrentLocation;
window.formatDateTime = formatDateTime;
window.getDeliveryStatusText = getDeliveryStatusText;
window.getWorkStatusText = getWorkStatusText;
window.showMessage = showMessage;
window.setCurrentRiderId = setCurrentRiderId;
window.getCurrentRiderId = getCurrentRiderId;

// 初始化时获取位置权限
document.addEventListener('DOMContentLoaded', function() {
    // 请求位置权限
    getCurrentLocation().then(location => {
        console.log('当前位置:', location);
    }).catch(error => {
        console.warn('位置获取失败:', error);
    });
});