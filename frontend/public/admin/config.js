// 管理员页面配置
window.ADMIN_CONFIG = {
    // 后端API配置
    getBackendURL: function() {
        // 从环境变量或URL参数获取后端地址
        const urlParams = new URLSearchParams(window.location.search);
        const backendParam = urlParams.get('backend');
        
        if (backendParam) {
            return backendParam;
        }
        
        // 根据当前域名自动判断
        const protocol = window.location.protocol;
        const hostname = window.location.hostname;
        
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'http://localhost:8000';
        } else {
            // 生产环境配置
            // 如果前端和后端在同一域名的不同端口
            if (window.location.port) {
                return `${protocol}//${hostname}:8000`;
            }
            // 如果后端在不同的域名（Railway部署场景）
            return 'https://your-backend-railway-url.railway.app';
        }
    }
};
