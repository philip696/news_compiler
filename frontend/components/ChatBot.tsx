'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import { useChatContext } from '../context/ChatContext';

type ChatSize = 'closed' | 'minimized' | 'medium' | 'maximized';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const SIZE_CLASSES: Record<Exclude<ChatSize, 'closed' | 'minimized'>, string> = {
  medium:    'w-80 h-[480px]',
  maximized: 'w-[560px] h-[700px]',
};

/** Build the context blurb injected as the last system message before the user's messages */
function buildContextBlurb(ctx: ReturnType<typeof useChatContext>['pageContext']): string | null {
  if (!ctx.type) return null;

  if (ctx.type === 'article' && ctx.title) {
    const lines = [
      `The user is currently reading an article on the Synergy platform.`,
      `Title: "${ctx.title}"`,
      ctx.source       ? `Source: ${ctx.source}` : null,
      ctx.topic        ? `Topic: ${ctx.topic}` : null,
      ctx.publishedAt  ? `Published: ${ctx.publishedAt}` : null,
      ctx.authors      ? `Authors: ${ctx.authors}` : null,
      ctx.url          ? `URL: ${ctx.url}` : null,
      ctx.content
        ? `\nArticle content (first 2000 chars):\n${ctx.content.slice(0, 2000)}`
        : null,
      `\nAnswer questions about this article directly and concisely.`,
    ];
    return lines.filter(Boolean).join('\n');
  }

  if (ctx.type === 'feed')      return 'The user is browsing the main news feed on Synergy.';
  if (ctx.type === 'category')  return `The user is browsing the "${ctx.label}" category on Synergy.`;
  if (ctx.type === 'wechat')    return 'The user is browsing WeChat official account articles on Synergy.';
  if (ctx.type === 'bookmarks') return 'The user is viewing their saved bookmarks on Synergy.';
  if (ctx.type === 'profile')   return 'The user is on their profile page on Synergy.';
  return null;
}

