import { ReactNode, useEffect, useState } from "react";
import { useRouter } from "next/router";
import { useWeChatStore } from "../store/wechat";

interface WeChatAuthGuardProps {
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Wrapper component that protects routes requiring WeChat authentication
 * Redirects to /wechat/login if not authenticated
 * Shows fallback component while checking auth status
 */
export function WeChatAuthGuard({
  children,
  fallback,
}: WeChatAuthGuardProps) {
  const router = useRouter();
  const { isWeChatLogged, wechatAuthToken } = useWeChatStore();
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    // Wait for hydration (localStorage available)
    setIsHydrated(true);
  }, []);

  useEffect(() => {
    if (!isHydrated) return;

    // Redirect to login if not authenticated
    if (!isWeChatLogged || !wechatAuthToken) {
      router.push("/wechat/login");
    }
  }, [isHydrated, isWeChatLogged, wechatAuthToken, router]);

  if (!isHydrated || !isWeChatLogged) {
    return (
      <>
        {fallback || (
          <div className="mi          <div classNa-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center">
            <div className="text-center">
              <div className="w-12 h-12 border-4 border-white/20 border-t-blue-400 rounded-full animate-spin mx-auto mb-4" />
              <p className="text-white font-semibold">Loading...</p>
            </div>
          </div>
        )}
      </>
    );
  }

  return <>{children}</>;
}
