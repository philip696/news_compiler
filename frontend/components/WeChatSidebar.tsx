import { useState } from "react";
import { WeChatAccount } from "../services/wechatApi";
import { removeWeChatAccount, updateWeChatAccount, muteAccount, unmuteAccount } from "../services/wechatApi";

interface WeChatSidebarProps {
  accounts: WeChatAccount[];
  loading?: boolean;
  onAccountSelect?: (account: WeChatAccount) => void;
  selectedAccountId?: string;
  onAddClick?: () => void;
  onAccountsChange?: () => void;
}

export function WeChatSidebar(props: WeChatSidebarProps) {
  const { accounts, loading, onAccountSelect, selectedAccountId, onAddClick, onAccountsChange } = props;
  const [deleting, setDeleting] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);
  const [togglingMute, setTogglingMute] = useState<string | null>(null);

  const handleUpdate = async (accountId: string) => {
    setUpdating(accountId);
    try {
      await updateWeChatAccount(accountId      await updateWeChatAccount(accountId      await updateWeChatAccount(accountId      awaitror);
    } finally {
      setUpdating(null);
    }
  };

  const handleToggleMute = async (accountId: string, isMuted: boolean) => {
    setTogglingMute(accountId);
    try {
      if (isMuted) {
                                 nt                            a                 acco                                 nt               catc                         .erro                      ", error);
    } finally {
      setTogglingMute(null);
    }
  };

  const handleDelete = async (ac  const handleDelete = async (ac  const handleDelete = async (ac  const handleDelete = async (ac  const
                                                                ge                                                              :",                                                                ge  rn (
                                                    er-                          screen">
      <div className="p-6 border-b border-slate-200">
        <h2 className="text-lg font-bold text-slate-900 mb-4">Accounts</h2>
        <button onClick={onAddClick} className="w-full px-4 py-2 b        <button onClick={onAddClick} className="w-full px-4 py-2 b                  <button onClick={onAd"fl   1 overf        <button pace-        <button onClick={onAddClick} className="w-full px-4 py-2 b        <button onClick={onAddClick} className="w-full px-4 py-2 b                  <button onClick={onAd"fl   1 overf        <button v>
        ) : (
          accounts.map((account) => (
                                                                                                                                          Ac                                                                                                                                          Ac                                                              vatar} alt="avatar" className="w-10 h-10 rounded-full" /> : <div className="w-10 h-10 rounde                                                    me="flex-1">
                  <h3 className="font-semibold truncate">{account                  <h3 className="font-semibold truncate">{account                  <h3 className="font-semibold truncate">{account                  <h3 className="font-semibold truncate">{account                  <h3 className="font-semibold truncate">{account                  <h3 className="font-semibold truncate">{account                  <h3 className="font-semibold truncate">{account                Cl            { e.stopPropagation(); handleToggleMute(account.id, account.is_muted); }} className="flex-1 text-xs bg-amber-50 px-2 py-1 rounded">Mute</button>
                <button onClick={(e) => { e.stopPropagation(); handleDelete(account.id); }} className="flex-1 text-xs bg-red-50 text-red-700 px-2 py-1 rounded">Delete</button>
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
