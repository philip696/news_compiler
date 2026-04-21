'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { QRCodeSVG } from 'qrcode.react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8007';

// Read the GEB JWT stored by the main auth flow
const getGebToken = (): string | null => {
  try {
    if (typeof window === 'undefined') return null;
    const raw = localStorage.getItem('auth-storage');
    if (!raw) return null;
    return JSON.parse(raw)?.state?.token ?? null;
  } catch {
    return null;
  }
};

const authHeaders = () => ({
  Authorization: `Bearer ${getGebToken()}`,
});

type WeChatAuthState =
  | 'idle'
  | 'loading_qr'
  | 'polling'
  | 'linked'
  | 'error'
  | 'qr_expired';

interface WeReadAccount {
  id: string;    // vid
  name: string;
  status: number;
  blockedToday: boolean;
}

interface Feed {
  id: string;    // mp_id
  mpName: string;
  mpCover: string;
  mpIntro: string;
  updateTime: number;
  syncTime: number;
  articleCount: number;
}

export default function WeChatOfficialAccounts({ onLogin }: { onLogin?: () => void }) {
  const queryClient = useQueryClient();
  const [qrState, setQrState] = useState<WeChatAuthState>('idle');
  const [uuid, setUuid] = useState<string>('');
  const [scanUrl, setScanUrl] = useState<string>('');
  const [qrTimer, setQrTimer] = useState<number>(60);
  const [error, setError] = useState<string>('');
  const [shareUrl, setShareUrl] = useState<string>('');
  const [syncingMp, setSyncingMp] = useState<string | null>(null);

  const gebToken = getGebToken();

  // ── QR timer countdown ──────────────────────────────────────────────── //
  useEffect(() => {
    if (qrState !== 'polling') return;
    if (qrTimer <= 0) {
      setQrState('qr_expired');
      setError('QR code expired. Please try again.');
      return;
    }
    const t = setTimeout(() => setQrTimer((v) => v - 1), 1000);
    return () => clearTimeout(t);
  }, [qrTimer, qrState]);

  // ── GET QR ──────────────────────────────────────────────────────────── //
  const startQrMutation = useMutation({
    mutationFn: async () => {
      const res = await axios.get(`${API_BASE}/api/wechat/qr`);
      return res.data as { uuid: string; scanUrl: string };
    },
    onSuccess: (data) => {
      setUuid(data.uuid);
      setScanUrl(data.scanUrl);
      setQrTimer(60);
      setQrState('polling');
      setError('');
    },
    onError: () => {
      setError('Could not generate QR code. Please try again.');
      setQrState('error');
    },
  });

  // ── POLL login-status ────────────────────────────────────────────────── //
  const { data: loginStatus } = useQuery({
    queryKey: ['wechatLoginStatus', uuid],
    queryFn: async () => {
      const res = await axios.get(`${API_BASE}/api/wechat/login-status`, {
        params: { uuid },
        headers: gebToken ? authHeaders() : {},
      });
      return res.data as { message: string; vid?: string; username?: string };
    },
    enabled: qrState === 'polling' && !!uuid,
    refetchInterval: 2000,
  });

  useEffect(() => {
    if (!loginStatus) return;
    if (loginStatus.message === 'success') {
      setQrState('linked');
      queryClient.invalidateQueries({ queryKey: ['wereadAccounts'] });
      onLogin?.();
    } else if (loginStatus.message === 'error') {
      setQrState('error');
      setError('Login failed. Please try again.');
    }
  }, [loginStatus]);

  // ── WeRead accounts (linked sessions) ───────────────────────────────── //
  const { data: accounts = [] } = useQuery<WeReadAccount[]>({
    queryKey: ['wereadAccounts'],
    queryFn: async () => {
      const res = await axios.get(`${API_BASE}/api/wechat/accounts`, {
        headers: authHeaders(),
      });
      return res.data;
    },
    enabled: !!gebToken,
  });

  const deleteAccountMutation = useMutation({
    mutationFn: async (vid: string) => {
      await axios.delete(`${API_BASE}/api/wechat/accounts/${vid}`, {
        headers: authHeaders(),
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['wereadAccounts'] }),
    onError: () => setError('Failed to remove account'),
  });

  // ── Official Account feeds ───────────────────────────────────────────── //
  const { data: feeds = [] } = useQuery<Feed[]>({
    queryKey: ['wereadFeeds'],
    queryFn: async () => {
      const res = await axios.get(`${API_BASE}/api/wechat/mps`, {
        headers: authHeaders(),
      });
      return res.data;
    },
    enabled: !!gebToken,
    refetchInterval: 5 * 60 * 1000,
  });

  // ── Add Official Account via share URL ──────────────────────────────── //
  const addFeedMutation = useMutation({
    mutationFn: async (wxsLink: string) => {
      const res = await axios.post(
        `${API_BASE}/api/wechat/mps`,
        { wxsLink },
        { headers: authHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      setShareUrl('');
      queryClient.invalidateQueries({ queryKey: ['wereadFeeds'] });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.error || err.response?.data?.detail || 'Failed to add account';
      setError(msg);
    },
  });

  // ── Remove feed ─────────────────────────────────────────────────────── //
  const deleteFeedMutation = useMutation({
    mutationFn: async (mpId: string) => {
      await axios.delete(`${API_BASE}/api/wechat/mps/${mpId}`, {
        headers: authHeaders(),
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['wereadFeeds'] }),
    onError: () => setError('Failed to remove account'),
  });

  // ── Sync feed ───────────────────────────────────────────────────────── //
  const syncFeed = async (mpId: string, history = false) => {
    setSyncingMp(mpId);
    try {
      await axios.post(
        `${API_BASE}/api/wechat/mps/${mpId}/sync${history ? '?history=1' : ''}`,
        {},
        { headers: authHeaders() }
      );
      queryClient.invalidateQueries({ queryKey: ['wereadFeeds'] });
    } catch (err: any) {
      setError(err.response?.data?.error || 'Sync failed');
    } finally {
      setSyncingMp(null);
    }
  };

  const formatTimeAgo = (ts: number | null) => {
    if (!ts) return 'Never';
    const secs = Math.floor(Date.now() / 1000 - ts);
    if (secs < 60) return 'just now';
    if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
    if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
    return `${Math.floor(secs / 86400)}d ago`;
  };

  // ── Render ──────────────────────────────────────────────────────────── //

  if (!gebToken) {
    return (
      <div className="wewe-sidebar-section space-y-4">
        <h2 className="text-lg font-bold text-slate-900">WeChat Official Accounts</h2>
        <div className="rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 p-6 text-center">
          <p className="text-sm text-slate-600 mb-2">
            Log in to GEB first to use WeChat features.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="wewe-sidebar-section space-y-4">
      <h2 className="text-lg font-bold text-slate-900">WeChat Official Accounts</h2>

      {/* ERROR BANNER */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-3 flex justify-between items-center">
          <span className="text-sm text-red-700">{error}</span>
          <button onClick={() => setError('')} className="text-red-400 hover:text-red-600 font-bold">×</button>
        </div>
      )}

      {/* ── LINK WEREAD ACCOUNT SECTION ── */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-slate-900">WeRead Session</h3>
          {accounts.length > 0 && (
            <span className="text-xs text-green-600 font-medium">
              ✅ {accounts.length} linked
            </span>
          )}
        </div>

        {/* QR states */}
        {qrState === 'idle' || qrState === 'error' || qrState === 'qr_expired' ? (
          <button
            onClick={() => {
              setQrState('loading_qr');
              startQrMutation.mutate();
            }}
            disabled={startQrMutation.isPending}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white font-semibold py-2 px-4 rounded-lg transition-colors text-sm"
          >
            {startQrMutation.isPending ? '⏳ Generating...' : '📱 Link WeRead Account'}
          </button>
        ) : qrState === 'loading_qr' ? (
          <div className="text-center py-4">
            <div className="animate-spin h-6 w-6 border-4 border-blue-200 border-t-blue-600 rounded-full mx-auto" />
        </div>
        ) : qrState === 'polling' ? (
          <div className="text-center space-y-2">
            <p className="text-sm font-medium text-slate-700">Scan with WeChat</p>
            {scanUrl ? (
              <div className="bg-white border-2 border-slate-200 p-3 rounded-lg inline-block">
                <QRCodeSVG value={scanUrl} size={160} />
        </div>
            ) : (
              <div className="w-40 h-40 bg-slate-100 flex items-center justify-center rounded-lg mx-auto">
                <div className="animate-spin h-6 w-6 border-4 border-blue-200 border-t-blue-600 rounded-full" />
              </div>
            )}
            <p className="text-xs text-slate-500">Open WeChat → [+] → Scan QR Code</p>
            <p className={`text-xs font-semibold ${qrTimer < 20 ? 'text-red-600' : 'text-slate-500'}`}>
              Expires in {qrTimer}s
            </p>
            <button
              onClick={() => { setQrState('loading_qr'); setQrTimer(60); startQrMutation.mutate(); }}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              🔄 Get new QR
            </button>
          </div>
        ) : qrState === 'linked' ? (
          <p className="text-sm text-green-700 font-medium text-center py-1">
            ✅ WeRead account linked!
          </p>
        ) : null}

        {/* Linked accounts list */}
        {accounts.length > 0 && (
          <div className="space-y-1 pt-1 border-t border-slate-100">
            {accounts.map((acc) => (
              <div key={acc.id} className="flex items-center justify-between text-sm py-1">
                <span className="text-slate-700 truncate max-w-[180px]">
                  {acc.name || acc.id}
                  {acc.blockedToday && <span className="ml-1 text-xs text-orange-500">(blocked today)</span>}
                </span>
          <button
                  onClick={() => deleteAccountMutation.mutate(acc.id)}
                  className="text-xs text-red-500 hover:text-red-700 ml-2 flex-shrink-0"
                >
                  Remove
          </button>
              </div>
            ))}
        </div>
      )}
      </div>

      {/* ── ADD OFFICIAL ACCOUNT SECTION ── */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
        <h3 className="font-semibold text-slate-900">Add Official Account</h3>
        <div className="flex flex-col gap-2">
          <input
            type="text"
            placeholder="https://mp.weixin.qq.com/s/..."
            value={shareUrl}
            onChange={(e) => setShareUrl(e.target.value)}
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={() => addFeedMutation.mutate(shareUrl)}
            disabled={!shareUrl || addFeedMutation.isPending}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white font-semibold py-2 px-3 rounded-lg transition-colors text-sm"
          >
            {addFeedMutation.isPending ? '⏳ Adding…' : 'Add Account'}
          </button>
        </div>
        <p className="text-xs text-slate-500">
          Paste any article link from the official account you want to follow.
            </p>
          </div>

      {/* ── MY OFFICIAL ACCOUNTS ── */}
      {feeds.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-2">
          <h3 className="font-semibold text-slate-900">My Accounts</h3>
          {feeds.map((feed) => (
            <div key={feed.id} className="border border-slate-100 rounded-lg p-3 hover:bg-slate-50 transition-colors">
              <div className="flex items-start gap-2">
                {feed.mpCover && (
                  <img src={feed.mpCover} alt={feed.mpName} className="w-8 h-8 rounded-full object-cover flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-sm text-slate-900 truncate">{feed.mpName || feed.id}</h4>
                  <p className="text-xs text-slate-500 mt-0.5">
                    📊 {feed.articleCount} articles · synced {formatTimeAgo(feed.syncTime)}
                  </p>
                </div>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                <a
                  href={`/wechat-feed?account=${feed.id}`}
                        className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                      >
                        View Articles
                      </a>
                <button
                  onClick={() => syncFeed(feed.id)}
                  disabled={syncingMp === feed.id}
                  className="text-xs text-indigo-600 hover:text-indigo-700 font-medium disabled:opacity-50"
                >
                  {syncingMp === feed.id ? '⏳ Syncing…' : '🔄 Sync'}
                </button>
                      <button
                        onClick={() => {
                    if (confirm('Remove this account?')) deleteFeedMutation.mutate(feed.id);
                        }}
                        className="text-xs text-red-600 hover:text-red-700 font-medium"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
        </div>
      )}
    </div>
  );
}
