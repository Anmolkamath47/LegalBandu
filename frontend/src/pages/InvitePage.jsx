import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  ShieldCheck, 
  ArrowRight,
  User,
  Mail,
  Lock,
  Loader2,
  Sparkles,
  LogOut
} from 'lucide-react';

export default function InvitePage({ onOpenAuth }) {
  const { token } = useParams();
  const navigate = useNavigate();
  const { user, signIn, signUp, signOut } = useAuth();

  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Inline auth state for non-authenticated recipients
  const [authMode, setAuthMode] = useState('signup'); // 'signup' | 'signin'
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authFullName, setAuthFullName] = useState('');
  const [authSubmitting, setAuthSubmitting] = useState(false);
  const [authError, setAuthError] = useState('');

  useEffect(() => {
    loadInviteInfo();
  }, [token]);

  async function loadInviteInfo() {
    setLoading(true);
    setErrorMsg('');
    try {
      const data = await api.getInvitationInfo(token);
      setInfo(data);
      if (data.invitation_email) {
        setAuthEmail(data.invitation_email);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Invalid or expired invitation link.');
    } finally {
      setLoading(false);
    }
  }

  async function handleAccept() {
    if (!user) {
      return;
    }

    setAccepting(true);
    setErrorMsg('');

    try {
      const res = await api.acceptInvitation(token);
      navigate(`/deal/${res.deal_id}`);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to accept invitation.');
    } finally {
      setAccepting(false);
    }
  }

  async function handleInlineAuthSubmit(e) {
    e.preventDefault();
    setAuthError('');
    setAuthSubmitting(true);

    const cleanEmail = authEmail.trim();
    if (!cleanEmail) {
      setAuthError('Please enter a valid email address.');
      setAuthSubmitting(false);
      return;
    }

    if (!authPassword || authPassword.length < 6) {
      setAuthError('Password must be at least 6 characters.');
      setAuthSubmitting(false);
      return;
    }

    try {
      if (authMode === 'signup') {
        const nameToUse = authFullName.trim() || cleanEmail.split('@')[0];
        await signUp(cleanEmail, authPassword, nameToUse);
      } else {
        await signIn(cleanEmail, authPassword);
      }

      // Automatically accept the invitation immediately after authenticating
      try {
        const res = await api.acceptInvitation(token);
        navigate(`/deal/${res.deal_id}`);
      } catch (acceptErr) {
        // If immediate accept has slight propagation delay, user can click "Accept & Enter"
        console.warn('Post-login accept attempt notice:', acceptErr);
      }
    } catch (err) {
      setAuthError(err.message || 'Authentication failed. Please verify your details.');
    } finally {
      setAuthSubmitting(false);
    }
  }

  async function handleSwitchAccount() {
    await signOut();
    if (info?.invitation_email) {
      setAuthEmail(info.invitation_email);
    }
  }

  const isEmailMismatch = Boolean(
    user && 
    info?.invitation_email && 
    user.email?.toLowerCase() !== info.invitation_email?.toLowerCase()
  );

  return (
    <div className="min-h-[85vh] flex items-center justify-center p-4 bg-slate-50">
      <div className="w-full max-w-lg bg-white rounded-xl shadow-xl border border-slate-200 p-6 sm:p-8 text-center animate-in fade-in">
        
        {/* Header Icon */}
        <div className="w-12 h-12 rounded-full bg-navy-900 text-white flex items-center justify-center mx-auto mb-4 shadow-md">
          <FileText className="w-6 h-6 text-blue-400" />
        </div>

        <h1 className="text-xl font-bold text-navy-900">
          Deal Room Invitation
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          You have been invited to review, collaborate, and confirm agreement terms.
        </p>

        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center space-y-2 text-xs text-slate-400">
            <Loader2 className="w-5 h-5 animate-spin text-navy-900" />
            <span>Validating secure invitation token...</span>
          </div>
        ) : errorMsg ? (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 text-left">
            <div className="flex items-start space-x-2">
              <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-800">Invitation Unavailable</p>
                <p className="mt-1">{errorMsg}</p>
                <button
                  type="button"
                  onClick={() => navigate('/')}
                  className="mt-3 text-xs text-blue-600 hover:underline font-semibold block"
                >
                  Return to Home
                </button>
              </div>
            </div>
          </div>
        ) : info ? (
          <div className="mt-6 space-y-4 text-left">
            {/* Deal Overview Card */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-2.5">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                  Agreement Title
                </span>
                <span className="text-sm font-bold text-navy-900 block">
                  {info.deal_title}
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-700">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                    Invited By
                  </span>
                  <span>{info.creator_name}</span>
                </div>
                {info.category && (
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                      Category
                    </span>
                    <span className="capitalize">{info.category}</span>
                  </div>
                )}
                {info.invitation_email && (
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                      Recipient
                    </span>
                    <span className="font-semibold text-blue-900">{info.invitation_email}</span>
                  </div>
                )}
              </div>

              {info.description && (
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                    Scope & Description
                  </span>
                  <span className="text-xs text-slate-600 block line-clamp-3">
                    {info.description}
                  </span>
                </div>
              )}
            </div>

            {/* Status alerts */}
            {info.is_expired ? (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-md text-amber-800 text-xs flex items-center space-x-2">
                <Clock className="w-4 h-4 shrink-0" />
                <span>This invitation token has expired. Please ask {info.creator_name} to issue a new invite.</span>
              </div>
            ) : info.is_already_accepted ? (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-md text-blue-800 text-xs flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-blue-600" />
                  <span>This invitation has already been accepted.</span>
                </div>
                <button
                  type="button"
                  onClick={() => navigate(`/deal/${info.deal_id}`)}
                  className="px-3 py-1 bg-navy-900 text-white rounded text-xs font-semibold hover:bg-navy-800"
                >
                  Go to Deal
                </button>
              </div>
            ) : user ? (
              /* User is authenticated */
              <div className="space-y-3">
                {isEmailMismatch ? (
                  <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-900 space-y-2">
                    <p className="font-semibold flex items-center space-x-1.5">
                      <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                      <span>Email Mismatch Notice</span>
                    </p>
                    <p className="text-[11px] text-amber-800">
                      This invitation was addressed specifically to <b>{info.invitation_email}</b>. 
                      You are currently signed in as <b>{user.email}</b>.
                    </p>
                    <button
                      type="button"
                      onClick={handleSwitchAccount}
                      className="px-3 py-1.5 bg-white border border-amber-300 text-amber-900 hover:bg-amber-100 rounded text-xs font-medium flex items-center space-x-1"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>Switch Account to {info.invitation_email}</span>
                    </button>
                  </div>
                ) : (
                  <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-md text-xs text-emerald-900 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-emerald-700 block tracking-wider">
                        Ready to Join as Counterparty
                      </span>
                      <span className="font-semibold text-emerald-950">
                        {user.email}
                      </span>
                    </div>
                    <span className="text-[11px] text-emerald-700 font-medium flex items-center space-x-1">
                      <ShieldCheck className="w-4 h-4 text-emerald-600" />
                      <span>Authenticated</span>
                    </span>
                  </div>
                )}

                {!isEmailMismatch && (
                  <button
                    id="btn-accept-invitation"
                    onClick={handleAccept}
                    disabled={accepting}
                    className="w-full py-3 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-md transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
                  >
                    {accepting ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Joining Deal Room...</span>
                      </>
                    ) : (
                      <>
                        <span>Accept & Enter Deal Room</span>
                        <ArrowRight className="w-4 h-4 text-blue-300" />
                      </>
                    )}
                  </button>
                )}
              </div>
            ) : (
              /* User is NOT authenticated - Frictionless In-Place Join Form */
              <div className="border border-slate-200 rounded-lg p-4 bg-white shadow-sm space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <div className="flex items-center space-x-1.5">
                    <ShieldCheck className="w-4 h-4 text-blue-600" />
                    <span className="text-xs font-bold text-navy-900">
                      {authMode === 'signup' ? '1-Click Join (Create Account)' : 'Sign In to Enter'}
                    </span>
                  </div>
                  <div className="flex space-x-1 text-[11px]">
                    <button
                      type="button"
                      onClick={() => setAuthMode(authMode === 'signup' ? 'signin' : 'signup')}
                      className="text-blue-600 hover:underline font-medium"
                    >
                      {authMode === 'signup' ? 'Already have an account? Sign in' : 'New here? 1-Click Join'}
                    </button>
                  </div>
                </div>

                {authError && (
                  <div className="p-2.5 bg-red-50 border border-red-200 rounded text-[11px] text-red-700">
                    {authError}
                  </div>
                )}

                <form onSubmit={handleInlineAuthSubmit} className="space-y-3">
                  {authMode === 'signup' && (
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                        Your Full Name / Representative Name
                      </label>
                      <div className="relative">
                        <User className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                        <input
                          type="text"
                          required
                          placeholder="e.g. Ramesh Kumar"
                          value={authFullName}
                          onChange={(e) => setAuthFullName(e.target.value)}
                          className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-navy-900 outline-none"
                        />
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Email Address
                    </label>
                    <div className="relative">
                      <Mail className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                      <input
                        type="email"
                        required
                        placeholder="your-email@business.com"
                        value={authEmail}
                        onChange={(e) => setAuthEmail(e.target.value)}
                        className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-navy-900 outline-none"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Password
                    </label>
                    <div className="relative">
                      <Lock className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                      <input
                        type="password"
                        required
                        placeholder="••••••••"
                        value={authPassword}
                        onChange={(e) => setAuthPassword(e.target.value)}
                        className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-navy-900 outline-none"
                      />
                    </div>
                  </div>

                  <button
                    id="btn-inline-join"
                    type="submit"
                    disabled={authSubmitting}
                    className="w-full py-2.5 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm transition-colors flex items-center justify-center space-x-2 disabled:opacity-50"
                  >
                    {authSubmitting ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Verifying & Entering Room...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5 text-blue-300" />
                        <span>{authMode === 'signup' ? 'Create Account & Enter Deal Room' : 'Sign In & Enter Deal Room'}</span>
                      </>
                    )}
                  </button>
                </form>

                <p className="text-[10px] text-slate-400 text-center">
                  By joining, you enter a mutually confirmed deal room where agreements can be negotiated and confirmed.
                </p>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
