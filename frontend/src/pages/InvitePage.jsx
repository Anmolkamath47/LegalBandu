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
  LogIn
} from 'lucide-react';

export default function InvitePage({ onOpenAuth }) {
  const { token } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    loadInviteInfo();
  }, [token]);

  async function loadInviteInfo() {
    setLoading(true);
    setErrorMsg('');
    try {
      const data = await api.getInvitationInfo(token);
      setInfo(data);
    } catch (err) {
      setErrorMsg(err.message || 'Invalid or expired invitation link.');
    } finally {
      setLoading(false);
    }
  }

  async function handleAccept() {
    if (!user) {
      onOpenAuth('signin');
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

  return (
    <div className="min-h-[80vh] flex items-center justify-center p-4 bg-slate-50">
      <div className="w-full max-w-md bg-white rounded-xl shadow-xl border border-slate-200 p-6 sm:p-8 text-center animate-in fade-in">
        
        <div className="w-12 h-12 rounded-full bg-navy-900 text-white flex items-center justify-center mx-auto mb-4">
          <FileText className="w-6 h-6 text-blue-400" />
        </div>

        <h1 className="text-xl font-bold text-navy-900">
          Deal Room Invitation
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          You have been invited to participate in a mutually reviewed agreement.
        </p>

        {loading ? (
          <div className="py-8 text-xs text-slate-400">
            Validating invitation token...
          </div>
        ) : errorMsg ? (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
            <AlertCircle className="w-6 h-6 text-red-500 mx-auto mb-2" />
            <p className="font-semibold">Invitation Unavailable</p>
            <p className="mt-1">{errorMsg}</p>
          </div>
        ) : info ? (
          <div className="mt-6 space-y-4 text-left">
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                  Deal Title
                </span>
                <span className="text-sm font-bold text-navy-900 block">
                  {info.deal_title}
                </span>
              </div>

              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                  Invited By
                </span>
                <span className="text-xs text-slate-700 block">
                  {info.creator_name} ({info.category})
                </span>
              </div>

              {info.description && (
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                    Description
                  </span>
                  <span className="text-xs text-slate-600 block line-clamp-3">
                    {info.description}
                  </span>
                </div>
              )}
            </div>

            {info.is_expired ? (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-md text-amber-800 text-xs flex items-center space-x-2">
                <Clock className="w-4 h-4 shrink-0" />
                <span>This invitation token has expired. Request a new invite from the creator.</span>
              </div>
            ) : info.is_already_accepted ? (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-md text-blue-800 text-xs flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>This invitation has already been accepted. Sign in to view the deal.</span>
              </div>
            ) : (
              <>
                {!user ? (
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-md text-slate-600 text-xs">
                    <p className="font-medium text-slate-900 mb-1 flex items-center space-x-1.5">
                      <ShieldCheck className="w-4 h-4 text-emerald-600" />
                      <span>Authentication Required</span>
                    </p>
                    <p className="text-[11px]">
                      Please sign in or create an account with your email to access this private deal room.
                    </p>
                    <div className="mt-3 flex space-x-2">
                      <button
                        onClick={() => onOpenAuth('signin')}
                        className="flex-1 py-2 bg-white border border-slate-300 hover:bg-slate-100 text-navy-900 text-xs font-semibold rounded-md shadow-sm"
                      >
                        Sign In
                      </button>
                      <button
                        onClick={() => onOpenAuth('signup')}
                        className="flex-1 py-2 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm"
                      >
                        Create Account
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    id="btn-accept-invitation"
                    onClick={handleAccept}
                    disabled={accepting}
                    className="w-full py-2.5 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm transition-colors flex items-center justify-center space-x-1.5 disabled:opacity-50"
                  >
                    <span>{accepting ? 'Joining Room...' : 'Accept & Enter Deal Room'}</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                )}
              </>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
