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
    <div className="min-h-screen bg-[#f3f4f6] flex items-center justify-center px-4 py-12 relative overflow-hidden">
      {/* Subtle dot-grid backdrop to match the feed pages */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            'radial-gradient(circle at 1px 1px, rgba(15,23,42,0.08) 1px, transparent 0)',
          backgroundSize: '24px 24px',
        }}
      />

      <div className="relative w-full max-w-md">
        {/* Brand header */}
        <div className="mb-6 flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-slate-900 text-white flex items-center justify-center font-bold shadow-sm">
            S
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 leading-tight">Synergy</h1>
            <p className="text-xs text-slate-500">Personalized News Aggregation</p>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8">
          <h2 className="text-xl font-semibold text-slate-900 mb-1">Welcome back</h2>
          <p className="text-sm text-slate-500 mb-6">Sign in to continue to your feed.</p>

          {error && (
            <div className="mb-5 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wide text-slate-600 mb-2">
                Username
              </label>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                required
                className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900 transition"
                placeholder="username"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wide text-slate-600 mb-2">
                Password
              </label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900 transition"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 mt-2 bg-slate-900 hover:bg-slate-800 text-white font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
            >
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>

          <p className="text-sm text-slate-600 text-center mt-6">
            Don&apos;t have an account?{' '}
            <Link href="/register" className="text-slate-900 hover:text-slate-700 font-semibold underline underline-offset-2">
              Sign up
            </Link>
          </p>

          {/* Demo Credentials Box */}
          <div className="mt-8 pt-6 border-t border-slate-200">
            <p className="text-[11px] text-slate-500 font-semibold uppercase tracking-widest mb-3">
              Demo Account
            </p>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-2">
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wide font-semibold">
                  Username
                </p>
                <p className="text-slate-900 font-mono text-sm">demo123@test.com</p>
              </div>
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wide font-semibold">
                  Password
                </p>
                <p className="text-slate-900 font-mono text-sm">demo123</p>
              </div>
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-slate-400 mt-6">
          © {new Date().getFullYear()} Synergy · Intelligence Feed
        </p>
      </div>
    </div>
  );
}
