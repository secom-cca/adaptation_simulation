import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, Button, CircularProgress, Alert } from '@mui/material';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "https://web-production-5fb04.up.railway.app";

function ThankYouPage() {
  const [userLogs, setUserLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [userName, setUserName] = useState('');

  useEffect(() => {
    // 从URL参数获取用户名
    const urlParams = new URLSearchParams(window.location.search);
    const user = urlParams.get('user');
    if (user) {
      setUserName(decodeURIComponent(user));
      fetchUserLogs(user);
    } else {
      setError('用户名未找到');
      setLoading(false);
    }
  }, []);

  const fetchUserLogs = async (user) => {
    try {
      setLoading(true);
      const response = await axios.get(`${BACKEND_URL}/user-logs/${encodeURIComponent(user)}`);
      setUserLogs(response.data.logs || []);
    } catch (err) {
      console.error('获取用户日志失败:', err);
      setError('无法获取用户数据');
    } finally {
      setLoading(false);
    }
  };

  const handleBackToHome = () => {
    window.location.href = '/';
  };

  if (loading) {
    return (
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '100vh',
        flexDirection: 'column',
        gap: 2
      }}>
        <CircularProgress />
        <Typography>加载用户数据中...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '100vh',
        flexDirection: 'column',
        gap: 2,
        p: 3
      }}>
        <Alert severity="error">{error}</Alert>
        <Button variant="contained" onClick={handleBackToHome}>
          返回首页
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ 
      padding: 4, 
      backgroundColor: '#f5f7fa', 
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center'
    }}>
      {/* 感谢信息 */}
      <Paper sx={{ 
        p: 4, 
        mb: 4, 
        textAlign: 'center',
        maxWidth: 800,
        width: '100%'
      }}>
        <Typography variant="h3" color="primary" gutterBottom>
          ありがとうございました！
        </Typography>
        <Typography variant="h5" color="text.secondary" gutterBottom>
          Thank You!
        </Typography>
        <Typography variant="body1" sx={{ mt: 2, mb: 3 }}>
          {userName} さん、気候変動適応策検討シミュレーションにご参加いただき、ありがとうございました。
        </Typography>
        <Typography variant="body2" color="text.secondary">
          あなたの実験データは正常に記録されました。以下で確認できます。
        </Typography>
      </Paper>

      {/* 用户数据显示 */}
      <Paper sx={{ 
        p: 3, 
        maxWidth: 1200,
        width: '100%'
      }}>
        <Typography variant="h6" gutterBottom>
          実験データ (Raw Log Data)
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          記録された操作ログ: {userLogs.length} 件
        </Typography>
        
        <Box sx={{ 
          maxHeight: 400, 
          overflow: 'auto',
          backgroundColor: '#f8f9fa',
          p: 2,
          borderRadius: 1,
          border: '1px solid #e0e0e0'
        }}>
          {userLogs.length > 0 ? (
            <pre style={{ 
              margin: 0, 
              fontSize: '12px', 
              lineHeight: 1.4,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}>
              {userLogs.map((log, index) => (
                <div key={index} style={{ marginBottom: '8px', padding: '4px', backgroundColor: '#fff', borderRadius: '4px' }}>
                  {JSON.stringify(log, null, 2)}
                </div>
              ))}
            </pre>
          ) : (
            <Typography color="text.secondary">
              データが見つかりませんでした。
            </Typography>
          )}
        </Box>
      </Paper>

      {/* 操作按钮 */}
      <Box sx={{ mt: 4, display: 'flex', gap: 2 }}>
        <Button 
          variant="contained" 
          color="primary" 
          onClick={handleBackToHome}
          size="large"
        >
          新しい実験を開始
        </Button>
        <Button 
          variant="outlined" 
          onClick={() => window.print()}
          size="large"
        >
          データを印刷
        </Button>
      </Box>
    </Box>
  );
}

export default ThankYouPage;
