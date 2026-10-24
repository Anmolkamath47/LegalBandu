import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { X, Lock, Mail, User, AlertCircle, CheckCircle2, Eye, EyeOff, Zap } from 'lucide-react';

export default function AuthModal({ isOpen, onClose, initialMode = 'signin', onSuccess }) {
  const [mode, setMode] = useState(initialMode); // 'signin' | 'signup' | 'forgot'
  const [email, setEmail] = useState('anmolravindrakamath@gmail.com');
  const [password, setPassword] = useState('Anmolkamath@47');
  const [fullName, setFullName] = useState('Anmol Kamath');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const { continueWithCredentials, quickDemoLogin, resetPassword, isSupabaseConfigured } = useAuth();

  if (!isOpen) return null;

  async function handleQuickAccess() {
    setErrorMsg('');
    setSuccessMsg('');
    setSubmitting(true);
    try {
      await quickDemoLogin(email || 'anmolravindrakamath@gmail.com', fullName || 'Anmol Kamath');
      onSuccess && onSuccess();
      onClose();
    } catch (err) {
      setErrorMsg(err.message || 'Quick login failed.');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');
    setSubmitting(true);

    try {
      if (mode === 'forgot') {
        await resetPassword(email.trim());
        setSuccessMsg('Password reset link sent to your email.');
      } else {
        // Unified seamless auth: automatically signs in or creates account without mode switching
        await continueWithCredentials(email.trim(), password, fullName.trim());
        onSuccess && onSuccess();
        onClose();
      }
    } catch (err) {
      const rawMsg = err.message || 'Authentication failed. Please check your credentials.';
      setErrorMsg(rawMsg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
      <div 
        className="w-full max-w-md bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
          <div>
            <h2 className="text-base font-bold text-navy-900">
              Welcome to Legalbandu
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Secure, instant access to your deal rooms & agreements
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-200/50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <div className="p-6">
          {/* 1-Click Quick Access Button */}
          <button
            type="button"
            id="btn-quick-login"
            onClick={handleQuickAccess}
            disabled={submitting}
            className="w-full mb-5 py-2.5 px-4 bg-navy-900 hover:bg-navy-800 active:scale-[0.99] text-white text-xs font-semibold rounded-lg shadow-sm flex items-center justify-center space-x-2 transition-all border border-navy-950"
          >
            <Zap className="w-4 h-4 text-amber-400 fill-amber-400" />
            <span>⚡ 1-Click Instant Sign In ({email.split('@')[0]})</span>
          </button>

          <div className="relative mb-5">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-white px-2 text-slate-500">or continue with email</span>
            </div>
          </div>

          {errorMsg && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md flex items-start space-x-2 text-red-700 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-md flex items-start space-x-2 text-emerald-700 text-xs">
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{successMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Full Name / Representative
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  id="input-fullname"
                  type="text"
                  placeholder="Your Name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 focus:border-navy-900 outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Email Address <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  id="input-email"
                  type="email"
                  required
                  placeholder="name@business.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 focus:border-navy-900 outline-none"
                />
              </div>
            </div>

            {mode !== 'forgot' && (
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-xs font-semibold text-slate-700">
                    Password <span className="text-red-500">*</span>
                  </label>
                  <button
                    type="button"
                    onClick={() => setMode('forgot')}
                    className="text-[11px] text-blue-600 hover:text-blue-800"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    id="input-password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    minLength={6}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pl-9 pr-9 py-2 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 focus:border-navy-900 outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            )}

            <button
              id="btn-auth-submit"
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 bg-blue-700 hover:bg-blue-800 active:scale-[0.99] text-white text-xs font-semibold rounded-md shadow-sm transition-all disabled:opacity-50"
            >
              {submitting ? 'Authenticating...' : mode === 'forgot' ? 'Send Reset Link' : 'Continue to Dashboard →'}
            </button>
          </form>

          <p className="mt-4 text-[11px] text-center text-slate-500">
            Smart Login: Automatically signs in if you have an account, or creates one instantly if you're new.
          </p>
        </div>
      </div>
    </div>
  );
}
