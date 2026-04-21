import { useState } from "react";
import { useRouter } from "next/router";
import { useWeChatStore } from "../store/wechat";
import { useWeChatAuth } from "../hooks/useWeChatAuth";
import { api } from "../services/api";

interface WeChatLoginButtonProps {
  variant?: "default" | "outline" | "text";
  size?: "sm" | "md" | "lg";
  className?: string;
  onLoginStart?: () => void;
  onLoginError?: (error: string) => void;
}

export function WeChatLoginButton({
  variant = "default",
  size = "md",
  className = "",
  onLoginStart,
  onLoginError,
}: WeChatLoginButtonProps) {
  const router = useRouter();
  const { isWeChatLogged, wechatUser } = useWeChatStore();
  const { logout } = useWeChatAuth();
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (isWeChatLogged) {
      router.push("/wechat/accounts");
      return;
    }
    onLoginStart?.();
    setLoading(true);
    try {
      const { data } = await api.get<{ login_url?: string }>(
        "/api/wechat/auth/start"
      );
      const url = data?.login_url;
      if (url) {
        window.location.href = url;
      } else {
        router.push("/wechat/login");
      }
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: string } }; message?: string };
      const errorMsg =
        ax.response?.data?.detail || ax.message || "Login failed";
      onLoginError?.(String(errorMsg));
      try {
        await router.push("/wechat/login");
      } catch {
        /* noop */
      }
    } finally {
      setLoading(false);
    }
  };

  const sizeClasses = {
    sm: "px-3 py-1 text-sm",
    md: "px-4 py-2 text-base",
    lg: "px-6 py-3 text-lg",
  };

  const variantClasses = {
    default: "bg-green-600 text-white hover:bg-green-700",
    outline: "border-2 border-green-600 text-green-600 hover:bg-green-50",
    text: "text-green-600 hover:text-green-700",
  };

  if (isWeChatLogged && wechatUser) {
    return (
      <div className="flex items-center gap-2">
        {wechatUser.avatar ? (
          <img
            src={wechatUser.avatar}
            alt={wechatUser.nickname || ""}
            className="w-8 h-8 rounded-full"
          />
        ) : null}
        <div className="flex flex-col">
          <span className="text-sm text-slate-700">
            {wechatUser.nickname || wechatUser.openid}
          </span>
          <button
            type="button"
            onClick={() => void logout()}
            className="text-xs text-slate-500 hover:text-slate-800 text-left"
          >
            Logout
          </button>
        </div>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => void handleClick()}
      disabled={loading}
      className={`
        inline-flex items-center justify-center gap-2 rounded-lg font-medium
        ${sizeClasses[size]}
        ${variantClasses[variant]}
        disabled:opacity-50
        ${className}
      `}
    >
      {loading ? (
        <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
      ) : (
        <>
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden>
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 8 15.5 8 14 8.67 14 9.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 8 8.5 8 7 8.67 7 9.5 7.67 7 8.5 8 8.5 8.83 8.5 9.5zM12 17.5c-2.33 0-4.31-1.46-5.11-3.5h10.22c-.8 2.04-2.78 3.5-5.11 3.5z" />
          </svg>
          <span>登录 WeChat</span>
        </>
      )}
    </button>
  );
}
