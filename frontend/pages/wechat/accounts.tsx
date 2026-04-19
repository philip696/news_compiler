import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import { useWeChatStore } from "../../store/wechat";
import { WeChatAuthGuard } from "../../components/WeChatAuthGuard";
import { WeChatSidebar } from "../../components/WeChatSidebar";
import { AddWeChatModal } from "../../components/AddWeChatModal";
import { getWeChatAccounts, WeChatAccount } from "../../services/wechatApi";

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

  // Load accounts on mount
  useEffect(() => {
    loadAccounts();
  }, []);

  // Selec  // Selec  // Selec  // Selec  // Selec  // Selec  // Selec  // Selec  // Selec  // Selete  // Selec  // Selec  // Selec  // Selec  /ts  // Selec  // Selec  // Selec  // Sst lo  // Selec  // Selec  // Selec  // Selec  // Selec     // Selec  // Selec  // Selec  // Selec  // Selec  // Selec  // s();
      setAccounts(data);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message;
      setError(errorMsg || "Failed to load accounts");
    } finally {
      setLoading(false);
    }
  };

  const handleAccountRefresh = () => {
    loadAccounts();
  };

  return (
    <WeChatAuthGuard>
      <div className="flex h-screen bg-slate-100">
        {/* Sideba        {/* Sideba        {/* Sideba     counts={accounts}
          loading={loading}
                                                                         d={selectedAccount?.id}
                                                                                 ndleAccountRefresh}
        />

        {/* Main Content *        {/* Main Content *        {/* Main Content *        {/* Main Content *        {/* Main Content *        {/* Main Content *        {/* Main Content *        {/* Main Content *        {/* Main Content *        {/* Main Content *        {/* Main Content *        {/* Main Content *        {/* Main Conteol        {/* Main Con             {/* Main Con��户        {/* Main Content *        {/* Main Content *       text-sl        {/* Main Content *        {/* Main Content * .nickname}! 👋
                </p>
              </d              </d              </d                ={() => router.push("/")}
              </d   sName="px-4 py-2 text-slate-700 hover:bg-slate-100 rounded-lg transition-colors font-medium"
              >
                ← 返回首页
              </              </              </              </              </              </         classNam              </              </              </              </              </              </  red-50 border border-red-200 rounded-lg text-red-700">
                {error}
              </div>
            )}

            {loading ? (
              // Loading skeleton
              <div className="space-y-4">
                {[...Array(3)].map((_, i) => (
                  <div
                    key={i}
                    className="p-6 bg-white rounded-lg border border-slate-200 animate-pulse"
                  >
                    <div className="flex gap-4 mb-4">
                      <div className="w-16 h-16 bg-slate-200 rounded-lg" />                      <div className="w-16 h-16 bg-slate-200 rounded-lg" />              -6 b                      <div className="w-16 h-16 bg-slate-200 rounded-lg" />                      <div className                                        <div clas/d                      <div className="w-16 h-16 bg-slate-200 rounded-lg" />                      <div className="w-16 h-16 bg-slate-200 rounded-lg" />              -6 b                      <div className="w-16 h-16 bg-slate-200 rounded-lg" />                                          </div                   cc             ===                     // E                      <div claclas                      <div className="wfy-                      <div className="w-16 <div className="w-20 h-20 b                      <diflex items-center justify-center mb-6">
                  <svg
                    className="w-10 h-10 text-slate-400"
                    fill="none"
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              te               emibold                                                      
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M12 4v16m8-8H4"
                    />
                  </svg>
                  添加第一个账户
                </button>
              </div>
            ) : selectedAccount ? (
              // Account details
              <div className="space-y-6">
                {/* Account info card */}
                <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
                  <div className="p-6 bg-gradient-to-r from-emerald-50 to-blue-50 border-b border-slate-200">
                    <div className="flex gap-6">
                      {selectedAccount.wechat_account_avatar ? (
                        <img
                          src={selectedAccount.wechat_account_avatar}
                                                                                                                           lg                                                                    (
                                           0                                   from                                       te                                             <sp                                      -bold">
                                    dAccount.wechat_account_name?.[0]?.toUpperCase()}
                                                                
                                                                                                                                       -slate-900">
                          {selectedAccount.wechat_account_name}
                        </h2>
                                                     mt-1">
                          {selectedAccount.wechat_account_id}
                        </                        </                        </                                          </                        </                        </                                          </                        </                        </                                             </                        </                        </                                          </                        </                        </                                    ed-700 r                        </                        </                        </      la                        </                        </           "
                        </                        </                        </                                          </                        20                        </                        </           <                        <       静音中
                        </div>
                                                                             
                  {/* Quick actions */}
                  <div className="p-6 bg-white">
                    <h3 className="text-lg font-bold text-slate-900 mb-4">
                      快速操作
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                      <button className="px-4 py-3 bg-blue-50 text-blue-700 hover:bg-blue-100 font-semibold rounded-lg transition-colors flex items-center justify-center gap-2">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path
                            strokeLinecap="round"
                                                                                                                                                                                                                                                                      >
                            g>
                        立即更新
                      </button>
                      <button className="px-4 py-3 bg-amber-50 text-amber-700 hover:bg-amber-100 font-semibold rounded-lg transition-colors flex items-center justify-center gap-2">
                        <svg                        l=                        <svg                        l=                      <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth="2"
                                                                                                                 7 0                              1.                                              
                                                                                                                                                                                                                                                                      "grid grid-cols-3 gap-4">
                  <div className="bg-white rounded-lg p-6 border border-slate-2                  <div className="bg-white rounded-lg p-6 border border-slate-2                  <div className="bg-white rounded-lg p-6 border border-slate-2                  <di                    <div className="bg-white rounded-lg p-6 border border-slate-2                  <div className="bg-white rounded--sm te                  <div className="bg-white round      <p className="text-3xl font-bold text-slate-900 mt-2">--</p>
                  </div>
                                                                                                                                                                                                      lg                                                                                                                                                                                                      lg                                                                                      dd account modal */}
      <AddWeChatModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={handleAccountRefresh}
      />
    </WeChatAuthGuard>
  );
}
