import { createContext, useContext, useState, useCallback, ReactNode } from 'react';

export interface PageContext {
  type: 'article' | 'feed' | 'category' | 'wechat' | 'profile' | 'bookmarks' | null;
  // article-specific
  title?: string;
  content?: string;
  source?: string;
  url?: string;
  topic?: string;
  publishedAt?: string;
  authors?: string;
  // generic label shown in the chatbot header
  label?: string;
}

interface ChatContextValue {
  pageContext: PageContext;
  setPageContext: (ctx: PageContext) => void;
  clearPageContext: () => void;
  /** Fires the chatbot open with a pre-filled prompt */
  quickPrompt: string | null;
  setQuickPrompt: (prompt: string | null) => void;
}

const ChatCtx = createContext<ChatContextValue>({
  pageContext: { type: null },
  setPageContext: () => {},
  clearPageContext: () => {},
  quickPrompt: null,
  setQuickPrompt: () => {},
});

export function ChatContextProvider({ children }: { children: ReactNode }) {
  const [pageContext, setPageContextState] = useState<PageContext>({ type: null });
  const [quickPrompt, setQuickPrompt] = useState<string | null>(null);

  const setPageContext = useCallback((ctx: PageContext) => {
    setPageContextState(ctx);
  }, []);

  const clearPageContext = useCallback(() => {
    setPageContextState({ type: null });
  }, []);

  return (
    <ChatCtx.Provider value={{ pageContext, setPageContext, clearPageContext, quickPrompt, setQuickPrompt }}>
      {children}
    </ChatCtx.Provider>
  );
}

export const useChatContext = () => useContext(ChatCtx);
