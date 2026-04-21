import { useCallback } from "react";
import { useRouter } from "next/router";
import { useWeChatStore } from "../store/wechat";

export function useWeChatAuth() {
  const router = useRouter();
  const {
    isWeChatLogged,
    wechatAuthToken,
    wechatUser,
    clearWeChatToken,
    setWeChatAuth,
  } = useWeChatStore();

  const isAuthenticated = useCallback(() => {
    return isWeChatLogged && !!wechatAuthToken;
  }, [isWeChatLogged, wechatAuthToken]);

  const logout = useCallback(async () => {
    try {
      clearWeChatToken();
      await router.push("/wechat/login");
    } catch (error) {
      console.error("Logout failed:", error);
      clearWeChatToken();
    }
  }, [clearWeChatToken, router]);

  return {
    isAuthenticated,
    logout,
    token: wechatAuthToken,
    user: wechatUser,
    setWeChatAuth,
  };
}
