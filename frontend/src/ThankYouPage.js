import React from 'react';
import './App.css';

const ThankYouPage = () => {
  return (
    <div className="App">
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        padding: '20px',
        textAlign: 'center'
      }}>
        <h1 style={{ 
          fontSize: '3rem', 
          marginBottom: '2rem',
          color: '#2c3e50'
        }}>
          🎉 ありがとうございました！
        </h1>
        
        <div style={{
          maxWidth: '600px',
          fontSize: '1.2rem',
          lineHeight: '1.6',
          color: '#555'
        }}>
          <p style={{ marginBottom: '1.5rem' }}>
            気候変化適応策シミュレーションにご参加いただき、ありがとうございました。
          </p>
          
          <p style={{ marginBottom: '1.5rem' }}>
            あなたの決策データは正常に保存されました。
            研究の発展にご協力いただき、心より感謝申し上げます。
          </p>
          
          <p style={{ marginBottom: '2rem' }}>
            今後ともよろしくお願いいたします。
          </p>
        </div>
        
        <button 
          onClick={() => window.location.href = '/'}
          style={{
            padding: '12px 30px',
            fontSize: '1.1rem',
            backgroundColor: '#3498db',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer',
            transition: 'background-color 0.3s'
          }}
          onMouseOver={(e) => e.target.style.backgroundColor = '#2980b9'}
          onMouseOut={(e) => e.target.style.backgroundColor = '#3498db'}
        >
          ホームに戻る
        </button>
      </div>
    </div>
  );
};

export default ThankYouPage;
