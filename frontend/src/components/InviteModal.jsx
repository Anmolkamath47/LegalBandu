import React, { useState } from 'react';
import { api } from '../services/api';
import { X, Copy, Check, Mail, ShieldAlert, Link as LinkIcon, UserPlus } from 'lucide-react';

export default function InviteModal({ isOpen, onClose, dealId, dealTitle }) {
  const [email, setEmail] = useState('');
  const [expiresInDays, setExpiresInDays] = useState(7);
  const [invitationUrl, setInvitationUrl] = useState('');
  const [copied, setCopied] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  if (!isOpen) return null;

  async function handleGenerate(e) {
    e.preventDefault();
    setGenerating(true);
    setErrorMsg('');
    try {
      const data = await api.createInvitation(dealId, {
        email: email.trim() || undefined,
        expires_in_days: Number(expiresInDays),
      });
      setInvitationUrl(data.invitation_url);
    } catch (err) {
      setErrorMsg(err.message || 'Could not create invitation link.');
    } finally {
      setGenerating(false);
    }
  }

  function handleCopy() {
    if (invitationUrl) {
      navigator.clipboard.writeText(invitationUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
      <div 
        className="w-full max-w-md bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
          <div>
            <h2 className="text-base font-bold text-navy-900 flex items-center space-x-2">
              <UserPlus className="w-4 h-4 text-blue-600" />
              <span>Invite Counterparty</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5 truncate max-w-xs">
              {dealTitle}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-200/50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {errorMsg && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-xs">
              {errorMsg}
            </div>
          )}

          {!invitationUrl ? (
            <form onSubmit={handleGenerate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Recipient Email (Optional)
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    id="input-invite-email"
                    type="email"
                    placeholder="partner@business.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 focus:border-navy-900 outline-none"
                  />
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  If set, only a user logging in with this specific email will be permitted to join.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Link Expiration
                </label>
                <select
                  value={expiresInDays}
                  onChange={(e) => setExpiresInDays(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 focus:border-navy-900 outline-none bg-white"
                >
                  <option value={7}>7 Days</option>
                  <option value={14}>14 Days</option>
                  <option value={30}>30 Days</option>
                </select>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-md text-slate-600 text-[11px] flex items-start space-x-2">
                <ShieldAlert className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                <span>
                  The counterparty must authenticate before accessing the private room. 
                  Once accepted, the token is invalidated to prevent reuse.
                </span>
              </div>

              <button
                id="btn-generate-invite"
                type="submit"
                disabled={generating}
                className="w-full py-2.5 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm transition-colors disabled:opacity-50"
              >
                {generating ? 'Generating Link...' : 'Generate Secure Invitation Link'}
              </button>
            </form>
          ) : (
            <div className="space-y-4 animate-in fade-in">
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-md text-emerald-800 text-xs">
                Invitation link generated! Share this URL with your business counterparty.
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Invitation Link
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    id="input-generated-link"
                    type="text"
                    readOnly
                    value={invitationUrl}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-md font-mono text-slate-700 select-all"
                  />
                  <button
                    id="btn-copy-invite-link"
                    type="button"
                    onClick={handleCopy}
                    className="px-3 py-2 bg-navy-900 hover:bg-navy-800 text-white rounded-md text-xs font-medium flex items-center space-x-1 shrink-0"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-300" />
                        <span>Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              <div className="flex justify-between items-center pt-2">
                <button
                  type="button"
                  onClick={() => setInvitationUrl('')}
                  className="text-xs text-blue-600 hover:underline"
                >
                  Create another link
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-1.5 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md"
                >
                  Done
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
