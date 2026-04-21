import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import { useWeChatStore } from "../../store/wechat";
import { api } from "../../services/api";

export default function WeChatLogin() {
  const router = useRouter();
  const { isWeChatLogged } = useWeChatStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isWeChatLogged) {
      void router.push("/wechat/accounts");
    }
  }, [isWeChatLogged, router]);

  const handleWeChatLogin = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await api.get<{ login_url?: string }>(
        "/api/wechat/auth/start"
      );
      const loginUrl = response.data?.login_url;

      if (!loginUrl) {
        throw new Error("Failed to get WeChat login URL");
      }

      window.location.href = loginUrl;
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: string } }; message?: string };
      const msg =
        ax.response?.data?.detail ||
        (err instanceof Error ? err.message : null) ||
        "Failed to start WeChat login";
      setError(String(msg));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-900 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 p-8 shadow-xl">
          <h1 className="text-3xl font-bold text-white mb-2">WeChat Login</h1>
          <p className="text-slate-300 mb-8">Sign in with your WeChat account</p>

          {error ? (
            <div className="mb-6 p-4 bg-red-500/20 border border-red-300/50 rounded-lg text-red-200 text-sm">
              {error}
            </div>
          ) : null}

          <button
            type="button"
            onClick={() => void handleWeChatLogin()}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold rounded-lg transition-colors"
          >
            {loading ? (
              <>
                <span className="inline-block w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Redirecting...
              </>
            ) : (
              <>
                <svg
                  className="w-5 h-5"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden
                >
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 8 15.5 8 14 8.67 14 9.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 8 8.5 8 7 8.67 7 9.5 7.67 7 8.5 8 8.5 8.83 8.5 9.5zM12 17.5c-2.33 0-4.31-1.46-5.11-3.5h10.22c-.8 2.04-2.78 3.5-5.11 3.5z" />
                </svg>
                Continue with WeChat
              </>
            )}
          </button>

          <div className="space-y-3 text-center text-sm text-slate-300 mt-6">
            <p>
              Prefer the main app?
              <Link
                href="/login"
                className="text-blue-400 hover:text-blue-300 font-semibold ml-1"
              >
                使用用户名登录
              </Link>
            </p>
          </div>
        </div>

        <div className="mt-8 text-center text-slate-400 text-xs">
          <p>Synergy - Personalized News Aggregation</p>
        </div>
      </div>
    </div>
  );
}
