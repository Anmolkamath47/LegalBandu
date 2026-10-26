import React, { useState } from 'react';
import { api } from '../services/api';
import {
  X,
  Copy,
  Check,
  Mail,
  Scale,
  Send,
  ExternalLink,
  ShieldCheck,
  Clock,
  Sparkles,
} from 'lucide-react';

export default function InviteLawyerModal({ isOpen, onClose, dealId, dealTitle, creatorName, onInvited }) {
  const [email, setEmail] = useState('');
  const [expiresInDays, setExpiresInDays] = useState(14);
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
      const data = await api.createLawyerInvitation(dealId, {
        email: email.trim() || undefined,
        expires_in_days: Number(expiresInDays),
      });

      const currentOrigin = typeof window !== 'undefined' ? window.location.origin : '';
      const rawToken = data.invitation_url.split('/invite/')[1] || '';
      const realUrl = rawToken ? `${currentOrigin}/invite/${rawToken}` : data.invitation_url;
      setInvitationUrl(realUrl);
      if (onInvited) {
        onInvited();
      }
    } catch (err) {
      setErrorMsg(err.message || 'Could not create lawyer invitation link.');
    } finally {
      setGenerating(false);
    }
  }

  const subject = `[Legal Review Request] Formal Agreement Review for: "${dealTitle || 'Commercial Contract'}"`;
  const emailBody = `Respected Counsel / Advocate,

You are cordially invited${creatorName ? ` by ${creatorName}` : ''} to conduct a formal legal review of the draft agreement for "${dealTitle || 'our commercial agreement'}" on Legalbandu.

👉 Secure Legal Counsel Review Link:
${invitationUrl}

Scope of Review:
• Access authorized bilateral agreement draft and background context
• Suggest specific clause modifications, add comments, and provide statutory legal rationale
• Directly discuss and align on proposed revisions with the agreement owner
• Formally approve or recommend modifications prior to stamp duty execution

Security Notice:
This is a secure, single-use invitation link that requires your advocate authentication. It is valid for ${expiresInDays} days.

Best regards,
${creatorName || 'Agreement Owner'}
Documented via Legalbandu — Secure Contract & Legal Review Infrastructure`;

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
    const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(
      email.trim()
    )}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(emailBody)}`;
    window.open(gmailUrl, '_blank', 'noopener,noreferrer');
  }

  function handleOpenDefaultMail() {
    if (!invitationUrl) return;
    const mailtoUrl = `mailto:${encodeURIComponent(email.trim())}?subject=${encodeURIComponent(
      subject
    )}&body=${encodeURIComponent(emailBody)}`;
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
              <Scale className="w-4 h-4 text-indigo-600" />
              <span>Invite a Real Lawyer for Review</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5 truncate max-w-sm">
              Deal: <span className="font-semibold text-slate-700">{dealTitle}</span>
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
                  Advocate / Law Firm Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    id="input-lawyer-email"
                    type="email"
                    placeholder="advocate@lawfirm.in"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 focus:border-navy-900 outline-none"
                    autoFocus
                  />
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Leave blank to generate an open link, or specify an email address to restrict access strictly to that advocate.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Link Validity Period
                </label>
                <div className="relative">
                  <Clock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <select
                    value={expiresInDays}
                    onChange={(e) => setExpiresInDays(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 focus:border-navy-900 outline-none bg-white"
                  >
                    <option value={7}>7 Days</option>
                    <option value={14}>14 Days (Recommended for advocate review)</option>
                    <option value={30}>30 Days</option>
                  </select>
                </div>
              </div>

              <div className="p-3 bg-indigo-50/70 border border-indigo-200 rounded-md text-xs text-indigo-900 space-y-1">
                <div className="font-bold flex items-center space-x-1.5">
                  <ShieldCheck className="w-4 h-4 text-indigo-600" />
                  <span>Real Legal Counsel Access Control:</span>
                </div>
                <p className="text-[11px] text-indigo-800 leading-relaxed">
                  Only the invited, authenticated advocate will be granted access to review the draft, suggest clause modifications, and participate in discussion threads. No simulated or fake lawyer profiles are used.
                </p>
              </div>

              <button
                id="btn-generate-lawyer-link"
                type="submit"
                disabled={generating}
                className="w-full py-2.5 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow transition-colors flex items-center justify-center space-x-1.5 disabled:opacity-50"
              >
                <Scale className="w-4 h-4" />
                <span>{generating ? 'Generating Secure Link...' : 'Generate Lawyer Review Link'}</span>
              </button>
            </form>
          ) : (
            <div className="space-y-4 animate-in fade-in">
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-md flex items-center space-x-2 text-emerald-800 text-xs font-medium">
                <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Lawyer invitation link generated successfully!</span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Authorized Advocate Review URL
                </label>
                <div className="flex space-x-2">
                  <input
                    type="text"
                    readOnly
                    value={invitationUrl}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md bg-slate-50 font-mono text-slate-600 select-all outline-none"
                  />
                  <button
                    id="btn-copy-lawyer-url"
                    onClick={handleCopyLink}
                    className="px-4 py-2 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm flex items-center space-x-1 shrink-0 transition-colors"
                  >
                    {copiedLink ? <Check className="w-4 h-4 text-emerald-300" /> : <Copy className="w-4 h-4" />}
                    <span>{copiedLink ? 'Copied!' : 'Copy'}</span>
                  </button>
                </div>
              </div>

              {/* 1-Click Communication Options */}
              <div className="space-y-2 pt-2 border-t border-slate-100">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Send to Advocate:
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <button
                    onClick={handleOpenGmail}
                    className="px-3 py-2 bg-white hover:bg-slate-50 border border-slate-200 rounded-md text-xs font-medium text-slate-700 flex items-center justify-center space-x-1.5 shadow-sm transition-colors"
                  >
                    <Send className="w-3.5 h-3.5 text-red-500" />
                    <span>Open in Gmail</span>
                  </button>
                  <button
                    onClick={handleOpenDefaultMail}
                    className="px-3 py-2 bg-white hover:bg-slate-50 border border-slate-200 rounded-md text-xs font-medium text-slate-700 flex items-center justify-center space-x-1.5 shadow-sm transition-colors"
                  >
                    <Mail className="w-3.5 h-3.5 text-blue-500" />
                    <span>Email App</span>
                  </button>
                  <button
                    onClick={handleCopyFullEmail}
                    className="px-3 py-2 bg-white hover:bg-slate-50 border border-slate-200 rounded-md text-xs font-medium text-slate-700 flex items-center justify-center space-x-1.5 shadow-sm transition-colors"
                  >
                    {copiedEmail ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
                    <span>{copiedEmail ? 'Copied!' : 'Copy Briefing'}</span>
                  </button>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  onClick={onClose}
                  className="px-4 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-md transition-colors"
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
