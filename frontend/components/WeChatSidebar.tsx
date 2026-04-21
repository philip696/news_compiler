import { useState } from "react";
import type { WeChatAccount } from "../services/wechatApi";
import {
  removeWeChatAccount,
  updateWeChatAccount,
  muteAccount,
  unmuteAccount,
} from "../services/wechatApi";

interface WeChatSidebarProps {
  accounts: WeChatAccount[];
  loading?: boolean;
  onAccountSelect?: (account: WeChatAccount) => void;
  selectedAccountId?: string;
  onAddClick?: () => void;
  onAccountsChange?: () => void;
}

function label(a: WeChatAccount): string {
  return a.mpName || a.name || a.wechat_account_name || a.id;
}

export function WeChatSidebar(props: WeChatSidebarProps) {
  const {
    accounts,
    loading,
    onAccountSelect,
    selectedAccountId,
    onAddClick,
    onAccountsChange,
  } = props;
  const [deleting, setDeleting] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);
  const [togglingMute, setTogglingMute] = useState<string | null>(null);

  const handleUpdate = async (accountId: string) => {
    setUpdating(accountId);
    try {
      await updateWeChatAccount(accountId);
      onAccountsChange?.();
    } catch (error) {
      console.error("Failed to refresh feed:", error);
    } finally {
      setUpdating(null);
    }
  };

  const handleToggleMute = async (accountId: string, isMuted: boolean) => {
    setTogglingMute(accountId);
    try {
      if (isMuted) {
        await unmuteAccount(accountId);
      } else {
        await muteAccount(accountId);
      }
      onAccountsChange?.();
    } catch (error) {
      console.error("Mute toggle failed:", error);
    } finally {
      setTogglingMute(null);
    }
  };

  const handleDelete = async (accountId: string) => {
    if (!confirm("Remove this account?")) return;
    setDeleting(accountId);
    try {
      await removeWeChatAccount(accountId);
      onAccountsChange?.();
    } catch (error) {
      console.error("Failed to remove:", error);
    } finally {
      setDeleting(null);
    }
  };

  return (
    <aside className="w-full max-w-sm border-r border-slate-200 bg-white min-h-screen">
      <div className="p-6 border-b border-slate-200">
        <h2 className="text-lg font-bold text-slate-900 mb-4">Accounts</h2>
        <button
          type="button"
          onClick={onAddClick}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Add account
        </button>
      </div>
      <div className="p-4 overflow-y-auto">
        {loading ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : accounts.length === 0 ? (
          <p className="text-sm text-slate-500">No accounts yet.</p>
        ) : (
          accounts.map((account) => (
            <div
              key={account.id}
              role="button"
              tabIndex={0}
              onClick={() => onAccountSelect?.(account)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") onAccountSelect?.(account);
              }}
              className={`flex gap-3 p-3 rounded-lg mb-2 cursor-pointer border ${
                selectedAccountId === account.id
                  ? "border-blue-500 bg-blue-50"
                  : "border-transparent hover:bg-slate-50"
              }`}
            >
              {account.mpCover || account.wechat_account_avatar ? (
                <img
                  src={account.mpCover || account.wechat_account_avatar}
                  alt=""
                  className="w-10 h-10 rounded-full object-cover shrink-0"
                />
              ) : (
                <div className="w-10 h-10 rounded-full bg-slate-200 shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold truncate">{label(account)}</h3>
                <p className="text-xs text-slate-500 truncate">{account.id}</p>
                <div className="flex gap-1 mt-2 flex-wrap">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleUpdate(account.id);
                    }}
                    disabled={updating === account.id}
                    className="flex-1 text-xs bg-slate-100 px-2 py-1 rounded"
                  >
                    {updating === account.id ? "…" : "Refresh"}
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleToggleMute(account.id, !!account.is_muted);
                    }}
                    disabled={togglingMute === account.id}
                    className="flex-1 text-xs bg-amber-50 px-2 py-1 rounded"
                  >
                    {account.is_muted ? "Unmute" : "Mute"}
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(account.id);
                    }}
                    disabled={deleting === account.id}
                    className="flex-1 text-xs bg-red-50 text-red-700 px-2 py-1 rounded"
                  >
                    {deleting === account.id ? "…" : "Delete"}
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
