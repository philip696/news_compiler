import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface WeChatUser {
  openid: string;
  nickname?: string;
  avatar?: string;
  privilege?: string[];
}

type WeChatState = {
  wechatAuthToken: string | null;
  wechatUser: WeChatUser | null;
  isWeChatLogged: boolean;

  setWeChatToken: (token: string | null) => void;
  setWeChatUser: (user: WeChatUser | null) => void;
  clearWeChatToken: () => void;
  setWeChatAuth: (token: string, user: WeChatUser) => void;
  loadWeChatFromStorage: () => void;
};

export const useWeChatStore = create<WeChatState>()(
  persist(
    (set, get) => ({
      wechatAuthToken: null,
      wechatUser: null,
      isWeChatLogged: false,

      setWeChatToken: (token) => {
        set({ wechatAuthToken: token });
      },

      setWeChatUser: (user) => {
        set({
          wechatUser: user,
          isWeChatLogged: !!user && !!get().wechatAuthToken,
        });
      },

      clearWeChatToken: () => {
        set({
          wechatAuthToken: null,
          wechatUser: null,
          isWeChatLogged: false,
        });
      },

      setWeChatAuth: (token, user) => {
        set({
          wechatAuthToken: token,
          wechatUser: user,
          isWeChatLogged: true,
        });
      },

      loadWeChatFromStorage: () => {
        const state = get();
        set({
          isWeChatLogged: !!state.wechatAuthToken && !!state.wechatUser,
        });
      },
    }),
    { name: "wechat-auth-storage" }
  )
);
