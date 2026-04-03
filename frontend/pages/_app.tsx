import type { AppProps } from "next/app";
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
    <QueryClientProvider client={queryClient}>
      {isHydrated ? <Component {...pageProps} /> : null}
    </QueryClientProvider>
  );
}
