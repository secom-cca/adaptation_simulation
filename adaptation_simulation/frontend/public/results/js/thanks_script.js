// 感谢页面脚本
document.addEventListener('DOMContentLoaded', function() {
    console.log('感谢页面加载完成');
    
    // 加载用户名
    loadPlayerName();
    
    // 添加动画效果
    addAnimations();
    
    // 添加粒子效果
    createParticles();
});

// 加载玩家名称
function loadPlayerName() {
    // 优先从localStorage获取用户名
    const storedName = localStorage.getItem('userName');
    if (storedName && storedName.trim() !== '') {
        console.log('从localStorage加载用户名:', storedName);
        document.getElementById('player-name').textContent = storedName;
        return;
    }

    // 尝试从sessionStorage获取（作为备选）
    const sessionName = sessionStorage.getItem('userName');
    if (sessionName && sessionName.trim() !== '') {
        console.log('从sessionStorage加载用户名:', sessionName);
        document.getElementById('player-name').textContent = sessionName;
        // 同时保存到localStorage
        localStorage.setItem('userName', sessionName);
        return;
    }

    // 最后尝试从URL参数获取
    const urlParams = new URLSearchParams(window.location.search);
    const urlName = urlParams.get('userName');
    if (urlName && urlName.trim() !== '') {
        console.log('从URL参数加载用户名:', urlName);
        document.getElementById('player-name').textContent = urlName;
        // 保存到localStorage
        localStorage.setItem('userName', urlName);
        return;
    }

    // 如果都没有，使用默认值
    console.log('未找到用户名，使用默认值');
    document.getElementById('player-name').textContent = 'プレイヤー';
}

// 重新开始模拟
function restartSimulation() {
    // 确认对话框
    if (confirm('新しいシミュレーションを開始しますか？\n現在の結果は失われます。')) {
        // 清除localStorage中的数据（可选）
        // localStorage.removeItem('userName');
        // localStorage.removeItem('selectedMode');
        // localStorage.removeItem('chartPredictMode');
        
        // 跳转到主页（自动检测环境）
        const baseUrl = window.location.hostname === 'localhost'
            ? 'http://localhost:3000/'
            : window.location.origin.replace(/\/results.*/, '/');
        window.location.href = baseUrl;
    }
}

// 添加动画效果
function addAnimations() {
    // 为统计项目添加延迟动画
    const statItems = document.querySelectorAll('.stat-item');
    statItems.forEach((item, index) => {
        item.style.animationDelay = `${index * 0.1}s`;
        item.classList.add('fade-in-up');
    });
    
    // 为行动项目添加延迟动画
    const actionItems = document.querySelectorAll('.action-item');
    actionItems.forEach((item, index) => {
        item.style.animationDelay = `${(index + statItems.length) * 0.1}s`;
        item.classList.add('fade-in-left');
    });
}

// 创建粒子效果
function createParticles() {
    const particleContainer = document.createElement('div');
    particleContainer.className = 'particles';
    particleContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 0;
    `;
    
    document.body.appendChild(particleContainer);
    
    // 创建多个粒子
    for (let i = 0; i < 20; i++) {
        createParticle(particleContainer);
    }
}

function createParticle(container) {
    const particle = document.createElement('div');
    const symbols = ['🌱', '🌿', '🍃', '💚', '🌍', '⭐', '✨'];
    const symbol = symbols[Math.floor(Math.random() * symbols.length)];
    
    particle.textContent = symbol;
    particle.style.cssText = `
        position: absolute;
        font-size: ${Math.random() * 20 + 10}px;
        opacity: ${Math.random() * 0.5 + 0.3};
        animation: float ${Math.random() * 10 + 10}s linear infinite;
        left: ${Math.random() * 100}%;
        top: 100%;
    `;
    
    container.appendChild(particle);
    
    // 动画结束后移除粒子并创建新的
    particle.addEventListener('animationend', () => {
        particle.remove();
        createParticle(container);
    });
}

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes fade-in-up {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes fade-in-left {
        from {
            opacity: 0;
            transform: translateX(-30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes float {
        from {
            transform: translateY(0) rotate(0deg);
            opacity: 0;
        }
        10% {
            opacity: 1;
        }
        90% {
            opacity: 1;
        }
        to {
            transform: translateY(-100vh) rotate(360deg);
            opacity: 0;
        }
    }
    
    .fade-in-up {
        animation: fade-in-up 0.6s ease-out forwards;
        opacity: 0;
    }
    
    .fade-in-left {
        animation: fade-in-left 0.6s ease-out forwards;
        opacity: 0;
    }
`;

document.head.appendChild(style);

// 添加键盘快捷键
document.addEventListener('keydown', function(event) {
    // ESC键关闭窗口
    if (event.key === 'Escape') {
        window.close();
    }
    
    // Enter键重新开始
    if (event.key === 'Enter') {
        restartSimulation();
    }
});

// 页面可见性变化时的处理
document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible') {
        console.log('感谢页面重新获得焦点');
    }
});

// 页面卸载前的处理
window.addEventListener('beforeunload', function(event) {
    console.log('感谢页面即将关闭');
});

console.log('感谢页面脚本加载完成');
