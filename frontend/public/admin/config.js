// 管理员页面配置 - 使用统一配置
window.ADMIN_CONFIG = {
    // 后端API配置
    getBackendURL: function() {
        // 优先使用全局配置
        if (window.APP_CONFIG) {
            return window.APP_CONFIG.getBackendUrl();
        }

        // 降级方案：从环境变量或URL参数获取后端地址
        const urlParams = new URLSearchParams(window.location.search);
        const backendParam = urlParams.get('backend');

        if (backendParam) {
            return backendParam;
        }

        // 根据当前域名自动判断
        const hostname = window.location.hostname;

        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'http://localhost:8000';
        } else {
            // 生产环境默认配置
            return 'https://web-production-5fb04.up.railway.app';
        }
    }
};
