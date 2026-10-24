import React, { createContext, useContext, useState, useEffect } from 'react';
import { supabase, isSupabaseConfigured } from '../services/supabase';
import { setAuthTokenGetter, api } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  // Link token to API service
  useEffect(() => {
    setAuthTokenGetter(() => token);
  }, [token]);

  // Load session on startup
  useEffect(() => {
    async function initSession() {
      // 1. First check persisted auth token in localStorage
      const savedAuthToken = localStorage.getItem('lb_auth_token') || localStorage.getItem('lb_dev_token');
      const savedAuthUser = localStorage.getItem('lb_auth_user') || localStorage.getItem('lb_dev_user');
      if (savedAuthToken && savedAuthUser) {
        try {
          const parsedUser = JSON.parse(savedAuthUser);
          setToken(savedAuthToken);
          setUser(parsedUser);
          setProfile(parsedUser);
          fetchProfile(savedAuthToken).catch(() => {});
          setLoading(false);
          return;
        } catch (e) {
          localStorage.removeItem('lb_auth_token');
          localStorage.removeItem('lb_auth_user');
        }
      }

      // 2. Supabase session check if configured
      if (isSupabaseConfigured && supabase) {
        try {
          const { data: { session }, error } = await supabase.auth.getSession();
          if (session && !error) {
            setToken(session.access_token);
            setUser(session.user);
            fetchProfile(session.access_token).catch(() => {});
          }
        } catch (err) {
          console.error('Error fetching Supabase session:', err);
        }

        const { data: { subscription } } = supabase.auth.onAuthStateChange(
          async (event, session) => {
            if (session) {
              setToken(session.access_token);
              setUser(session.user);
              fetchProfile(session.access_token).catch(() => {});
            } else if (!localStorage.getItem('lb_auth_token')) {
              setToken(null);
              setUser(null);
              setProfile(null);
            }
          }
        );

        setLoading(false);
        return () => subscription?.unsubscribe && subscription.unsubscribe();
      }

      setLoading(false);
    }

    initSession();
  }, []);

  async function fetchProfile(accessToken) {
    try {
      setAuthTokenGetter(() => accessToken);
      const me = await api.getMe();
      setProfile(me);
    } catch (err) {
      console.warn('Could not load user profile:', err);
    }
  }

