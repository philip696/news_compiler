import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface WeChatUser {
  openid: string;
  nickname?: string;
  avatar?: string;
  privilege?: string[];
}

type WeChatState = {
  // Auth state
  wechatAuthToken: string | null;
  wechatUser: WeChatUser | null;
  isWeChatLogged: boolean;

  // Actions
  setWeChatToken: (token: string | null) => void;
  setWeChatUser: (user: WeChatUser | null) => void;
  clearWeChatToken: () => void;
  setWeChatAuth: (token: string, user: WeChatUser) => void;
  
  // Refresh
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
        set({ wechatUser: user, isWeChatLogged: !!user });
                                                                                    To                                :                                               }                            at     : () => {
                                     en: nu                     ser: n                sWeCh              e,                                dWeChatFromStorage: () => {
        // Called on app init to load state from localStorage
        const state = get();
        set({
          isWeChatLogged: !!state.wechatAuthToken && !!state.wechatUser,
                                                              ",
            
