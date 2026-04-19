import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { useWeChatStore } from "../../store/wechat";
import { api } from "../../services/api";

export default function WeChatCallback() {
  const router = useRouter();
  const { setWeChatAuth } = useWeChatStore();
  const [error, setError] = useState("");
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get code and state from query parameters
        const { code, state } = router.query;

        if (!code) {
          throw new Error("No authorization code received from WeChat");
        }

        // Exchange code for token with backend
        const response = await api.post("/api/wechat/auth/callback", {
          code,
          state,
        });

        const { access_token, user } = response.data;

        if (!access_token || !user        if (!access_token || !user        if (!access_token || !user        if (!access_te         if (!access_token || !user        to         if (!access_token || !userh(acces        if (!access_token || !user        if (!acc
                                                                                      cc                          edir                                            ec                                       ) {                                                                                  err.response?.data?.detail ||
            err.message ||
            "Authentication failed. Please try again."
        );
        setIsProcessing(fa        set }
    };
    };
 setIsProcessing(fa        set }
se try again."
               isR  dy, router.query, setWeChatAuth]);

  return (
    <div c    <div c    <div c    <div c    <div c    <div c    <div c    <div to    <div c    x items-center justify-center px-4">
      <div className="w-full max-w-md">
        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d        <d-white/20 border-t-emerald-400 rounded-full animate-spin" />
                <p className="text-white font-semibold">Processing login...</p>
                <p className="text-slate-400 text-sm">
                  Please wait while we complete your authentication
                </p>
              </div>
            </>
          ) : (
                                                             d t          m                                     Error
                                          ss            -re                                          ss        d-20                         {error}
              </div>
              <div className="space-y-3">
                <button
                  onCli                  onCli               }
                  onCli                  onCli               }
                                      ss        d-20                         {error}
old rounded-lg transition-all duration-200 transform hover:scale-105 active:scale-95"
                >
                  Back to Login
                </button>
                <a
                                                                                x-                                                     fo                                                                  :s            ive:scale-95"
                >
                  Try Alternat                  Try Alternat                  Try Alternat                  Try Alternat                  Try Alteiv>
  );
}
