import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { X, Lock, Mail, User, AlertCircle, CheckCircle2, Eye, EyeOff, ArrowRight, Loader2 } from 'lucide-react';

export default function AuthModal({ isOpen, onClose, initialMode = 'signin', onSuccess }) {
  const [mode, setMode] = useState(initialMode); // 'signin' | 'signup' | 'forgot'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const { signIn, signUp, resetPassword } = useAuth();

  useEffect(() => {
    if (isOpen) {
      setMode(initialMode || 'signin');
      setErrorMsg('');
      setSuccessMsg('');
      setSubmitting(false);
    }
  }, [isOpen, initialMode]);

  if (!isOpen) return null;

  function switchMode(newMode) {
    setMode(newMode);
    setErrorMsg('');
    setSuccessMsg('');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');
    setSubmitting(true);

    const cleanEmail = email.trim();
    if (!cleanEmail) {
      setErrorMsg('Please enter your email address.');
      setSubmitting(false);
      return;
    }

    // Safety timeout promise to guarantee form never hangs
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Connection timed out. Please check your network and try again.')), 12000)
    );

    try {
      if (mode === 'forgot') {
        await Promise.race([resetPassword(cleanEmail), timeoutPromise]);
        setSuccessMsg('A password reset link has been sent to your email.');
      } else if (mode === 'signup') {
        if (!fullName.trim()) {
          setErrorMsg('Please enter your full name or company representative name.');
          setSubmitting(false);
          return;
        }
        await Promise.race([
          signUp(cleanEmail, password, fullName.trim()),
          timeoutPromise
        ]);
        onSuccess && onSuccess();
        onClose();
      } else {
        // Sign In
        await Promise.race([
          signIn(cleanEmail, password),
          timeoutPromise
        ]);
        onSuccess && onSuccess();
        onClose();
      }
    } catch (err) {
      const rawMsg = err.message || 'Authentication failed. Please verify your credentials.';
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
              {mode === 'forgot' ? 'Reset Password' : mode === 'signup' ? 'Create Account' : 'Sign In to Legalbandu'}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {mode === 'forgot'
                ? 'Enter your email to receive recovery instructions'
                : 'Direct access to your deal rooms, agreement reviews & e-signatures'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-200/50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mode Selector Tabs (Sign In vs Create Account) */}
        {mode !== 'forgot' && (
          <div className="grid grid-cols-2 p-1.5 bg-slate-100 border-b border-slate-200 text-xs font-semibold">
            <button
              type="button"
              id="tab-signin"
              onClick={() => switchMode('signin')}
              className={`py-2 rounded-md transition-all text-center ${
                mode === 'signin'
                  ? 'bg-white text-navy-900 shadow-sm font-bold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              id="tab-signup"
              onClick={() => switchMode('signup')}
              className={`py-2 rounded-md transition-all text-center ${
                mode === 'signup'
                  ? 'bg-white text-navy-900 shadow-sm font-bold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Create Account
            </button>
          </div>
        )}

        {/* Form Body */}
        <div className="p-6">
          {errorMsg && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-2 text-red-700 text-xs animate-in fade-in">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-start space-x-2 text-emerald-700 text-xs animate-in fade-in">
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{successMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'signup' && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Full Name / Representative <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    id="input-fullname"
                    type="text"
                    required
                    placeholder="e.g. Anmol Kamath"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 focus:border-navy-900 outline-none"
                  />
                </div>
              </div>
            )}

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
                  placeholder="name@company.com"
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
                  {mode === 'signin' && (
                    <button
                      type="button"
                      onClick={() => switchMode('forgot')}
                      className="text-[11px] text-blue-600 hover:text-blue-800"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    id="input-password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    minLength={6}
                    placeholder={mode === 'signup' ? 'Choose password (min 6 characters)' : 'Enter your password'}
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
              className="w-full py-2.5 bg-navy-900 hover:bg-navy-800 active:scale-[0.99] text-white text-xs font-semibold rounded-lg shadow-sm transition-all disabled:opacity-50 flex items-center justify-center space-x-2"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-white" />
                  <span>{mode === 'signup' ? 'Creating Account...' : 'Signing In...'}</span>
                </>
              ) : (
                <>
                  <span>
                    {mode === 'forgot'
                      ? 'Send Reset Link'
                      : mode === 'signup'
                      ? 'Create Account & Access'
                      : 'Sign In to Dashboard'}
                  </span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Bottom Switcher */}
          <div className="mt-5 text-center text-xs text-slate-500 pt-4 border-t border-slate-100">
            {mode === 'signin' && (
              <p>
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={() => switchMode('signup')}
                  className="font-bold text-navy-900 hover:text-blue-600 underline ml-1"
                >
                  Create one now
                </button>
              </p>
            )}

            {mode === 'signup' && (
              <p>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => switchMode('signin')}
                  className="font-bold text-navy-900 hover:text-blue-600 underline ml-1"
                >
                  Sign In here
                </button>
              </p>
            )}

            {mode === 'forgot' && (
              <p>
                Remembered your password?{' '}
                <button
                  type="button"
                  onClick={() => switchMode('signin')}
                  className="font-bold text-navy-900 hover:text-blue-600 underline ml-1"
                >
                  Back to Sign In
                </button>
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
