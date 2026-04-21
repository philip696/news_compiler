import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/router";
import { useWeChatStore } from "../../store/wechat";
import { WeChatAuthGuard } from "../../components/WeChatAuthGuard";
import { WeChatSidebar } from "../../components/WeChatSidebar";
import { AddWeChatModal } from "../../components/AddWeChatModal";
import { getWeChatAccounts, type WeChatAccount } from "../../services/wechatApi";

export default function WeChatAccountsPage() {
  const router = useRouter();
  const { wechatUser } = useWeChatStore();
  const [accounts, setAccounts] = useState<WeChatAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedAccount, setSelectedAccount] = useState<WeChatAccount | null>(
    null
  );
  const [showAddModal, setShowAddModal] = useState(false);

  const loadAccounts = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getWeChatAccounts();
      setAccounts(data);
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: string } }; message?: string };
      const errorMsg = ax.response?.data?.detail || ax.message;
      setError(String(errorMsg || "Failed to load accounts"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAccounts();
  }, [loadAccounts]);

  const label = (a: WeChatAccount) =>
    a.mpName || a.name || a.wechat_account_name || a.id;

  return (
    <WeChatAuthGuard>
      <div className="flex h-screen bg-slate-100">
        <WeChatSidebar
          accounts={accounts}
          loading={loading}
          onAccountSelect={(a) => setSelectedAccount(a)}
          selectedAccountId={selectedAccount?.id}
          onAddClick={() => setShowAddModal(true)}
          onAccountsChange={() => void loadAccounts()}
        />

        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-2xl font-bold text-slate-900">
                  WeChat feeds
                </h1>
                {wechatUser?.nickname ? (
                  <p className="text-sm text-slate-500 mt-1">
                    Signed in as {wechatUser.nickname}
                  </p>
                ) : null}
              </div>
              <button
                type="button"
                onClick={() => router.push("/")}
                className="px-4 py-2 text-slate-700 hover:bg-white rounded-lg border border-slate-200"
              >
                ? Home
              </button>
            </div>

            {error ? (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                {error}
              </div>
            ) : null}

            {!loading && accounts.length === 0 ? (
              <div className="rounded-xl border border-slate-200 bg-white p-12 text-center">
                <p className="text-slate-600 mb-4">No feeds yet.</p>
                <button
                  type="button"
                  onClick={() => setShowAddModal(true)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Add feed
                </button>
              </div>
            ) : selectedAccount ? (
              <div className="rounded-xl border border-slate-200 bg-white p-6">
                <h2 className="text-xl font-semibold text-slate-900">
                  {label(selectedAccount)}
                </h2>
                <p className="text-sm text-slate-500 mt-1 font-mono">
                  {selectedAccount.id}
                </p>
              </div>
            ) : (
              <p className="text-slate-500">Select a feed from the sidebar.</p>
            )}
          </div>
        </main>
      </div>

      <AddWeChatModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={() => void loadAccounts()}
      />
    </WeChatAuthGuard>
  );
}
