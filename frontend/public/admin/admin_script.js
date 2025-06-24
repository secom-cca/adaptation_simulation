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
                this.currentUserData = userData; // 保存当前用户数据供导出使用
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
            <div class="user-detail-content">
                <!-- 数据概览 -->
                <div class="data-overview">
                    <h4>📊 データ概要</h4>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-number">${userData.statistics.total_actions || 0}</div>
                            <div class="stat-label">総操作数</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${userData.statistics.total_decisions || 0}</div>
                            <div class="stat-label">決定記録</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${userData.statistics.simulation_periods || 0}</div>
                            <div class="stat-label">シミュレーション期間</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${Object.keys(userData.statistics.action_types || {}).length}</div>
                            <div class="stat-label">操作タイプ</div>
                        </div>
                    </div>
                </div>

                <!-- 数据选择标签页 -->
                <div class="data-tabs">
                    <div class="tab-buttons">
                        <button class="tab-btn active" data-tab="user-logs">📋 操作ログ</button>
                        <button class="tab-btn" data-tab="block-scores">📊 評価データ</button>
                        <button class="tab-btn" data-tab="decision-log">📝 決定記録</button>
                        <button class="tab-btn" data-tab="parameter-zones">🎯 パラメータ設定</button>
                        <button class="tab-btn" data-tab="user-info">👤 ユーザー情報</button>
                    </div>

                    <!-- 操作日志标签页 -->
                    <div class="tab-content active" id="user-logs">
                        <div class="tab-header">
                            <h5>📋 ユーザー操作ログ (${(userData.user_logs || []).length}件)</h5>
                            <button class="export-btn" onclick="adminApp.exportUserData('${userData.user_name}', 'user_logs')">
                                💾 エクスポート
                            </button>
                        </div>
                        ${this.renderUserLogsTab(userData.user_logs, userData.statistics.action_types || {})}
                    </div>

                    <!-- 评分数据标签页 -->
                    <div class="tab-content" id="block-scores">
                        <div class="tab-header">
                            <h5>📊 シミュレーション評価データ (${(userData.block_scores || []).length}件)</h5>
                            <button class="export-btn" onclick="adminApp.exportUserData('${userData.user_name}', 'block_scores')">
                                💾 エクスポート
                            </button>
                        </div>
                        ${this.renderBlockScoresTab(userData.block_scores)}
                    </div>

                    <!-- 决策记录标签页 -->
                    <div class="tab-content" id="decision-log">
                        <div class="tab-header">
                            <h5>📝 決定記録 (${(userData.decision_log || []).length}件)</h5>
                            <button class="export-btn" onclick="adminApp.exportUserData('${userData.user_name}', 'decision_log')">
                                💾 エクスポート
                            </button>
                        </div>
                        ${this.renderDecisionLogTab(userData.decision_log)}
                    </div>

                    <!-- 参数配置标签页 -->
                    <div class="tab-content" id="parameter-zones">
                        <div class="tab-header">
                            <h5>🎯 パラメータ設定 (${(userData.parameter_zones || []).length}件)</h5>
                        </div>
                        ${this.renderParameterZonesTab(userData.parameter_zones)}
                    </div>

                    <!-- 用户信息标签页 -->
                    <div class="tab-content" id="user-info">
                        <div class="tab-header">
                            <h5>👤 ユーザー情報</h5>
                        </div>
                        ${this.renderUserInfoTab(userData)}
                    </div>
                </div>
            </div>
        `;

        // 添加标签页切换事件
        this.initTabSwitching();

        modal.style.display = 'block';
    }

    closeModal() {
        document.getElementById('user-modal').style.display = 'none';
    }

    // 初始化标签页切换功能
    initTabSwitching() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const targetTab = button.getAttribute('data-tab');

                // 移除所有活动状态
                tabButtons.forEach(btn => btn.classList.remove('active'));
                tabContents.forEach(content => content.classList.remove('active'));

                // 添加活动状态
                button.classList.add('active');
                document.getElementById(targetTab).classList.add('active');
            });
        });
    }

    // 渲染用户操作日志标签页
    renderUserLogsTab(userLogs, actionTypes) {
        if (!userLogs || userLogs.length === 0) {
            return '<div class="no-data">📭 操作ログがありません</div>';
        }

        // 操作类型统计图表
        const actionTypesChart = Object.entries(actionTypes || {}).map(([type, count]) => `
            <div class="action-type-item">
                <span class="action-type">${this.getActivityIcon(type)} ${type}</span>
                <span class="action-count">${count}回</span>
                <div class="action-bar">
                    <div class="action-fill" style="width: ${(count / Math.max(...Object.values(actionTypes || {}))) * 100}%"></div>
                </div>
            </div>
        `).join('');

        // 最近的操作记录
        const recentLogs = userLogs.slice(-20).reverse().map(log => `
            <div class="log-item">
                <div class="log-icon">${this.getActivityIcon(log.type)}</div>
                <div class="log-content">
                    <div class="log-type">${log.type}</div>
                    <div class="log-details">
                        ${log.name ? `<span class="log-name">${log.name}</span>` : ''}
                        ${log.value ? `<span class="log-value">${log.value}</span>` : ''}
                        ${log.cycle ? `<span class="log-cycle">サイクル${log.cycle}</span>` : ''}
                    </div>
                </div>
                <div class="log-time">${new Date(log.timestamp).toLocaleString()}</div>
            </div>
        `).join('');

        return `
            <div class="logs-section">
                <div class="action-types-chart">
                    <h6>📊 操作タイプ統計</h6>
                    <div class="action-types-list">
                        ${actionTypesChart}
                    </div>
                </div>

                <div class="recent-logs">
                    <h6>📝 最近の操作 (最新20件)</h6>
                    <div class="logs-list">
                        ${recentLogs}
                    </div>
                </div>
            </div>
        `;
    }

    // 渲染评分数据标签页
    renderBlockScoresTab(blockScores) {
        if (!blockScores || blockScores.length === 0) {
            return '<div class="no-data">📭 評価データがありません</div>';
        }

        const scoresTable = blockScores.map(score => {
            let rawData = '';
            let scoreData = '';

            try {
                const raw = typeof score.raw === 'string' ? JSON.parse(score.raw.replace(/'/g, '"')) : score.raw;
                const scoreObj = typeof score.score === 'string' ? JSON.parse(score.score.replace(/'/g, '"')) : score.score;

                rawData = Object.entries(raw).map(([key, value]) =>
                    `<div class="score-detail"><span>${key}:</span> <span>${typeof value === 'number' ? value.toFixed(2) : value}</span></div>`
                ).join('');

                scoreData = Object.entries(scoreObj).map(([key, value]) =>
                    `<div class="score-detail"><span>${key}:</span> <span>${typeof value === 'number' ? value.toFixed(1) : value}</span></div>`
                ).join('');
            } catch (e) {
                rawData = score.raw || 'データ解析エラー';
                scoreData = score.score || 'データ解析エラー';
            }

            return `
                <div class="score-card">
                    <div class="score-header">
                        <h6>${score.period}</h6>
                        <div class="total-score">総合: ${parseFloat(score.total_score).toFixed(2)}</div>
                    </div>
                    <div class="score-details">
                        <div class="score-section">
                            <h7>📊 評価スコア</h7>
                            <div class="score-grid">${scoreData}</div>
                        </div>
                        <div class="score-section">
                            <h7>📈 生データ</h7>
                            <div class="score-grid">${rawData}</div>
                        </div>
                    </div>
                    <div class="score-time">${new Date(score.timestamp).toLocaleString()}</div>
                </div>
            `;
        }).join('');

        return `
            <div class="scores-section">
                <div class="scores-grid">
                    ${scoresTable}
                </div>
            </div>
        `;
    }

    // 渲染决策记录标签页
    renderDecisionLogTab(decisionLog) {
        if (!decisionLog || decisionLog.length === 0) {
            return '<div class="no-data">📭 決定記録がありません</div>';
        }

        const decisionsTable = decisionLog.map(decision => `
            <div class="decision-card">
                <div class="decision-header">
                    <h6>年: ${decision.year}</h6>
                    <div class="decision-scenario">${decision.scenario_name || 'N/A'}</div>
                </div>
                <div class="decision-params">
                    <div class="param-grid">
                        <div class="param-item">
                            <span class="param-label">植林・森林保全:</span>
                            <span class="param-value">${decision.planting_trees_amount || 0}</span>
                        </div>
                        <div class="param-item">
                            <span class="param-label">住宅移転・嵩上げ:</span>
                            <span class="param-value">${decision.house_migration_amount || 0}</span>
                        </div>
                        <div class="param-item">
                            <span class="param-label">ダム・堤防工事:</span>
                            <span class="param-value">${decision.dam_levee_construction_cost || 0}</span>
                        </div>
                        <div class="param-item">
                            <span class="param-label">田んぼダム工事:</span>
                            <span class="param-value">${decision.paddy_dam_construction_cost || 0}</span>
                        </div>
                        <div class="param-item">
                            <span class="param-label">防災訓練・普及啓発:</span>
                            <span class="param-value">${decision.capacity_building_cost || 0}</span>
                        </div>
                        <div class="param-item">
                            <span class="param-label">交通網の拡充:</span>
                            <span class="param-value">${decision.transportation_invest || 0}</span>
                        </div>
                        <div class="param-item">
                            <span class="param-label">農業研究開発:</span>
                            <span class="param-value">${decision.agricultural_RnD_cost || 0}</span>
                        </div>
                        <div class="param-item">
                            <span class="param-label">気候パラメータ:</span>
                            <span class="param-value">${decision.cp_climate_params || 0}</span>
                        </div>
                    </div>
                </div>
                <div class="decision-time">${decision.timestamp ? new Date(decision.timestamp).toLocaleString() : 'N/A'}</div>
            </div>
        `).join('');

        return `
            <div class="decisions-section">
                <div class="decisions-list">
                    ${decisionsTable}
                </div>
            </div>
        `;
    }

    // 渲染参数区域标签页
    renderParameterZonesTab(parameterZones) {
        if (!parameterZones || parameterZones.length === 0) {
            return '<div class="no-data">📭 パラメータ設定がありません</div>';
        }

        const zonesTable = parameterZones.map(zone => `
            <div class="zone-card">
                <div class="zone-header">
                    <h6>${zone.param}</h6>
                </div>
                <div class="zone-coords">
                    <div class="coord-grid">
                        <div class="coord-item">
                            <span class="coord-label">X範囲:</span>
                            <span class="coord-value">${zone.x_min} - ${zone.x_max}</span>
                        </div>
                        <div class="coord-item">
                            <span class="coord-label">Y範囲:</span>
                            <span class="coord-value">${zone.y_min} - ${zone.y_max}</span>
                        </div>
                        <div class="coord-item">
                            <span class="coord-label">中央値:</span>
                            <span class="coord-value">${zone.mid || 'N/A'}</span>
                        </div>
                        <div class="coord-item">
                            <span class="coord-label">最大値:</span>
                            <span class="coord-value">${zone.max || 'N/A'}</span>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        return `
            <div class="zones-section">
                <div class="zones-grid">
                    ${zonesTable}
                </div>
            </div>
        `;
    }

    // 渲染用户信息标签页
    renderUserInfoTab(userData) {
        const firstActivity = userData.statistics.first_activity ?
            new Date(userData.statistics.first_activity).toLocaleString() : 'N/A';
        const lastActivity = userData.statistics.last_activity ?
            new Date(userData.statistics.last_activity).toLocaleString() : 'N/A';

        return `
            <div class="user-info-section">
                <div class="info-cards">
                    <div class="info-card">
                        <h6>👤 基本情報</h6>
                        <div class="info-grid">
                            <div class="info-item">
                                <span class="info-label">ユーザー名:</span>
                                <span class="info-value">${userData.user_name}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">登録状況:</span>
                                <span class="info-value ${userData.user_info.registered ? 'registered' : 'not-registered'}">
                                    ${userData.user_info.registered ? '✅ 登録済み' : '❌ 未登録'}
                                </span>
                            </div>
                        </div>
                    </div>

                    <div class="info-card">
                        <h6>📊 活動統計</h6>
                        <div class="info-grid">
                            <div class="info-item">
                                <span class="info-label">総操作数:</span>
                                <span class="info-value">${userData.statistics.total_actions}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">決定記録数:</span>
                                <span class="info-value">${userData.statistics.total_decisions}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">シミュレーション期間:</span>
                                <span class="info-value">${userData.statistics.simulation_periods}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">操作タイプ数:</span>
                                <span class="info-value">${Object.keys(userData.statistics.action_types || {}).length}</span>
                            </div>
                        </div>
                    </div>

                    <div class="info-card">
                        <h6>⏰ 活動期間</h6>
                        <div class="info-grid">
                            <div class="info-item">
                                <span class="info-label">初回活動:</span>
                                <span class="info-value">${firstActivity}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">最終活動:</span>
                                <span class="info-value">${lastActivity}</span>
                            </div>
                        </div>
                    </div>

                    <div class="info-card">
                        <h6>📁 データファイル状況</h6>
                        <div class="info-grid">
                            <div class="info-item">
                                <span class="info-label">操作ログ:</span>
                                <span class="info-value ${userData.statistics.data_files_found.user_logs ? 'found' : 'not-found'}">
                                    ${userData.statistics.data_files_found.user_logs ? '✅ あり' : '❌ なし'}
                                </span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">評価データ:</span>
                                <span class="info-value ${userData.statistics.data_files_found.block_scores ? 'found' : 'not-found'}">
                                    ${userData.statistics.data_files_found.block_scores ? '✅ あり' : '❌ なし'}
                                </span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">決定記録:</span>
                                <span class="info-value ${userData.statistics.data_files_found.decision_log ? 'found' : 'not-found'}">
                                    ${userData.statistics.data_files_found.decision_log ? '✅ あり' : '❌ なし'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // 导出用户数据功能
    exportUserData(userName, dataType) {
        try {
            const modal = document.getElementById('user-modal');
            const userData = this.currentUserData; // 需要保存当前用户数据

            if (!userData) {
                this.showError('ユーザーデータが見つかりません');
                return;
            }

            let dataToExport = [];
            let filename = '';

            switch (dataType) {
                case 'user_logs':
                    dataToExport = userData.user_logs;
                    filename = `${userName}_user_logs_${new Date().toISOString().slice(0, 10)}.json`;
                    break;
                case 'block_scores':
                    dataToExport = userData.block_scores;
                    filename = `${userName}_block_scores_${new Date().toISOString().slice(0, 10)}.json`;
                    break;
                case 'decision_log':
                    dataToExport = userData.decision_log;
                    filename = `${userName}_decision_log_${new Date().toISOString().slice(0, 10)}.json`;
                    break;
                default:
                    this.showError('不明なデータタイプです');
                    return;
            }

            // 创建下载链接
            const dataStr = JSON.stringify(dataToExport, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);

            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

            console.log(`✅ ${dataType} データをエクスポートしました: ${filename}`);
        } catch (error) {
            console.error('データエクスポートエラー:', error);
            this.showError('データのエクスポートに失敗しました');
        }
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

