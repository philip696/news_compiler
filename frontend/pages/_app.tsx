import type { AppProps } from "next/app";
import Head from "next/head";
import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setAuthToken } from "../services/api";
import { useAuthStore } from "../store/auth";
import "../styles/globals.css";

const queryClient = new QueryClient();

export default function App({ Component, pageProps }: AppProps) {
  const token = useAuthStore((state) => state.token);
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    // Set hydration flag after first render (when localStorage is available)
    setIsHydrated(true);
  }, []);

  useEffect(() => {
    // Set the auth token immediately when it changes
    if (token) {
      setAuthToken(token);
    }
  }, [token, isHydrated]);

  return (
    <>
      <Head>
        <title>Synergy - Personalized News Aggregation</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📰</text></svg>" />
      </Head>
      <QueryClientProvider client={queryClient}>
        {isHydrated ? <Component {...pageProps} /> : null}
      </QueryClientProvider>
    </>
  );
}
