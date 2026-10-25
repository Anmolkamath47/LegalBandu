import React, { useState } from 'react';
import { api } from '../services/api';
import { 
  X, 
  Copy, 
  Check, 
  Mail, 
  ShieldAlert, 
  UserPlus, 
  ExternalLink, 
  Send, 
  CheckCircle2,
  Clock,
  Sparkles
} from 'lucide-react';

export default function InviteModal({ isOpen, onClose, dealId, dealTitle, creatorName }) {
  const [email, setEmail] = useState('');
  const [expiresInDays, setExpiresInDays] = useState(7);
  const [invitationUrl, setInvitationUrl] = useState('');
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedEmail, setCopiedEmail] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  if (!isOpen) return null;

  async function handleGenerate(e) {
    if (e) e.preventDefault();
    setGenerating(true);
    setErrorMsg('');
    try {
      const data = await api.createInvitation(dealId, {
        email: email.trim() || undefined,
        expires_in_days: Number(expiresInDays),
      });

      // Always guarantee the link uses current window origin (e.g. https://legal-bandu.vercel.app)
      const currentOrigin = typeof window !== 'undefined' ? window.location.origin : '';
      const rawToken = data.invitation_url.split('/invite/')[1] || '';
      const realUrl = rawToken ? `${currentOrigin}/invite/${rawToken}` : data.invitation_url;
      setInvitationUrl(realUrl);
    } catch (err) {
      setErrorMsg(err.message || 'Could not create invitation link.');
    } finally {
      setGenerating(false);
    }
  }

  const subject = `[Legalbandu] Invitation to join Deal Room: ${dealTitle || 'Agreement'}`;
  const emailBody = `Hello,

You have been invited${creatorName ? ` by ${creatorName}` : ''} to review, clarify, and confirm the agreement terms for "${dealTitle || 'our business agreement'}" on Legalbandu.

👉 Click the secure link below to enter our private deal room:
${invitationUrl}

• Access deal terms, conversation history, and bond verifications
• Propose clarifications and track revision history
• E-sign and generate a legally binding stamped agreement

This invitation link is valid for ${expiresInDays} days.

Best regards,
${creatorName || 'Your Business Partner'}
Sent via Legalbandu — From Handshake to Contract`;

  function handleCopyLink() {
    if (!invitationUrl) return;
    navigator.clipboard.writeText(invitationUrl);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  }

  function handleCopyFullEmail() {
    if (!invitationUrl) return;
    const fullText = `Subject: ${subject}\n\n${emailBody}`;
    navigator.clipboard.writeText(fullText);
    setCopiedEmail(true);
    setTimeout(() => setCopiedEmail(false), 2500);
  }

  function handleOpenGmail() {
    if (!invitationUrl) return;
    const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(email.trim())}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(emailBody)}`;
    window.open(gmailUrl, '_blank', 'noopener,noreferrer');
  }

  function handleOpenDefaultMail() {
    if (!invitationUrl) return;
    const mailtoUrl = `mailto:${encodeURIComponent(email.trim())}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(emailBody)}`;
    window.location.href = mailtoUrl;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
      <div 
        className="w-full max-w-lg bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
          <div>
            <h2 className="text-base font-bold text-navy-900 flex items-center space-x-2">
              <UserPlus className="w-4 h-4 text-blue-600" />
              <span>Invite Counterparty to Deal Room</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5 truncate max-w-sm">
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
                  Counterparty Email Address
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
                    autoFocus
                  />
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  We'll pre-fill a professional invitation email so you can send it with 1-click via Gmail or your mail app.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Link Expiration Duration
                </label>
                <div className="relative">
                  <Clock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <select
                    value={expiresInDays}
                    onChange={(e) => setExpiresInDays(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 focus:border-navy-900 outline-none bg-white"
                  >
                    <option value={7}>7 Days (Recommended)</option>
                    <option value={14}>14 Days</option>
                    <option value={30}>30 Days</option>
                  </select>
                </div>
              </div>

              <div className="p-3 bg-blue-50/70 border border-blue-200/60 rounded-md text-slate-600 text-[11px] flex items-start space-x-2">
                <ShieldAlert className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                <span>
                  The counterparty can join with 1 click directly through email. Their acceptance is logged with a tamper-evident SHA-256 audit timestamp.
                </span>
              </div>

              <button
                id="btn-generate-invite"
                type="submit"
                disabled={generating}
                className="w-full py-2.5 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm transition-colors flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                <Sparkles className="w-3.5 h-3.5 text-blue-300" />
                <span>{generating ? 'Creating Real Invite Link...' : 'Create Real Invite Link & Mail Options'}</span>
              </button>
            </form>
          ) : (
            <div className="space-y-4 animate-in fade-in">
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-md text-emerald-800 text-xs flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span className="font-medium">
                  Real invitation link generated! Send it directly via email or copy the link below.
                </span>
              </div>

              {/* Direct Mail Actions */}
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                    Send Invitation via Email
                  </span>
                  {email && (
                    <span className="text-[11px] text-slate-500 truncate max-w-[200px]" title={email}>
                      To: <b>{email}</b>
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    id="btn-send-gmail"
                    type="button"
                    onClick={handleOpenGmail}
                    className="py-2 px-3 bg-white hover:bg-red-50 border border-red-200 text-red-700 hover:text-red-800 text-xs font-semibold rounded-md shadow-sm flex items-center justify-center space-x-1.5 transition-colors"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>Open in Gmail</span>
                  </button>

                  <button
                    id="btn-send-mailto"
                    type="button"
                    onClick={handleOpenDefaultMail}
                    className="py-2 px-3 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm flex items-center justify-center space-x-1.5 transition-colors"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Send via Mail App</span>
                  </button>
                </div>

                <button
                  id="btn-copy-full-email"
                  type="button"
                  onClick={handleCopyFullEmail}
                  className="w-full py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-medium rounded border border-slate-200 flex items-center justify-center space-x-1.5 transition-colors"
                >
                  {copiedEmail ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                      <span className="text-emerald-700 font-semibold">Full Email Text Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5 text-slate-500" />
                      <span>Copy Full Invitation Email Text (with Link & Instructions)</span>
                    </>
                  )}
                </button>
              </div>

              {/* Direct Link Copy */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Direct Room Link
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
                    onClick={handleCopyLink}
                    className="px-3 py-2 bg-navy-900 hover:bg-navy-800 text-white rounded-md text-xs font-medium flex items-center space-x-1 shrink-0 transition-colors"
                  >
                    {copiedLink ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-300" />
                        <span>Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copy Link</span>
                      </>
                    )}
                  </button>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  This link allows the counterparty to enter the room, review conversations and agreement terms, and e-sign.
                </p>
              </div>

              <div className="flex justify-between items-center pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setInvitationUrl('')}
                  className="text-xs text-blue-600 hover:underline"
                >
                  Create another invite
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-1.5 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md transition-colors"
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
