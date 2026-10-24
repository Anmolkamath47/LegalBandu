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
      if (isSupabaseConfigured && supabase) {
        try {
          const { data: { session }, error } = await supabase.auth.getSession();
          if (session && !error) {
            setToken(session.access_token);
            setUser(session.user);
            await fetchProfile(session.access_token);
          }
        } catch (err) {
          console.error('Error fetching Supabase session:', err);
        }

        const { data: { subscription } } = supabase.auth.onAuthStateChange(
          async (event, session) => {
            if (session) {
              setToken(session.access_token);
              setUser(session.user);
              await fetchProfile(session.access_token);
            } else {
              setToken(null);
              setUser(null);
              setProfile(null);
            }
          }
        );

        setLoading(false);
        return () => subscription.unsubscribe();
      } else {
        // Check for local development test session in localStorage
        const savedDevToken = localStorage.getItem('lb_dev_token');
        const savedDevUser = localStorage.getItem('lb_dev_user');
        if (savedDevToken && savedDevUser) {
          try {
            setToken(savedDevToken);
            setUser(JSON.parse(savedDevUser));
          } catch (e) {
            localStorage.removeItem('lb_dev_token');
            localStorage.removeItem('lb_dev_user');
          }
        }
        setLoading(false);
      }
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

  // Real Supabase Sign Up
  async function signUp(email, password, fullName) {
    setAuthError(null);
    if (!isSupabaseConfigured || !supabase) {
      // Local dev mode fallback if Supabase credentials are not in .env
      const devUserId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : '11111111-1111-4111-8111-' + Array.from({length: 12}, () => Math.floor(Math.random()*16).toString(16)).join('');
      const devPayload = {
        sub: devUserId,
        email,
        user_metadata: { full_name: fullName, email },
      };
      const b64Header = base64UrlEncode(JSON.stringify({ alg: "HS256", typ: "JWT" }));
      const b64Payload = base64UrlEncode(JSON.stringify(devPayload));
      const mockToken = `${b64Header}.${b64Payload}.c2lnbmF0dXJl`;

      const devUser = { id: devUserId, email, full_name: fullName };
      localStorage.setItem('lb_dev_token', mockToken);
      localStorage.setItem('lb_dev_user', JSON.stringify(devUser));
      setToken(mockToken);
      setUser(devUser);
      setProfile({ id: devUserId, email, full_name: fullName });
      return { user: devUser, session: { access_token: mockToken } };
    }

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: fullName,
        },
      },
    });

    if (error) {
      setAuthError(error.message);
      throw error;
    }

    if (data.session) {
      setToken(data.session.access_token);
      setUser(data.user);
      await fetchProfile(data.session.access_token);
    } else {
      // Auto-sign in immediately since email is auto-confirmed by database trigger
      try {
        const signInRes = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (signInRes.data?.session) {
          setToken(signInRes.data.session.access_token);
          setUser(signInRes.data.user);
          await fetchProfile(signInRes.data.session.access_token);
          return signInRes.data;
        }
      } catch (e) {
        console.warn('Auto-login attempt after signup:', e);
      }
    }

    return data;
  }

  // Real Supabase Sign In
  async function signIn(email, password) {
    setAuthError(null);
    if (!isSupabaseConfigured || !supabase) {
      // Local dev mode fallback
      const devUserId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : '11111111-1111-4111-8111-' + Array.from({length: 12}, () => Math.floor(Math.random()*16).toString(16)).join('');
      const fullName = email.split('@')[0];
      const devPayload = {
        sub: devUserId,
        email,
        user_metadata: { full_name: fullName, email },
      };
      const b64Header = base64UrlEncode(JSON.stringify({ alg: "HS256", typ: "JWT" }));
      const b64Payload = base64UrlEncode(JSON.stringify(devPayload));
      const mockToken = `${b64Header}.${b64Payload}.c2lnbmF0dXJl`;

      const devUser = { id: devUserId, email, full_name: fullName };
      localStorage.setItem('lb_dev_token', mockToken);
      localStorage.setItem('lb_dev_user', JSON.stringify(devUser));
      setToken(mockToken);
      setUser(devUser);
      setProfile({ id: devUserId, email, full_name: fullName });
      return { user: devUser, session: { access_token: mockToken } };
    }


    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      setAuthError(error.message);
      throw error;
    }

    if (data.session) {
      setToken(data.session.access_token);
      setUser(data.user);
      await fetchProfile(data.session.access_token);
    }

    return data;
  }

  // Sign Out
  async function signOut() {
    if (isSupabaseConfigured && supabase) {
      await supabase.auth.signOut();
    }
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
