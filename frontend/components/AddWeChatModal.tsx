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
      setError("Please enter account ID");
      return;
    }
    if (!validateWeChatAccountId(trimmed)) {
      setError("Invalid format, e.g. MP_WXS_123456");
      return;
    }
    setValidated(true);
    setValidated(true);
format, e.g. MP_WXS_123456");
ccess }: AddWeChatModalProps) {
   handleValidat   handleValidat   handleValidatLo   handleValidat   handleValidat   handleValidatLo   handleValidat   handleValidarim   handleValidat   handleValidd!   handleValiAccoun   handleValidat   alid   handleValidat   hnSuccess?   handleValidat   handleValidat   handleValidatLo   handleValidat   handleValidat?.da   handleValidat   handleValidat   handleValidatcludes("already")) {
        setError("Already subs        setError("Already subs        seudes("not found")) {
        setError("Account not found");
      } else {
        setError(errorMsg || "Failed to add");
      }
      }
selly {
                             }
                             ull;


                            ullixed i                  te                            ullixed i                  Na    w-                            ullixed i      ">
        <div className="flex items-center justify-between px-6 py-4 borde        <div classNam>
                      e="                      e="   -900">Add WeChat Account</h2>
                                                                                                                                                                                                                                                                                                                                                                                                          v>                                                                                         /l                                     va             d} onChange={(e) => handleInputChange(e.target.value)} di      ={loading} placeholder="e.g. MP_WXS_123456" className="w-full px-4 py-2 borde                                                                                                                                                                    </div>}

          <div className="p-3 bg-blue-50 rounded-lg">
            <p className="text-xs f            <p className="text-xs f            <p className="text-xs f           -x            <p className="text-xs f            <p className="text-xs f            <p className="text-xs f           -x            <p className="text-xs f            <p className="text-xs f            <p className="text-xs f           -x            <p className="text-xs f            <p className="text-xs f            <p className="text-xs f           -x            <p className="text-xs f            <p className="text-xs f            <p className="text-xs f           -x            <p className="text-xs f            <p className="text-xs f            <p className="text-xs f           -x            <p className="text-xs f            <p className="text-xs f            <p className="text-xs f           -x            <p className="text-xs f            <p className="text-xs f            <p className="text-xs f           -x            <p classNam    </div>
    </div>
  );
}
