// 外卖运营管理后台 - 主JavaScript文件

// 全局配置
const CONFIG = {
    API_BASE_URL: 'http://localhost:8080/api/v1',
    REFRESH_INTERVAL: 30000, // 30秒刷新一次数据
    CHART_COLORS: {
        primary: '#FFD100',
        secondary: '#FF6600',
        success: '#10B981',
        warning: '#F59E0B',
        error: '#EF4444',
        info: '#3B82F6'
    }
};

// 工具函数
const Utils = {
    // 格式化数字
    formatNumber(num) {
        if (num >= 10000) {
            return (num / 10000).toFixed(1) + '万';
        }
        return num.toLocaleString();
    },

    // 格式化金额
    formatCurrency(amount) {
        return '¥' + amount.toLocaleString();
    },

    // 格式化日期
    formatDate(date) {
        return new Date(date).toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // 格式化相对时间
    formatRelativeTime(date) {
        const now = new Date();
        const diff = now - new Date(date);
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return '刚刚';
        if (minutes < 60) return `${minutes}分钟前`;
        if (hours < 24) return `${hours}小时前`;
        if (days < 7) return `${days}天前`;
        return this.formatDate(date);
    },

    // 生成随机ID
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    },

    // 防抖函数
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // 显示通知
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${this.getNotificationIcon(type)}"></i>
            <span>${message}</span>
            <button class="notification-close">&times;</button>
        `;

        document.body.appendChild(notification);

        // 自动关闭
        setTimeout(() => {
            notification.remove();
        }, 5000);

        // 点击关闭
        notification.querySelector('.notification-close').onclick = () => {
            notification.remove();
        };
    },

    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            warning: 'exclamation-triangle',
            error: 'times-circle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
};

// 模拟数据生成器
const MockData = {
    // 生成统计数据
    generateStats() {
        return {
            todayOrders: Math.floor(Math.random() * 2000) + 1000,
            todayRevenue: Math.floor(Math.random() * 50000) + 30000,
            activeUsers: Math.floor(Math.random() * 10000) + 5000,
            activeMerchants: Math.floor(Math.random() * 500) + 400
        };
    },

    // 生成订单趋势数据
    generateOrderTrend(days = 7) {
        const data = [];
        const labels = [];
        const now = new Date();

        for (let i = days - 1; i >= 0; i--) {
            const date = new Date(now);
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }));
            data.push(Math.floor(Math.random() * 1000) + 500);
        }

        return { labels, data };
    },

    // 生成商家分布数据
    generateMerchantDistribution() {
        return {
            labels: ['中式快餐', '西式快餐', '火锅烧烤', '甜品饮品', '日韩料理', '其他'],
            data: [35, 25, 15, 12, 8, 5]
        };
    },

    // 生成最新订单数据
    generateRecentOrders(count = 10) {
        const orders = [];
        const statuses = [
            { text: '待支付', class: 'warning' },
            { text: '已支付', class: 'info' },
            { text: '配送中', class: 'info' },
            { text: '已完成', class: 'success' },
            { text: '已取消', class: 'error' }
        ];

        const merchants = [
            '麦当劳(三里屯店)', '星巴克(国贸店)', '肯德基(王府井店)',
            '海底捞(三里屯店)', '必胜客(朝阳店)', '汉堡王(西单店)'
        ];

        const users = [
            '张三', '李四', '王五', '赵六', '钱七', '孙八'
        ];

        for (let i = 0; i < count; i++) {
            const status = statuses[Math.floor(Math.random() * statuses.length)];
            orders.push({
                id: 'ORD' + Date.now().toString().slice(-8) + i.toString().padStart(2, '0'),
                user: users[Math.floor(Math.random() * users.length)],
                merchant: merchants[Math.floor(Math.random() * merchants.length)],
                amount: (Math.random() * 100 + 20).toFixed(2),
                status: status,
                time: new Date(Date.now() - Math.random() * 86400000).toISOString()
            });
        }

        return orders;
    },

    // 生成用户数据
    generateUsers(count = 50) {
        const users = [];
        const names = ['张三', '李四', '王五', '赵六', '钱七', '孙八', '周九', '吴十'];
        const phones = ['138', '139', '150', '151', '152', '188', '189'];

        for (let i = 0; i < count; i++) {
            users.push({
                id: 10000 + i,
                name: names[Math.floor(Math.random() * names.length)] + i,
                phone: phones[Math.floor(Math.random() * phones.length)] + 
                       Math.random().toString().slice(2, 10),
                email: `user${i}@example.com`,
                registerTime: new Date(Date.now() - Math.random() * 31536000000).toISOString(),
                lastLoginTime: new Date(Date.now() - Math.random() * 86400000).toISOString(),
                orderCount: Math.floor(Math.random() * 100),
                totalAmount: (Math.random() * 10000).toFixed(2),
                status: Math.random() > 0.1 ? 'active' : 'inactive'
            });
        }

        return users;
    },

    // 生成商家数据
    generateMerchants(count = 30) {
        const merchants = [];
        const names = [
            '麦当劳', '肯德基', '星巴克', '必胜客', '汉堡王', '德克士',
            '海底捞', '呷哺呷哺', '小龙坎', '大龙燚', '蜀大侠', '巴奴毛肚火锅'
        ];
        const areas = ['三里屯', '国贸', '王府井', '西单', '朝阳', '海淀', '丰台', '昌平'];
        const categories = ['中式快餐', '西式快餐', '火锅烧烤', '甜品饮品', '日韩料理'];
        const statuses = [
            { text: '营业中', class: 'success' },
            { text: '休息中', class: 'warning' },
            { text: '待审核', class: 'info' },
            { text: '已停业', class: 'error' }
        ];

        for (let i = 0; i < count; i++) {
            const name = names[Math.floor(Math.random() * names.length)];
            const area = areas[Math.floor(Math.random() * areas.length)];
            const status = statuses[Math.floor(Math.random() * statuses.length)];

            merchants.push({
                id: 20000 + i,
                name: `${name}(${area}店)`,
                category: categories[Math.floor(Math.random() * categories.length)],
                phone: '010-' + Math.random().toString().slice(2, 10),
                address: `北京市朝阳区${area}街道${Math.floor(Math.random() * 100)}号`,
                rating: (Math.random() * 2 + 3).toFixed(1),
                monthlyOrders: Math.floor(Math.random() * 5000) + 1000,
                monthlyRevenue: (Math.random() * 100000 + 50000).toFixed(2),
                status: status,
                joinTime: new Date(Date.now() - Math.random() * 31536000000).toISOString()
            });
        }

        return merchants;
    }
};

// 主应用类
class AdminApp {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadInitialData();
        this.startAutoRefresh();
    }

    // 绑定事件
    bindEvents() {
        // 侧边栏切换
        const sidebarToggle = document.querySelector('.sidebar-toggle');
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', this.toggleSidebar);
        }

        // 导航菜单点击
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', this.handleNavClick);
        });

        // 搜索框
        const searchInput = document.querySelector('.search-box input');
        if (searchInput) {
            searchInput.addEventListener('input', Utils.debounce(this.handleSearch, 300));
        }

        // 通知按钮
        const notificationBtn = document.querySelector('.notification-btn');
        if (notificationBtn) {
            notificationBtn.addEventListener('click', this.showNotifications);
        }

        // 用户菜单
        const userMenu = document.querySelector('.user-menu');
        if (userMenu) {
            userMenu.addEventListener('click', this.toggleUserMenu);
        }

        // 响应式处理
        window.addEventListener('resize', this.handleResize);
    }

    // 切换侧边栏
    toggleSidebar() {
        const sidebar = document.querySelector('.sidebar');
        sidebar.classList.toggle('open');
    }

    // 处理导航点击
    handleNavClick(e) {
        e.preventDefault();
        
        // 移除所有活动状态
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // 添加当前活动状态
        e.target.closest('.nav-item').classList.add('active');
        
        // 获取页面路径
        const href = e.target.closest('.nav-link').getAttribute('href');
        
        // 如果是当前页面，不需要跳转
        if (href === window.location.pathname.split('/').pop()) {
            return;
        }
        
        // 跳转到对应页面
        window.location.href = href;
    }

    // 处理搜索
    handleSearch(e) {
        const query = e.target.value.trim();
        if (query.length > 0) {
            console.log('搜索:', query);
            // 这里可以实现搜索逻辑
        }
    }

    // 显示通知
    showNotifications() {
        Utils.showNotification('您有5条新通知', 'info');
    }

    // 切换用户菜单
    toggleUserMenu() {
        console.log('切换用户菜单');
        // 这里可以实现用户菜单下拉逻辑
    }

    // 处理窗口大小变化
    handleResize() {
        const width = window.innerWidth;
        const sidebar = document.querySelector('.sidebar');
        
        if (width <= 768) {
            sidebar.classList.remove('open');
        }
    }

    // 加载初始数据
    loadInitialData() {
        // 这里可以加载页面初始数据
        console.log('加载初始数据');
    }

    // 开始自动刷新
    startAutoRefresh() {
        setInterval(() => {
            this.refreshData();
        }, CONFIG.REFRESH_INTERVAL);
    }

    // 刷新数据
    refreshData() {
        console.log('刷新数据');
        // 这里可以实现数据刷新逻辑
    }
}

// API 服务类
class ApiService {
    constructor() {
        this.baseURL = CONFIG.API_BASE_URL;
    }

    // 通用请求方法
    async request(url, options = {}) {
        try {
            const response = await fetch(`${this.baseURL}${url}`, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API请求失败:', error);
            // 使用模拟数据
            return this.getMockData(url);
        }
    }

    // 获取模拟数据
    getMockData(url) {
        // 根据URL返回对应的模拟数据
        if (url.includes('/platform/statistics')) {
            return {
                code: '00000',
                data: MockData.generateStats()
            };
        }
        
        if (url.includes('/orders')) {
            return {
                code: '00000',
                data: MockData.generateRecentOrders()
            };
        }
        
        return {
            code: '00000',
            data: null
        };
    }

    // 获取平台统计数据
    async getPlatformStats() {
        return await this.request('/platform/statistics');
    }

    // 获取订单列表
    async getOrders(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return await this.request(`/orders?${queryString}`);
    }

    // 获取商家列表
    async getMerchants(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return await this.request(`/platform/merchants?${queryString}`);
    }

    // 获取用户列表
    async getUsers(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return await this.request(`/users?${queryString}`);
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.adminApp = new AdminApp();
    window.apiService = new ApiService();
    window.utils = Utils;
    window.mockData = MockData;
    
    console.log('外卖运营管理后台已初始化');
});

// 导出给其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        AdminApp,
        ApiService,
        Utils,
        MockData,
        CONFIG
    };
}