import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { useWeChatStore } from "../../store/wechat";
import { handleWeChatCallback } from "../../services/wechatApi";

export default function WeChatCallback() {
  const router = useRouter();
  const { setWeChatAuth } = useWeChatStore();
  const [error, setError] = useState("");
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    if (!router.isReady) return;

    const run = async () => {
      try {
        const code = router.query.code;
        const state = router.query.state;
        if (!code || !state) {
          throw new Error("No authorization code received from WeChat");
        }

        const data = await handleWeChatCallback(String(code), String(state));
        if (!data.access_token || !data.user?.openid) {
          throw new Error("Invalid response from server");
        }

        setWeChatAuth(data.access_token, {
          openid: data.user.openid,
          nickname: data.user.nickname,
          avatar: data.user.avatar,
        });

        await router.replace("/wechat/accounts");
      } catch (err: unknown) {
        const ax = err as { response?: { data?: { detail?: string } }; message?: string };
        const msg =
          ax.response?.data?.detail ||
          (err instanceof Error ? err.message : null) ||
          "Authentication failed. Please try again.";
        setError(String(msg));
      } finally {
        setIsProcessing(false);
      }
    };

    void run();
  }, [router, router.isReady, router.query, setWeChatAuth]);

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <div className="w-full max-w-md text-center">
        {isProcessing ? (
          <>
            <div className="inline-block w-12 h-12 border-4 border-white/20 border-t-emerald-400 rounded-full animate-spin mb-4" />
            <p className="text-white font-semibold">Processing login...</p>
            <p className="text-slate-400 text-sm mt-2">
              Please wait while we complete your authentication
            </p>
          </>
        ) : error ? (
          <>
            <div className="rounded-lg bg-red-500/10 border border-red-500/30 p-4 mb-6">
              <p className="text-red-200">{error}</p>
            </div>
            <button
              type="button"
              onClick={() => router.push("/wechat/login")}
              className="w-full py-3 px-4 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg"
            >
              Back to Login
            </button>
          </>
        ) : null}
      </div>
    </div>
  );
}
