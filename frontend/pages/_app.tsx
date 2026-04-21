import type { AppProps } from "next/app";
import Head from "next/head";
import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setAuthToken } from "../services/api";
import { useAuthStore } from "../store/auth";
import ChatBot from "../components/ChatBot";
import { ChatContextProvider } from "../context/ChatContext";
import "../styles/globals.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error: any) => {
        const status = error?.response?.status;
        if (status === 401 || status === 403) {
          return false;
        }
        return failureCount < 2;
      },
    },
  },
});

export default function App({ Component, pageProps }: AppProps) {
  const token = useAuthStore((state) => state.token);
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    // Set hydration flag after first render (when localStorage is available)
    setIsHydrated(true);
  }, []);

  useEffect(() => {
    // Set the auth token immediately when it changes
    setAuthToken(token ?? null);
  }, [token, isHydrated]);

  return (
    <>
      <Head>
        <title>Synergy - Personalized News Aggregation</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📰</text></svg>" />
      </Head>
      <QueryClientProvider client={queryClient}>
        <ChatContextProvider>
          {isHydrated ? <Component {...pageProps} /> : null}
          {isHydrated && token && <ChatBot />}
        </ChatContextProvider>
      </QueryClientProvider>
    </>
  );
}
