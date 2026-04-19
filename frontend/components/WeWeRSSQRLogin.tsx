/**
 * WeChat + WeWe-RSS Integration Component
 * Allows users to scan QR code to authenticate with WeChat,
 * then use that account to add WeChat articles from WeWe-RSS
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';

interface WeWeRSSAccount {
  vid: string;
  username: string;
  created_at?: string;
}

interface Props {
  onAccountAdded?: (account: WeWeRSSAccount) => void;
  onError?: (error: string) => void;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

interface LoginState {
  status: 'idle' | 'loading' | 'waiting' | 'success' | 'error';
  scanUrl?: string;
  loginId?: string;
  account?: WeWeRSSAccount;
  errorMessage?: string;
}

/**
 * WeChat + WeWe-RSS QR Login Component
 * 
 * Flow:
 * 1. Click to start login
 * 2. Generate QR code by calling POST /api/wewe-rss/auth/qrcode
 * 3. User scans QR with WeChat app
 * 4. Component polls GET /api/wewe-rss/auth/status?login_id={id}
 * 5. On completion, account is stored and ready to fetch articles
 */
export default function WeWeRSSQRLogin({ onAccountAdded, onError }: Props) {
  const [loginState, setLoginState] = useState<LoginState>({ status: 'idle' });
  const [accounts, setAccounts] = useState<WeWeRSSAccount[]>([]);
  const [showAccountList, setShowAccountList] = useState(false);
  const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null);

  /**
   * Load existing accounts
   */
  const loadAccounts = useCallback(async () => {
    try {
      const response = await api.get('/api/wewe-rss/accounts');
      setAccounts(response.data.accounts || []);
    } catch (error) {
      console.error('Failed to load accounts:', error);
    }
  }, []);

  /**
   * Initialize login by fetching the WeChat login URL
   * This URL will be encoded as a QR code for the user to scan
   */
  const initializeQRCode = useCallback(async () => {
    try {
      setLoginState({ status: 'loading' });
      
      // Get the login URL from WeWe-RSS platform via our backend
      const response = await api.get('/api/wewe-rss/auth/login-url');
      const data = response.data;
      
      if (data.status === 'success' && data.scan_url && data.login_id) {
        setLoginState({
          status: 'waiting',
          scanUrl: data.scan_url,
          loginId: data.login_id
        });
        startPolling(data.login_id);
      } else {
        throw new Error(data.message || 'Failed to get login URL');
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      setLoginState({ status: 'error', errorMessage: errorMsg });
      onError?.(errorMsg);
    }
  }, [onError]);

  /**
   * Poll status endpoint for login completion
   */
  const startPolling = useCallback((loginId: string) => {
    if (pollInterval) clearInterval(pollInterval);

    const interval = setInterval(async () => {
      try {
        const response = await api.get(
          `/api/wewe-rss/auth/status?login_id=${loginId}`
        );
        const data = response.data;

        if (data.status === 'completed') {
          const newAccount: WeWeRSSAccount = {
            vid: data.account_id,
            username: data.account_name,
            created_at: new Date().toISOString()
          };

          setLoginState({
            status: 'success',
            account: newAccount
          });

          // Reload accounts list
          await loadAccounts();
          onAccountAdded?.(newAccount);

          clearInterval(interval);
          setPollInterval(null);
        } else if (data.status === 'error') {
          setLoginState({
            status: 'error',
            errorMessage: data.message || 'Login failed'
          });
          clearInterval(interval);
          setPollInterval(null);
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 1000);

    setPollInterval(interval);
  }, [pollInterval, loadAccounts, onAccountAdded]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    loadAccounts();
    
    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [pollInterval, loadAccounts]);

  /**
   * Retry login
   */
  const handleRetry = () => {
    setLoginState({ status: 'idle' });
    initializeQRCode();
  };

  /**
   * Remove account
   */
  const handleRemoveAccount = async (vid: string) => {
    try {
      await api.delete(`/api/wewe-rss/accounts/${vid}`);
      setAccounts(accounts.filter(acc => acc.vid !== vid));
    } catch (error) {
      console.error('Failed to remove account:', error);
    }
  };

  return (
    <div className="wewe-rss-qr-container" style={styles.container}>
      <div style={styles.header}>
        <h2>WeChat Article Sources</h2>
        <p style={styles.subtitle}>Add WeChat official accounts via WeWe-RSS</p>
      </div>

      {/* QR Code Login Section */}
      {loginState.status === 'idle' && (
        <button onClick={initializeQRCode} style={styles.primaryButton}>
          + Add Account
        </button>
      )}

      {/* Loading State */}
      {loginState.status === 'loading' && (
        <div style={styles.centerContent}>
          <div style={styles.spinner}></div>
          <p>Getting login URL...</p>
        </div>
      )}

      {/* Waiting for Scan */}
      {loginState.status === 'waiting' && loginState.scanUrl && (
        <div style={styles.centerContent}>
          <div style={styles.qrCodeWrapper}>
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(loginState.scanUrl)}`}
              alt="WeChat QR Code"
              style={{ width: '200px', height: '200px' }}
            />
          </div>
          <p style={styles.instruction}>
            Scan this QR code with WeChat to authenticate
          </p>
          <div style={{ ...styles.pulse, marginTop: '16px' }}>
            <div style={styles.pulseDot}></div>
            <span>Waiting for authorization...</span>
          </div>
        </div>
      )}

      {/* Success State */}
      {loginState.status === 'success' && loginState.account && (
        <div style={styles.successBox}>
          <div style={styles.checkmark}>✓</div>
          <p>Account Connected!</p>
          <p style={styles.accountName}>{loginState.account.username}</p>
          <button
            onClick={() => {
              setLoginState({ status: 'idle' });
              loadAccounts();
            }}
            style={styles.secondaryButton}
          >
            Add Another Account
          </button>
        </div>
      )}

      {/* Error State */}
      {loginState.status === 'error' && (
        <div style={styles.errorBox}>
          <div style={styles.errorIcon}>!</div>
          <p>{loginState.errorMessage}</p>
          <button onClick={handleRetry} style={styles.primaryButton}>
            Try Again
          </button>
        </div>
      )}

      {/* Accounts List */}
      {accounts.length > 0 && (
        <div style={styles.accountsList}>
          <div
            style={styles.accountsHeader}
            onClick={() => setShowAccountList(!showAccountList)}
          >
            <span>Connected Accounts ({accounts.length})</span>
            <span style={styles.toggle}>{showAccountList ? '▼' : '▶'}</span>
          </div>

          {showAccountList && (
            <div style={styles.accountsContent}>
              {accounts.map((account) => (
                <div key={account.vid} style={styles.accountItem}>
                  <div>
                    <p style={styles.accountUsername}>{account.username}</p>
                    <p style={styles.accountId}>ID: {account.vid}</p>
                  </div>
                  <button
                    onClick={() => handleRemoveAccount(account.vid)}
                    style={styles.removeButton}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}

const styles = {
  container: {
    padding: '24px',
    backgroundColor: '#fff',
    borderRadius: '12px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
    maxWidth: '500px',
    margin: '0 auto'
  } as React.CSSProperties,

  header: {
    marginBottom: '24px'
  } as React.CSSProperties,

  subtitle: {
    fontSize: '14px',
    color: '#666',
    margin: '8px 0 0 0'
  } as React.CSSProperties,

  centerContent: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    gap: '16px',
    padding: '32px 0'
  } as React.CSSProperties,

  spinner: {
    width: '40px',
    height: '40px',
    border: '3px solid #f0f0f0',
    borderTop: '3px solid #09b83e',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite'
  } as React.CSSProperties,

  qrCodeWrapper: {
    padding: '12px',
    backgroundColor: '#fafafa',
    borderRadius: '8px',
    border: '2px solid #f0f0f0'
  } as React.CSSProperties,

  instruction: {
    fontSize: '14px',
    color: '#666',
    textAlign: 'center' as const,
    margin: '0'
  } as React.CSSProperties,

  pulse: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '12px',
    color: '#999'
  } as React.CSSProperties,

  pulseDot: {
    width: '8px',
    height: '8px',
    backgroundColor: '#09b83e',
    borderRadius: '50%',
    animation: 'pulse 2s infinite'
  } as React.CSSProperties,

  primaryButton: {
    width: '100%',
    padding: '12px 24px',
    backgroundColor: '#09b83e',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'background-color 0.2s'
  } as React.CSSProperties,

  secondaryButton: {
    padding: '8px 16px',
    backgroundColor: '#f5f5f5',
    color: '#333',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer'
  } as React.CSSProperties,

  successBox: {
    textAlign: 'center' as const,
    padding: '24px',
    backgroundColor: '#f0f9f6',
    borderRadius: '8px',
    margin: '16px 0'
  } as React.CSSProperties,

  checkmark: {
    fontSize: '48px',
    color: '#09b83e',
    marginBottom: '8px'
  } as React.CSSProperties,

  accountName: {
    fontSize: '14px',
    color: '#999',
    margin: '8px 0 16px 0'
  } as React.CSSProperties,

  errorBox: {
    textAlign: 'center' as const,
    padding: '24px',
    backgroundColor: '#fef2f2',
    borderRadius: '8px',
    margin: '16px 0'
  } as React.CSSProperties,

  errorIcon: {
    fontSize: '48px',
    color: '#ff6b6b',
    marginBottom: '8px'
  } as React.CSSProperties,

  accountsList: {
    marginTop: '24px',
    borderTop: '1px solid #f0f0f0',
    paddingTop: '16px'
  } as React.CSSProperties,

  accountsHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px',
    cursor: 'pointer',
    backgroundColor: '#fafafa',
    borderRadius: '6px',
    fontWeight: '600',
    fontSize: '14px'
  } as React.CSSProperties,

  toggle: {
    fontSize: '12px',
    transition: 'transform 0.2s'
  } as React.CSSProperties,

  accountsContent: {
    marginTop: '12px',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px'
  } as React.CSSProperties,

  accountItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px',
    backgroundColor: '#fafafa',
    borderRadius: '6px',
    fontSize: '14px'
  } as React.CSSProperties,

  accountUsername: {
    fontWeight: '600',
    margin: '0 0 4px 0'
  } as React.CSSProperties,

  accountId: {
    fontSize: '12px',
    color: '#999',
    margin: '0'
  } as React.CSSProperties,

  removeButton: {
    padding: '6px 12px',
    backgroundColor: '#fff',
    color: '#ff6b6b',
    border: '1px solid #ff6b6b',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer',
    transition: 'all 0.2s'
  } as React.CSSProperties
};
