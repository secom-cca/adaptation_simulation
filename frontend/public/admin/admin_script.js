// 管理员页面脚本
class AdminDashboard {
    constructor() {
        // 使用配置文件获取后端URL
        this.baseURL = window.ADMIN_CONFIG.getBackendURL() + '/admin';
        this.credentials = null;
        this.dashboardData = null;

        console.log('管理员页面后端URL:', this.baseURL);
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // 认证表单
        document.getElementById('auth-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.authenticate();
        });

        // 刷新按钮
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadDashboard();
        });

        // 退出按钮
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.logout();
        });

        // 下载按钮
        document.getElementById('download-all-btn').addEventListener('click', () => {
            this.downloadData('all');
        });

        document.getElementById('download-logs-btn').addEventListener('click', () => {
            this.downloadData('logs');
        });

        document.getElementById('download-scores-btn').addEventListener('click', () => {
            this.downloadData('scores');
        });

        // 🔧 数据清空功能按钮
        document.getElementById('clear-data-btn').addEventListener('click', () => {
            this.showClearDataConfirmation();
        });

        // 模态框关闭
        document.querySelector('.close').addEventListener('click', () => {
            this.closeModal();
        });

        // 🔧 清空确认模态框关闭
        document.getElementById('clear-modal-close').addEventListener('click', () => {
            this.closeClearModal();
        });

        document.getElementById('cancel-clear-btn').addEventListener('click', () => {
            this.closeClearModal();
        });

        document.getElementById('execute-clear-btn').addEventListener('click', () => {
            this.executeClearData();
        });

        // 🔧 确认输入监听
        document.getElementById('delete-confirmation').addEventListener('input', () => {
            this.validateClearConfirmation();
        });

        // 🔧 复选框监听
        document.getElementById('confirm-backup').addEventListener('change', () => {
            this.validateClearConfirmation();
        });

        document.getElementById('confirm-understand').addEventListener('change', () => {
            this.validateClearConfirmation();
        });

        window.addEventListener('click', (e) => {
            if (e.target === document.getElementById('user-modal')) {
                this.closeModal();
            }
            if (e.target === document.getElementById('clear-confirm-modal')) {
                this.closeClearModal();
            }
        });
    }

    async authenticate() {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        if (!username || !password) {
            this.showError('ユーザー名とパスワードを入力してください');
            return;
        }

        this.credentials = btoa(`${username}:${password}`);
        
        try {
            this.showLoading(true);
            const response = await fetch(`${this.baseURL}/dashboard`, {
                headers: {
                    'Authorization': `Basic ${this.credentials}`
                }
            });

            if (response.ok) {
                this.dashboardData = await response.json();
                this.showDashboard();
                this.updateDashboard();
            } else {
                this.showError('認証に失敗しました。ユーザー名とパスワードを確認してください');
                this.credentials = null;
            }
        } catch (error) {
            console.error('認証エラー:', error);
            this.showError('サーバーへの接続に失敗しました。しばらくしてから再試行してください');
            this.credentials = null;
        } finally {
            this.showLoading(false);
        }
    }

    async loadDashboard() {
        if (!this.credentials) return;

        try {
            this.showLoading(true);
            const response = await fetch(`${this.baseURL}/dashboard`, {
                headers: {
                    'Authorization': `Basic ${this.credentials}`
                }
            });

            if (response.ok) {
                this.dashboardData = await response.json();
                this.updateDashboard();
                document.getElementById('last-update').textContent =
                    `最終更新: ${new Date().toLocaleString()}`;
            } else {
                this.showError('データの取得に失敗しました');
            }
        } catch (error) {
            console.error('データ読み込みエラー:', error);
            this.showError('データの読み込みに失敗しました');
        } finally {
            this.showLoading(false);
        }
    }

    updateDashboard() {
        if (!this.dashboardData) return;

        const { summary, users, user_scores, recent_activity } = this.dashboardData;

        // 更新统计数据
        document.getElementById('total-users').textContent = summary.total_users;
        document.getElementById('total-logs').textContent = summary.total_logs.toLocaleString();
        document.getElementById('total-simulations').textContent = summary.total_simulations;
        
        const lastActivity = summary.last_activity ?
            new Date(summary.last_activity).toLocaleString() : 'なし';
        document.getElementById('last-activity').textContent = lastActivity;

        // 更新用户列表
        this.updateUsersList(users, user_scores);

        // 更新最近活动
        this.updateRecentActivity(recent_activity);
    }

    updateUsersList(users, userScores) {
        const usersGrid = document.getElementById('users-grid');
        usersGrid.innerHTML = '';

        users.forEach(userName => {
            const userCard = document.createElement('div');
            userCard.className = 'user-card';
            userCard.onclick = () => this.showUserDetail(userName);

            const scores = userScores[userName] || [];
            const simulationCount = scores.length;
            const avgScore = scores.length > 0 ? 
                (scores.reduce((sum, s) => sum + parseFloat(s.total_score), 0) / scores.length).toFixed(1) : 'N/A';

            userCard.innerHTML = `
                <div class="user-name">${userName}</div>
                <div class="user-stats">
                    <div>シミュレーション回数: ${simulationCount}</div>
                    <div>平均スコア: ${avgScore}</div>
                </div>
            `;

            usersGrid.appendChild(userCard);
        });
    }

    updateRecentActivity(activities) {
        const activityList = document.getElementById('activity-list');
        activityList.innerHTML = '';

        activities.slice(0, 20).forEach(activity => {
            const activityItem = document.createElement('div');
            activityItem.className = 'activity-item';

            const icon = this.getActivityIcon(activity.type);
            const time = new Date(activity.timestamp).toLocaleString();

            activityItem.innerHTML = `
                <div class="activity-icon">${icon}</div>
                <div class="activity-content">
                    <div class="activity-text">
                        <strong>${activity.user_name}</strong> ${this.getActivityText(activity)}
                    </div>
                    <div class="activity-time">${time}</div>
                </div>
            `;

            activityList.appendChild(activityItem);
        });
    }

    getActivityIcon(type) {
        const icons = {
            'Register': '👤',
            'Slider': '🎚️',
            'Next': '⏭️',
            'GraphSelect': '📊',
            'StartCompare': '🔍',
            'EndCompare': '✅',
            'EndCycle': '🔄',
            'ScatterX': '📈',
            'ScatterY': '📉'
        };
        return icons[type] || '📝';
    }

    getActivityText(activity) {
        const texts = {
            'Register': 'アカウントを登録しました',
            'Slider': `${activity.name}を調整しました`,
            'Next': `${activity.name}年に進みました`,
            'GraphSelect': `グラフ${activity.name}を選択しました`,
            'StartCompare': '比較を開始しました',
            'EndCompare': '比較を終了しました',
            'EndCycle': 'サイクルを終了しました',
            'ScatterX': `X軸を${activity.name}に設定しました`,
            'ScatterY': `Y軸を${activity.name}に設定しました`
        };
        return texts[activity.type] || `${activity.type}を実行しました`;
    }

    async showUserDetail(userName) {
        try {
            this.showLoading(true);
            const response = await fetch(`${this.baseURL}/users/${userName}`, {
                headers: {
                    'Authorization': `Basic ${this.credentials}`
                }
            });

            if (response.ok) {
                const userData = await response.json();
                this.displayUserModal(userData);
            } else {
                this.showError('ユーザー詳細の取得に失敗しました');
            }
        } catch (error) {
            console.error('ユーザー詳細取得エラー:', error);
            this.showError('ユーザー詳細の取得に失敗しました');
        } finally {
            this.showLoading(false);
        }
    }

    displayUserModal(userData) {
        const modal = document.getElementById('user-modal');
        const modalUserName = document.getElementById('modal-user-name');
        const modalBody = document.getElementById('modal-body');

        modalUserName.textContent = `ユーザー詳細 - ${userData.user_name}`;

        modalBody.innerHTML = `
            <div class="user-detail">
                <h4>📊 統計情報</h4>
                <div class="stats-grid">
                    <div>総操作数: ${userData.statistics.total_actions}</div>
                    <div>シミュレーション期間数: ${userData.statistics.simulation_periods}</div>
                    <div>初回アクティビティ: ${userData.statistics.first_activity ? new Date(userData.statistics.first_activity).toLocaleString() : 'N/A'}</div>
                    <div>最終アクティビティ: ${userData.statistics.last_activity ? new Date(userData.statistics.last_activity).toLocaleString() : 'N/A'}</div>
                </div>

                <h4>🎯 シミュレーション結果</h4>
                <div class="scores-table">
                    ${userData.scores.map(score => `
                        <div class="score-item">
                            <strong>${score.period}</strong> - 総合スコア: ${parseFloat(score.total_score).toFixed(2)}
                            <br><small>時刻: ${new Date(score.timestamp).toLocaleString()}</small>
                        </div>
                    `).join('')}
                </div>

                <h4>📝 最近の操作 (最新10件)</h4>
                <div class="logs-list">
                    ${userData.logs.slice(-10).reverse().map(log => `
                        <div class="log-item">
                            <span class="log-type">${this.getActivityIcon(log.type)} ${log.type}</span>
                            <span class="log-detail">${log.name || ''} ${log.value || ''}</span>
                            <span class="log-time">${new Date(log.timestamp).toLocaleString()}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        modal.style.display = 'block';
    }

    closeModal() {
        document.getElementById('user-modal').style.display = 'none';
    }

    // 🔧 显示数据清空确认对话框
    async showClearDataConfirmation() {
        try {
            this.showLoading(true);

            // 获取数据统计
            const response = await fetch(`${this.baseURL}/data-stats`, {
                headers: {
                    'Authorization': `Basic ${this.credentials}`
                }
            });

            if (response.ok) {
                const dataStats = await response.json();
                this.displayClearConfirmationModal(dataStats);
            } else {
                this.showError('データ統計の取得に失敗しました');
            }
        } catch (error) {
            console.error('データ統計取得エラー:', error);
            this.showError('データ統計の取得に失敗しました');
        } finally {
            this.showLoading(false);
        }
    }

    // 🔧 显示清空确认模态框
    displayClearConfirmationModal(dataStats) {
        const modal = document.getElementById('clear-confirm-modal');
        const statsSection = document.getElementById('clear-stats');

        const { summary, files, users, periods } = dataStats;

        statsSection.innerHTML = `
            <h4>📊 削除されるデータ</h4>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">${summary.total_users}</div>
                    <div class="stat-label">ユーザー</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${summary.total_logs.toLocaleString()}</div>
                    <div class="stat-label">操作ログ</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${summary.total_simulations}</div>
                    <div class="stat-label">シミュレーション結果</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${summary.total_decision_logs}</div>
                    <div class="stat-label">決定ログ</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${summary.total_size_mb} MB</div>
                    <div class="stat-label">総データサイズ</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${summary.simulation_periods}</div>
                    <div class="stat-label">シミュレーション期間</div>
                </div>
            </div>

            <div class="file-details">
                <h5>📁 影響を受けるファイル:</h5>
                <ul>
                    ${Object.entries(files).map(([fileName, fileInfo]) => `
                        <li>
                            <strong>${fileName}</strong>:
                            ${fileInfo.exists ? `${fileInfo.size_mb} MB` : '存在しません'}
                        </li>
                    `).join('')}
                </ul>
            </div>

            ${users.length > 0 ? `
                <div class="users-details">
                    <h5>👥 影響を受けるユーザー (${users.length}名):</h5>
                    <div class="users-list">${users.join(', ')}</div>
                </div>
            ` : ''}

            ${summary.earliest_activity ? `
                <div class="activity-period">
                    <h5>📅 データ期間:</h5>
                    <p>${new Date(summary.earliest_activity).toLocaleString()} ～ ${new Date(summary.latest_activity).toLocaleString()}</p>
                </div>
            ` : ''}
        `;

        // 重置确认状态
        document.getElementById('confirm-backup').checked = false;
        document.getElementById('confirm-understand').checked = false;
        document.getElementById('delete-confirmation').value = '';
        document.getElementById('execute-clear-btn').disabled = true;

        modal.style.display = 'block';
    }

    // 🔧 关闭清空确认模态框
    closeClearModal() {
        document.getElementById('clear-confirm-modal').style.display = 'none';
    }

    // 🔧 验证清空确认条件
    validateClearConfirmation() {
        const backupChecked = document.getElementById('confirm-backup').checked;
        const understandChecked = document.getElementById('confirm-understand').checked;
        const deleteText = document.getElementById('delete-confirmation').value.toUpperCase();

        const allConditionsMet = backupChecked && understandChecked && deleteText === 'DELETE';
        document.getElementById('execute-clear-btn').disabled = !allConditionsMet;
    }

    // 🔧 执行数据清空
    async executeClearData() {
        try {
            this.showLoading(true);

            const response = await fetch(`${this.baseURL}/clear-data`, {
                method: 'POST',
                headers: {
                    'Authorization': `Basic ${this.credentials}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const result = await response.json();
                this.closeClearModal();

                if (result.success) {
                    this.showSuccessMessage('データクリアが正常に完了しました', result);
                    // 刷新仪表板数据
                    await this.loadDashboard();
                } else {
                    this.showError(`データクリアが部分的に失敗しました: ${result.errors.join(', ')}`);
                }
            } else {
                const errorData = await response.json();
                this.showError(`データクリアに失敗しました: ${errorData.detail}`);
            }
        } catch (error) {
            console.error('データクリアエラー:', error);
            this.showError('データクリアに失敗しました。サーバーエラーが発生しました');
        } finally {
            this.showLoading(false);
        }
    }

    // 🔧 显示成功消息
    showSuccessMessage(message, details) {
        // 创建成功提示
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(16, 185, 129, 0.3);
            z-index: 10000;
            max-width: 400px;
            animation: slideIn 0.3s ease-out;
        `;

        successDiv.innerHTML = `
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 24px; margin-right: 10px;">✅</span>
                <strong>${message}</strong>
            </div>
            <div style="font-size: 14px; opacity: 0.9;">
                処理されたファイル: ${details.successful_clears}/${details.total_files_processed}
            </div>
            <div style="font-size: 12px; opacity: 0.8; margin-top: 5px;">
                ${new Date(details.timestamp).toLocaleString()}
            </div>
        `;

        document.body.appendChild(successDiv);

        // 3秒后自动移除
        setTimeout(() => {
            if (successDiv.parentNode) {
                successDiv.parentNode.removeChild(successDiv);
            }
        }, 5000);
    }

    async downloadData(type) {
        if (!this.credentials) return;

        try {
            this.showLoading(true);
            const response = await fetch(`${this.baseURL}/download/${type}`, {
                headers: {
                    'Authorization': `Basic ${this.credentials}`
                }
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                
                // 从响应头获取文件名
                const contentDisposition = response.headers.get('content-disposition');
                const filename = contentDisposition ? 
                    contentDisposition.split('filename=')[1].replace(/"/g, '') :
                    `climate_data_${type}_${new Date().toISOString().slice(0, 10)}.zip`;
                
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                this.showError('ダウンロードに失敗しました');
            }
        } catch (error) {
            console.error('ダウンロードエラー:', error);
            this.showError('ダウンロードに失敗しました');
        } finally {
            this.showLoading(false);
        }
    }

    showDashboard() {
        document.getElementById('auth-section').style.display = 'none';
        document.getElementById('dashboard-section').style.display = 'block';
    }

    logout() {
        this.credentials = null;
        this.dashboardData = null;
        document.getElementById('auth-section').style.display = 'flex';
        document.getElementById('dashboard-section').style.display = 'none';
        document.getElementById('username').value = '';
        document.getElementById('password').value = '';
        this.hideError();
    }

    showError(message) {
        const errorDiv = document.getElementById('auth-error');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }

    hideError() {
        document.getElementById('auth-error').style.display = 'none';
    }

    showLoading(show) {
        document.getElementById('loading').style.display = show ? 'flex' : 'none';
    }
}

// 初始化管理员仪表板
document.addEventListener('DOMContentLoaded', () => {
    new AdminDashboard();
});

// 防止页面被意外访问的额外保护
document.addEventListener('contextmenu', (e) => {
    e.preventDefault();
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'F12' || (e.ctrlKey && e.shiftKey && e.key === 'I')) {
        e.preventDefault();
    }
});

