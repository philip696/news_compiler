import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import api from "../services/api";

interface AIChatProps {
  articleId: string;
  articleTitle: string;
  articleContent: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  type?: "summary" | "question" | "tags" | "sentiment";
}

export default function AIChat({
  articleId,
  articleTitle,
  articleContent,
}: AIChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [sessionId] = useState(() => Math.random().toString(36).slice(2, 9));

  // Summarize mutation
  const summarizeMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post("/api/ai/summarize", {
        article_id: articleId,
        max_length: 250,
      });
      return response.data;
    },
    onSuccess: (data) => {
      addMessage(
        `I've created a summary:\n\n${data.summary}`,
        "assistant",
        "summary"
      );
    },
    onError: (error: any) => {
      addMessage(
        `Error: ${error.response?.data?.detail || "Failed to summarize"}`,
        "assistant"
      );
    },
  });

  // Ask question mutation
  const askMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post("/api/ai/ask", {
        article_id: articleId,
        question: input,
      });
      return response.data;
    },
    onSuccess: (data) => {
      addMessage(data.answer, "assistant", "question");
    },
    onError: (error: any) => {
      addMessage(
        `Error: ${error.response?.data?.detail || "Failed to answer question"}`,
        "assistant"
      );
    },
  });

  // Generate tags mutation
  const tagsMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post("/api/ai/tags", {
        article_id: articleId,
        count: 5,
      });
      return response.data;
    },
    onSuccess: (data) => {
      addMessage(
        `Suggested tags:\n\n${data.tags.map((tag: string) => `• ${tag}`).join("\n")}`,
        "assistant",
        "tags"
      );
    },
    onError: (error: any) => {
      addMessage(
        `Error: ${error.response?.data?.detail || "Failed to generate tags"}`,
        "assistant"
      );
    },
  });

  // Sentiment mutation
  const sentimentMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post("/api/ai/sentiment", {
        text: articleContent.slice(0, 500),
      });
      return response.data;
    },
    onSuccess: (data) => {
      addMessage(
        `Sentiment Analysis:\n\n📊 Sentiment: ${data.sentiment.toUpperCase()}\n📈 Confidence: ${(data.confidence * 100).toFixed(1)}%\n\nReason: ${data.reason}`,
        "assistant",
        "sentiment"
      );
    },
    onError: (error: any) => {
      addMessage(
        `Error: ${error.response?.data?.detail || "Failed to analyze sentiment"}`,
        "assistant"
      );
    },
  });

  const addMessage = (
    content: string,
    role: "user" | "assistant",
    type?: string
  ) => {
    const message: Message = {
      id: `${sessionId}-${Date.now()}`,
      content,
      role,
      type: type as any,
    };
    setMessages((prev) => [...prev, message]);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const trimmedInput = input.toLowerCase().trim();
    addMessage(input, "user");
    setInput("");

    // Detect intent from user input
    if (
      trimmedInput.includes("summary") ||
      trimmedInput.includes("summarize") ||
      trimmedInput.includes("tldr") ||
      trimmedInput.includes("tl;dr")
    ) {
      summarizeMutation.mutate();
    } else if (
      trimmedInput.includes("tag") ||
      trimmedInput.includes("tags") ||
      trimmedInput.includes("keyword")
    ) {
      tagsMutation.mutate();
    } else if (
      trimmedInput.includes("sentiment") ||
      trimmedInput.includes("tone") ||
      trimmedInput.includes("feeling")
    ) {
      sentimentMutation.mutate();
    } else {
      // Default: ask as a question
      askMutation.mutate();
    }
  };

  const isLoading =
    summarizeMutation.isPending ||
    askMutation.isPending ||
    tagsMutation.isPending ||
    sentimentMutation.isPending;

  const quickActions = [
    { label: "📝 Summarize", onClick: () => summarizeMutation.mutate() },
    { label: "🏷️ Tags", onClick: () => tagsMutation.mutate() },
    { label: "📊 Sentiment", onClick: () => sentimentMutation.mutate() },
  ];

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {/* Chat Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="w-14 h-14 bg-gradient-to-br from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 rounded-full shadow-lg flex items-center justify-center text-white text-2xl transition-transform hover:scale-110"
          title="AI Assistant"
        >
          ✨
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 w-96 max-h-[600px] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-purple-500 to-indigo-600 text-white p-4 flex justify-between items-center">
            <h3 className="font-semibold">✨ AI Assistant</h3>
            <button
              onClick={() => setIsOpen(false)}
              className="text-xl leading-none hover:opacity-70"
            >
              ✕
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 max-h-[400px]">
            {messages.length === 0 ? (
              <div className="text-center text-slate-500 py-8">
                <p className="text-sm mb-4">Hi! I can help you with:</p>
                <div className="space-y-2">
                  {quickActions.map((action) => (
                    <button
                      key={action.label}
                      onClick={() => {
                        addMessage(action.label, "user");
                        action.onClick();
                      }}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-slate-100 rounded-lg transition-colors"
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-xs px-4 py-2 rounded-lg whitespace-pre-wrap text-sm ${
                      msg.role === "user"
                        ? "bg-indigo-100 text-slate-900"
                        : "bg-slate-100 text-slate-800"
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))
            )}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-slate-100 px-4 py-2 rounded-lg">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-100"></div>
                    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-200"></div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="border-t border-slate-200 p-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question or say 'summarize'..."
                className="flex-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium"
              >
                Send
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
