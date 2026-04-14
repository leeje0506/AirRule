import { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('airrule_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('airrule_token');
    if (token) {
      authApi.me()
        .then((u) => {
          setUser(u);
          localStorage.setItem('airrule_user', JSON.stringify(u));
        })
        .catch(() => {
          setUser(null);
          localStorage.removeItem('airrule_token');
          localStorage.removeItem('airrule_user');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (username, password) => {
    const data = await authApi.login(username, password);
    localStorage.setItem('airrule_token', data.token);
    const u = { username: data.username, role: data.role, name: data.name };
    localStorage.setItem('airrule_user', JSON.stringify(u));
    setUser(u);
    return u;
  };

  const logout = () => {
    localStorage.removeItem('airrule_token');
    localStorage.removeItem('airrule_user');
    setUser(null);
  };

  const canEditPolicy = user?.role === 'subtitle' || user?.role === 'admin';
  const canEditTech = user?.role === 'dev' || user?.role === 'admin';

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, canEditPolicy, canEditTech }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
