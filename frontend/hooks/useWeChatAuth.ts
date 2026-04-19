import { useCallback } from "react";
import { useRouter } from "next/router";
import { useWeChatStore } from "../store/wechat";
import { api } from "../services/api";

export function useWeChatAuth() {
  const router = useRouter();
  const { isWeChatLogged, wechatAuthToken, clearWeChatToken, setWeChatAuth } = useWeChatStore();

  /**
   * Check if user is logged in via WeChat
   */
  const isAuthenticated = useCallback(() => {
    return isWeChatLogged && !!wechatAuthToken;
  }, [isWeChatLogged, wechatAuthToken]);

  /**
   * Logout from WeChat
   */
  const logout = useCallback(async () => {
    try {
      // Optional: Call backend logout endpoint if needed
      clearWeChatToken();
      router.push("/wechat/login");
    } catch (error) {
      console.error("Logout failed:", error);
      clearWeChatToken();
    }
  }, [clearWeChatToken, router]);

  /**
   * Refresh auth token (if using refresh tokens)
   */
  const r  const r  const r  const r  const r  const r  const r  const r  const r  const r  cont(  const r  const r  const r  cons  co  const r  const r  const r  constnse.dat  const r  const r  const r  const r  const r       const r  const r  const r  const
                                   fail                          eCha                                   fail                          eCha                   
    isAuthentic    isAuthentic    isAuthentic    isAuthere  eshToken,
    token: wechatAuthToken,
  };
}
