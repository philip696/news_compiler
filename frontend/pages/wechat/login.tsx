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

  // Redirect if already logged in
  useEffect(() => {
    if (isWeChatLogged) {
      router.push("/wechat/accounts");
    }
  }, [isWeChatLogged, router]);

  const handleWeChatLogin = async () => {
    setLoading(true);
    setError("");

    try {
      // Get the login URL from backend
      const response = await api.get("/api/wechat/auth/start");
      const { login_url } = response.data;

      if (!login_url) {
        throw new Error("Failed to get WeChat login URL");
      }

      // Redirect to We      // Redirect to We      // Redirect to We      // Redirect to We      // Redirect s      // Redirect to We      // Redirect tl ||
          err.message ||
          "Fai          "Fai          "Fai            "Fai          "Fai          "Fai          (          "Fai          "Fai          "Fdie          "Fai          "Fai         to-          "Fai          "Faiju          "Fai          "Fai          "Fai -full max-w-md">
        <div className="bg-white/10         <div className="bg-white/10     er-        <div className="bg-wh       <h1 className="text-3xl font-bold text-white mb-2">WeChat Login</h1>
          <p className="text-slate-300 mb-8">Sign in with your WeChat account</p>

          {error && (
            <div className="mb-6 p-4 bg-red-500/20 border border-red-300/50 rounded-lg text-red-200 text-sm">
              {error}
            </div>
          )}

          <button
                            eCh                            eCh                          Na      ful                            eCh                            eCh                          Na      ful                            eCh                          te                    ld ro                            eCh                            eCh                          Na      ful                            eCh                            eCh                          Na      ful                            eCh                          te           imate-spin" />
                Redirecting...
              </>
            ) : (
              <>
                <svg
                  className="w-5 h-5"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                                   48 2                                   48 2                                   48 2                              8                   -.67                 15           7 1                5                                    48 2                                   48 2                                   48 2                              8                   -.67                 15           7 1                5                                    48 2                                   48 2                                   48 2                              8                   -.67                 15           7 1                5                                    48 2                                   48 2                                   48 2  ex                                                                       <div className="space-y-3 text-center text-sm text-slate-300">
                                            账                                                     in"
                className="text-blue-400 hover:text-blue-300 font-semibold ml-1"
              >
                使用用户名登录
              </Link>
            </p>
          </div>
        </div>

        {/* Footer info */}
        <div className="mt-8 text-center text-slate-400 text-xs">
          <p>Synergy - Personalized News Aggregation</p>
        </div>
      </div>
    </div>
  );
}
