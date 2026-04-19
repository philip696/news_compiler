/**
 * WeChat Login QR Code Component
 * Handles WeChat OAuth flow with QR code display and polling
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import QRCode from 'qrcode.react';
import { generateWeChatQRCode, checkWeChatLoginStatus } from '@/services/wechatApi';

interface WeChatLoginQRProps {
  onLoginSuccess?: (user: any, accessToken: string) => void;
  onLoginError?: (error: string) => void;
  onClose?: () => void;
}

interface LoginState {
  status: 'idle' | 'loading' | 'waiting' | 'success' | 'error';
  authUrl?: string;
  state?: string;
  errorMessage?: string;
  user?: any;
  accessToken?: string;
}

/**
 * WeChatLoginQR Component
 * 
 * Flow:
 * 1. User clicks to open modal
 * 2. Component generates QR code via POST /api/wechat-auth/qrcode/generate
 * 3. User scans QR with WeChat app
 * 4. Component polls status via GET /api/wechat-auth/status?state={state}
 * 5. On completion, returns user data and access_token
 */
export default function WeChatLoginQR({ 
  onLoginSuccess, 
  onLoginError, 
  onClose 
}: WeChatLoginQRProps) {
  const [loginState, setLoginState] = useState<LoginState>({ status: 'idle' });
  const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null);

  /**
   * Initialize QR code generation
   */
  const initializeQRCode = useCallback(async () => {
    try {
      setLoginState({ status: 'loading' });
      const response = await generateWeChatQRCode();
      
      if (response.status === 'success' && response.auth_url && response.state) {
        setLoginState({
          status: 'waiting',
          authUrl: response.auth_url,
          state: response.state,
        });
        // Start polling for login completion
        startPolling(response.state);
      } else {
        throw new Error(response.error || 'Failed to generate QR code');
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      setLoginState({
        status: 'error',
        errorMessage: errorMsg,
      });
      onLoginError?.(errorMsg);
    }
  }, [onLoginError]);

  /**
   * Poll status endpoint for login completion
   */
  const startPolling = useCallback((state: string) => {
    // Clear any existing interval
    if (pollInterval) clearInterval(pollInterval);

    // Poll every 1 second (WeChat login typically completes quickly)
    const interval = setInterval(async () => {
      try {
        const response = await checkWeChatLoginStatus(state);

        if (response.status === 'completed') {
          setLoginState({
            status: 'success',
            user: response.user,
            accessToken: response.access_token,
          });
          
          // Clear polling
          clearInterval(interval);
          setPollInterval(null);

          // Call success callback
          onLoginSuccess?.(response.user, response.access_token);
        } else if (response.status === 'expired' || response.status === 'error') {
          setLoginState({
            status: 'error',
            errorMessage: response.status === 'expired' 
              ? 'QR code expired. Please try again.'
              : 'Login failed. Please try again.',
          });
          clearInterval(interval);
          setPollInterval(null);
        }
        // 'pending' status: continue polling
      } catch (error) {
        console.error('Polling error:', error);
        // Continue polling even on error (connection issues)
      }
    }, 1000);

    setPollInterval(interval);
  }, [pollInterval, onLoginSuccess]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [pollInterval]);

  /**
   * Start QR generation on mount
   */
  useEffect(() => {
    if (loginState.status === 'idle') {
      initializeQRCode();
    }
  }, []);

  return (
    <div className="wechat-login-qr-container">
      <div className="modal-header">
        <h2>WeChat Login</h2>
        <button 
          className="close-btn" 
          onClick={onClose}
          aria-label="Close"
        >
          ✕
        </button>
      </div>

      <div className="modal-content">
        {loginState.status === 'loading' && (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Generating QR code...</p>
          </div>
        )}

        {loginState.status === 'waiting' && loginState.authUrl && (
          <div className="waiting-state">
            <div className="qr-code-container">
              <QRCode 
                value={loginState.authUrl}
                size={256}
                level="H"
                includeMargin={true}
                fgColor="#000000"
                bgColor="#ffffff"
              />
            </div>
            <p className="instruction">
              Scan this QR code with your WeChat app to log in
            </p>
            <div className="status-indicator">
              <div className="pulse"></div>
              <span>Waiting for scan...</span>
            </div>
          </div>
        )}

        {loginState.status === 'success' && loginState.user && (
          <div className="success-state">
            <div className="success-icon">✓</div>
            <h3>Login Successful!</h3>
            <p>Welcome, {loginState.user.nickname}</p>
            {loginState.user.avatar && (
              <img 
                src={loginState.user.avatar} 
                alt={loginState.user.nickname}
                className="avatar"
              />
            )}
          </div>
        )}

        {loginState.status === 'error' && (
          <div className="error-state">
            <div className="error-icon">!</div>
            <p>{loginState.errorMessage}</p>
            <button 
              className="retry-btn"
              onClick={() => {
                setLoginState({ status: 'idle' });
                initializeQRCode();
              }}
            >
              Try Again
            </button>
          </div>
        )}
      </div>

      <style jsx>{`
        .wechat-login-qr-container {
          width: 100%;
          max-width: 400px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
          overflow: hidden;
        }

        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 20px;
          border-bottom: 1px solid #f0f0f0;
        }

        .modal-header h2 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
          color: #333;
        }

        .close-btn {
          background: none;
          border: none;
          font-size: 24px;
          color: #999;
          cursor: pointer;
          padding: 0;
          width: 32px;
          height: 32px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
          transition: background-color 0.2s;
        }

        .close-btn:hover {
          background-color: #f5f5f5;
        }

        .modal-content {
          padding: 40px 20px;
          text-align: center;
          min-height: 400px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
        }

        .loading-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 20px;
        }

        .spinner {
          width: 40px;
          height: 40px;
          border: 3px solid #f0f0f0;
          border-top: 3px solid #09b83e;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .waiting-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 20px;
        }

        .qr-code-container {
          padding: 12px;
          border: 2px solid #f0f0f0;
          border-radius: 8px;
          background: #fafafa;
        }

        .instruction {
          margin: 0;
          font-size: 14px;
          color: #666;
          font-weight: 500;
        }

        .status-indicator {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
          color: #999;
        }

        .pulse {
          width: 8px;
          height: 8px;
          background-color: #09b83e;
          border-radius: 50%;
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        .success-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 16px;
        }

        .success-icon {
          font-size: 48px;
          color: #09b83e;
          animation: scaleIn 0.3s ease-out;
        }

        @keyframes scaleIn {
          from {
            transform: scale(0);
          }
          to {
            transform: scale(1);
          }
        }

        .success-state h3 {
          margin: 0;
          font-size: 16px;
          color: #333;
        }

        .avatar {
          width: 48px;
          height: 48px;
          border-radius: 50%;
          object-fit: cover;
        }

        .error-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
        }

        .error-icon {
          font-size: 48px;
          color: #ff6b6b;
        }

        .error-state p {
          margin: 0;
          font-size: 14px;
          color: #666;
          max-width: 280px;
        }

        .retry-btn {
          margin-top: 8px;
          padding: 8px 24px;
          background-color: #09b83e;
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: background-color 0.2s;
        }

        .retry-btn:hover {
          background-color: #08a432;
        }

        .retry-btn:active {
          transform: scale(0.98);
        }
      `}</style>
    </div>
  );
}
