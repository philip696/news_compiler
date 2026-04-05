import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuthStore } from '../store/auth';
import { api } from '../services/api';

export default function Login() {
  const [formData, setFormData] = useState({ username: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();
  const setAuth = useAuthStore((state) => state.setAuth);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await api.post('/api/auth/login', {
        username: formData.username,
        password: formData.password,
      });

      const data = response.data;
      setAuth(data.access_token, 1, formData.username);
      
      router.push('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 shadow-2xl p-8">
          <h1 className="text-3xl font-bold text-white mb-2">Synergy</h1>
          <p className="text-slate-300 mb-8">Personalized News Aggregation</p>

          {error && (
            <div className="mb-6 p-4 bg-red-500/20 border border-red-300/50 rounded-lg text-red-200">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Username</label>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                required
                className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-400"
                placeholder="username"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Password</label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-400"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2 mt-6 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white font-semibold rounded-lg transition-all disabled:opacity-50"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <p className="text-slate-300 text-center mt-6">
            Don't have an account?{' '}
            <Link href="/register" className="text-blue-400 hover:text-blue-300">
              Sign up
            </Link>
          </p>

          {/* Demo Credentials Box */}
          <div className="mt-8 pt-8 border-t border-white/20">
            <p className="text-slate-400 text-xs font-semibold uppercase tracking-widest mb-3">Demo Account</p>
            <div className="bg-blue-500/10 border border-blue-400/30 rounded-lg p-4 space-y-2">
              <div>
                <p className="text-[10px] text-blue-300 uppercase tracking-wide font-semibold">Username</p>
                <p className="text-white font-mono text-sm">demo123@test.com</p>
              </div>
              <div>
                <p className="text-[10px] text-blue-300 uppercase tracking-wide font-semibold">Password</p>
                <p className="text-white font-mono text-sm">demo123</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