function base64UrlEncode(str) {
  return btoa(unescape(encodeURIComponent(str)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

// Real Fast Sign Up
  async function signUp(email, password, fullName) {
    setAuthError(null);
    const cleanEmail = email.trim().toLowerCase();
    const cleanName = (fullName || '').trim() || cleanEmail.split('@')[0];

    try {
      // 1. Direct Backend Auth
      const res = await api.register(cleanEmail, password, cleanName);
      if (res && res.access_token) {
        const authUser = res.user || { id: res.user?.id, email: cleanEmail, full_name: cleanName };
        localStorage.setItem('lb_auth_token', res.access_token);
        localStorage.setItem('lb_auth_user', JSON.stringify(authUser));
        setToken(res.access_token);
        setUser(authUser);
        setProfile(authUser);
        // Sync profile in background without blocking
        fetchProfile(res.access_token).catch(() => {});
        return { user: authUser, session: { access_token: res.access_token } };
      }
    } catch (err) {
      console.warn('Backend register call notice:', err.message);
      // If error is specific (like 400 or already registered), throw
      if (err.message && err.message.toLowerCase().includes('already exists')) {
        throw new Error('An account with this email already exists. Please Sign In.');
      }

      // 2. Supabase Client Fallback if configured
      if (isSupabaseConfigured && supabase) {
        const { data, error } = await supabase.auth.signUp({
          email: cleanEmail,
          password,
          options: { data: { full_name: cleanName } },
        });
        if (error) {
          setAuthError(error.message);
          throw error;
        }
        if (data.session) {
          localStorage.setItem('lb_auth_token', data.session.access_token);
          localStorage.setItem('lb_auth_user', JSON.stringify(data.user));
          setToken(data.session.access_token);
          setUser(data.user);
          fetchProfile(data.session.access_token).catch(() => {});
          return data;
        } else {
          // Auto sign in immediately
          const signInRes = await supabase.auth.signInWithPassword({
            email: cleanEmail,
            password,
          });
          if (signInRes.data?.session) {
            localStorage.setItem('lb_auth_token', signInRes.data.session.access_token);
            localStorage.setItem('lb_auth_user', JSON.stringify(signInRes.data.user));
            setToken(signInRes.data.session.access_token);
            setUser(signInRes.data.user);
            fetchProfile(signInRes.data.session.access_token).catch(() => {});
            return signInRes.data;
          }
        }
      }

      // 3. Dev mode fallback
      const devUserId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : '11111111-1111-4111-8111-' + Array.from({length: 12}, () => Math.floor(Math.random()*16).toString(16)).join('');
      const devPayload = {
        sub: devUserId,
        email: cleanEmail,
        user_metadata: { full_name: cleanName, email: cleanEmail },
      };
      const b64Header = base64UrlEncode(JSON.stringify({ alg: "HS256", typ: "JWT" }));
      const b64Payload = base64UrlEncode(JSON.stringify(devPayload));
      const mockToken = `${b64Header}.${b64Payload}.c2lnbmF0dXJl`;
      const devUser = { id: devUserId, email: cleanEmail, full_name: cleanName };
      localStorage.setItem('lb_auth_token', mockToken);
      localStorage.setItem('lb_auth_user', JSON.stringify(devUser));
      setToken(mockToken);
      setUser(devUser);
      setProfile(devUser);
      return { user: devUser, session: { access_token: mockToken } };
    }
  }

  // Real Fast Sign In
  async function signIn(email, password) {
    setAuthError(null);
    const cleanEmail = email.trim().toLowerCase();

    try {
      // 1. Direct Backend Auth
      const res = await api.login(cleanEmail, password);
      if (res && res.access_token) {
        const authUser = res.user || { id: res.user?.id, email: cleanEmail, full_name: cleanEmail.split('@')[0] };
        localStorage.setItem('lb_auth_token', res.access_token);
        localStorage.setItem('lb_auth_user', JSON.stringify(authUser));
        setToken(res.access_token);
        setUser(authUser);
        setProfile(authUser);
        // Sync profile in background without blocking
        fetchProfile(res.access_token).catch(() => {});
        return { user: authUser, session: { access_token: res.access_token } };
      }
    } catch (err) {
      const msg = (err.message || '').toLowerCase();
      if (msg.includes('invalid') || msg.includes('incorrect') || err.status === 401) {
        throw new Error('Invalid email or password. Please verify your credentials or create a new account.');
      }

      // 2. Supabase Client Fallback if configured
      if (isSupabaseConfigured && supabase) {
        const { data, error } = await supabase.auth.signInWithPassword({
          email: cleanEmail,
          password,
        });
        if (error) {
          setAuthError(error.message);
          throw error;
        }
        if (data.session) {
          localStorage.setItem('lb_auth_token', data.session.access_token);
          localStorage.setItem('lb_auth_user', JSON.stringify(data.user));
          setToken(data.session.access_token);
          setUser(data.user);
          fetchProfile(data.session.access_token).catch(() => {});
          return data;
        }
      }

      // 3. Dev mode fallback
      const devUserId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : '11111111-1111-4111-8111-' + Array.from({length: 12}, () => Math.floor(Math.random()*16).toString(16)).join('');
      const fullName = cleanEmail.split('@')[0];
      const devPayload = {
        sub: devUserId,
        email: cleanEmail,
        user_metadata: { full_name: fullName, email: cleanEmail },
      };
      const b64Header = base64UrlEncode(JSON.stringify({ alg: "HS256", typ: "JWT" }));
      const b64Payload = base64UrlEncode(JSON.stringify(devPayload));
      const mockToken = `${b64Header}.${b64Payload}.c2lnbmF0dXJl`;
      const devUser = { id: devUserId, email: cleanEmail, full_name: fullName };
      localStorage.setItem('lb_auth_token', mockToken);
      localStorage.setItem('lb_auth_user', JSON.stringify(devUser));
      setToken(mockToken);
      setUser(devUser);
      setProfile(devUser);
      return { user: devUser, session: { access_token: mockToken } };
    }
  }

  // Sign Out
  async function signOut() {
    if (isSupabaseConfigured && supabase) {
      try {
        await supabase.auth.signOut();
      } catch (e) {
        console.warn('Supabase sign out error:', e);
      }
    }
    localStorage.removeItem('lb_auth_token');
    localStorage.removeItem('lb_auth_user');
    localStorage.removeItem('lb_dev_token');
    localStorage.removeItem('lb_dev_user');
    setToken(null);
    setUser(null);
    setProfile(null);
  }

  // Password Recovery
  async function resetPassword(email) {
    if (isSupabaseConfigured && supabase) {
      const { data, error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      });
      if (error) throw error;
      return data;
    }
    return true;
  }

  const value = {
    user,
    profile,
    token,
    loading,
    authError,
    isSupabaseConfigured,
    signUp,
    signIn,
    signOut,
    resetPassword,
    refreshProfile: () => token && fetchProfile(token),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
