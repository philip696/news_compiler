import { useState } from "react";
import { addWeChatAccount, validateWeChatAccountId } from "../services/wechatApi";

interface AddWeChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function AddWeChatModal({ isOpen, onClose, onSuccess }: AddWeChatModalProps) {
  const [accountId, setAccountId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [validated, setValidated] = useState(false);

  const handleInputChange = (value: string) => {
    setAccountId(value);
    setError("");
    setValidated(false);
  };

  const handleValidate = () => {
    const trimmed = accountId.trim();
    if (!trimmed) {
      setError("Please enter account ID or article URL");
      return;
    }
    if (!validateWeChatAccountId(trimmed)) {
      setError("Invalid format — use an mp.weixin.qq.com article URL or account id");
      return;
    }
    setValidated(true);
  };

  const handleSubmit = async () => {
    const trimmed = accountId.trim();
    if (!trimmed) {
      setError("Please enter account ID or article URL");
      return;
    }
    if (!validated && !validateWeChatAccountId(trimmed)) {
      setError("Invalid format");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await addWeChatAccount(trimmed);
      onSuccess?.();
      onClose();
      setAccountId("");
      setValidated(false);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: string; message?: string } } };
      const detail =
        err?.response?.data?.message ||
        err?.response?.data?.error ||
        (e instanceof Error ? e.message : "Failed to add");
      const msg = String(detail);
      if (msg.includes("placeholder") || msg.includes("MP_WXS")) {
        setError("That id looks like a placeholder — paste a full mp.weixin.qq.com article link instead.");
      } else if (msg.toLowerCase().includes("already") || msg.includes("duplicate")) {
        setError("Already subscribed");
      } else if (msg.includes("not found")) {
        setError("Account not found");
      } else {
        setError(msg || "Failed to add");
      }
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">Add WeChat feed</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-500 hover:text-slate-800"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Article URL or account id
            </label>
            <input
              type="text"
              value={accountId}
              onChange={(e) => handleInputChange(e.target.value)}
              disabled={loading}
              placeholder="https://mp.weixin.qq.com/s/… or biz id"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          {error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : null}
          <div className="p-3 bg-blue-50 rounded-lg">
            <p className="text-xs text-slate-600">
              Paste a full <code className="bg-blue-100 px-1 rounded">mp.weixin.qq.com</code> article
              link for the most reliable add flow.
            </p>
          </div>
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-slate-700 border border-slate-300 rounded-lg hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleValidate}
              disabled={loading}
              className="px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50"
            >
              Validate
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Adding…" : "Add"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
