import { useState, useEffect } from 'react';
import api from '../api/client';
import { User } from '../types';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Just checking if we can hit a protected route, or assuming the cookie is present
        // In a real app we might have a /api/auth/me route. 
        // For now, if we don't have a 401, we assume authenticated until proven otherwise.
        // We'll set a dummy user to bypass full auth check if we want, or do a real check.
        await api.get('/dashboard/stats');
        setUser({ id: 1, username: 'admin' });
      } catch (err) {
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    checkAuth();

    const handleUnauthorized = () => setUser(null);
    window.addEventListener('unauthorized', handleUnauthorized);
    return () => window.removeEventListener('unauthorized', handleUnauthorized);
  }, []);

  const login = async (password: string) => {
    // Usually uses form data for OAuth2PasswordRequestForm in FastAPI
    const formData = new FormData();
    formData.append('username', 'admin');
    formData.append('password', password);
    
    await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    setUser({ id: 1, username: 'admin' });
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (e) {
      // ignore
    }
    setUser(null);
  };

  return { user, loading, login, logout };
}
