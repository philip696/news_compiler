import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuthStore } from '../store/auth';

export const useProtectedRoute = () => {
  const router = useRouter();
  const token = useAuthStore((state) => state.token);

  useEffect(() => {
    // If no token, redirect to login
    if (!token) {
      router.push('/login');
    }
  }, [token, router]);

  return !!token;
};