export default function ChatBot() {
  const { pageContext, quickPrompt, setQuickPrompt } = useChatContext();

  // Always-current ref — avoids stale closures inside send()
  const pageContextRef = useRef(pageContext);
  pageContextRef.current = pageContext;

  const [size, setSize]       = useState<ChatSize>('closed');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput]     = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');
  const bottomRef   = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // When the page context changes, clear old messages so the conversation starts fresh
  useEffect(() => {
    setMessages([]);
    setError('');
  }, [pageContext.type, pageContext.title]);

  // Handle quick-prompt fired from another component (e.g. article page button)
  useEffect(() => {
    if (!quickPrompt) return;
    setSize('medium');
    setInput(quickPrompt);
    setQuickPrompt(null);
  }, [quickPrompt, setQuickPrompt]);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  }, [input]);

  const send = useCallback(async (overrideText?: string) => {
    const text = (overrideText ?? input).trim();
    if (!text || loading) return;

    const userMsg: Message = { role: 'user', content: text };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput('');
    setLoading(true);
    setError('');

    // Always read the ref so we never capture a stale closure value
    const contextBlurb = buildContextBlurb(pageContextRef.current);
    const payload = {
      messages: next,
      context: contextBlurb ?? undefined,
    };

    try {
      const res = await api.post('/api/chatbot/chat', payload);
      setMessages([...next, { role: 'assistant', content: res.data.reply }]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to get a response.');
    } finally {
      setLoading(false);
    }
  }, [input, messages, loading]); // pageContext intentionally omitted — read via ref

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  // Context badge shown in the header
  const contextLabel = pageContext.type === 'article' && pageContext.title
    ? `📄 ${pageContext.title.slice(0, 28)}${pageContext.title.length > 28 ? '…' : ''}`
    : pageContext.type === 'category' && pageContext.label
    ? `🗂 ${pageContext.label}`
    : pageContext.type === 'feed'
    ? '🏠 Main Feed'
    : pageContext.type === 'wechat'
    ? '🟩 WeChat'
    : pageContext.type === 'bookmarks'
    ? '🔖 Bookmarks'
    : null;

  // Empty-state placeholder text
  const placeholder = pageContext.type === 'article' && pageContext.title
    ? `Ask about "${pageContext.title.slice(0, 30)}…"`
    : 'Ask about the news… (Enter to send)';

  // ── Closed → floating button ─────────────────────────────────────────── //
  if (size === 'closed') {
    return (
      <button
        onClick={() => setSize('medium')}
        title="Open AI Assistant"
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-slate-900 text-white shadow-2xl hover:bg-slate-700 transition-all hover:scale-105 active:scale-95"
      >
        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-3 3-3-3z" />
        </svg>
      </button>
    );
  }

  const isMinimized = size === 'minimized';

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 flex flex-col rounded-2xl border border-slate-200 bg-white shadow-2xl transition-all duration-200 overflow-hidden
        ${isMinimized ? 'w-72 h-auto' : SIZE_CLASSES[size as 'medium' | 'maximized']}`}
    >
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex flex-shrink-0 flex-col bg-slate-900 px-4 pt-2.5 pb-2 select-none">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-white/10">
              <svg className="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-3 3-3-3z" />
              </svg>
            </div>
            <span className="text-sm font-semibold text-white">Synergy AI</span>
            {loading && (
              <span className="flex gap-0.5 items-end pb-0.5">
                {[0, 1, 2].map(i => (
                  <span key={i} className="block h-1 w-1 rounded-full bg-white/60 animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </span>
            )}
          </div>

          {/* Window controls */}
          <div className="flex items-center gap-1">
            <button onClick={() => setSize(size === 'minimized' ? 'medium' : 'minimized')}
              title={isMinimized ? 'Restore' : 'Minimize'}
              className="flex h-6 w-6 items-center justify-center rounded text-slate-400 hover:bg-white/10 hover:text-white transition-colors">
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M20 12H4" />
              </svg>
            </button>
            <button onClick={() => setSize('medium')} title="Medium"
              className={`flex h-6 w-6 items-center justify-center rounded transition-colors
                ${size === 'medium' ? 'bg-white/20 text-white' : 'text-slate-400 hover:bg-white/10 hover:text-white'}`}>
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <rect x="5" y="5" width="14" height="14" rx="1" strokeWidth={2.5} />
              </svg>
            </button>
            <button onClick={() => setSize('maximized')} title="Maximize"
              className={`flex h-6 w-6 items-center justify-center rounded transition-colors
                ${size === 'maximized' ? 'bg-white/20 text-white' : 'text-slate-400 hover:bg-white/10 hover:text-white'}`}>
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5}
                  d="M4 8V4h4M20 8V4h-4M4 16v4h4M20 16v4h-4" />
              </svg>
            </button>
            <button onClick={() => setSize('closed')} title="Close"
              className="flex h-6 w-6 items-center justify-center rounded text-slate-400 hover:bg-red-500/80 hover:text-white transition-colors">
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Context badge */}
        {contextLabel && !isMinimized && (
          <div className="mt-1.5 truncate rounded-md bg-white/10 px-2 py-0.5 text-[10px] text-white/70 font-medium">
            {contextLabel}
          </div>
        )}
      </div>

      {/* ── Body ───────────────────────────────────────────────────────── */}
      {!isMinimized && (
        <>
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 bg-slate-50">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center text-slate-400 py-8 gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-900/10">
                  <svg className="h-6 w-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-3 3-3-3z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-600">Synergy AI</p>
                  {pageContext.type === 'article' && pageContext.title ? (
                    <>
                      <p className="text-xs mt-1 text-slate-500">I can see the article you're reading.</p>
                      <div className="mt-3 flex flex-col gap-1.5">
                        {[
                          'Summarize this article',
                          'What are the key takeaways?',
                          'What\'s the broader context?',
                        ].map(q => (
                          <button key={q} onClick={() => send(q)}
                            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:border-slate-400 hover:bg-slate-50 transition-colors text-left">
                            {q}
                          </button>
                        ))}
                      </div>
                    </>
                  ) : (
                    <p className="text-xs mt-1">Ask me anything about the news.</p>
                  )}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap
                  ${msg.role === 'user'
                    ? 'bg-slate-900 text-white rounded-br-sm'
                    : 'bg-white border border-slate-200 text-slate-800 rounded-bl-sm shadow-sm'}`}>
                  {msg.content}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-sm bg-white border border-slate-200 px-4 py-3 shadow-sm">
                  {[0, 1, 2].map(i => (
                    <span key={i} className="block h-2 w-2 rounded-full bg-slate-400 animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }} />
                  ))}
                </div>
              </div>
            )}

            {error && (
              <div className="rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-600 flex justify-between gap-2">
                <span>{error}</span>
                <button onClick={() => setError('')} className="font-bold text-red-400 hover:text-red-600 flex-shrink-0">✕</button>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="flex-shrink-0 border-t border-slate-200 bg-white px-3 py-2.5 flex items-end gap-2">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder={placeholder}
              rows={1}
              className="flex-1 resize-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400 transition-all"
            />
            <button onClick={() => send()} disabled={!input.trim() || loading}
              className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-slate-900 text-white hover:bg-slate-700 disabled:bg-slate-200 disabled:text-slate-400 transition-colors">
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </>
      )}
    </div>
  );
}
