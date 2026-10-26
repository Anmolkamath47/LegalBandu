import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import {
  Scale,
  CheckCircle2,
  AlertCircle,
  Clock,
  XCircle,
  MessageSquare,
  Plus,
  Send,
  UserCheck,
  ShieldCheck,
  ArrowRight,
  FileText,
  UserPlus,
  RefreshCw,
  Check,
  X,
  FileCheck2,
} from 'lucide-react';

export default function LawyerReviewPanel({
  dealId,
  isOwner,
  isLawyer,
  onOpenInviteModal,
  onDraftUpdated,
}) {
  const [review, setReview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  // New suggestion form state (for lawyer)
  const [showNewSuggestionForm, setShowNewSuggestionForm] = useState(false);
  const [clauseRef, setClauseRef] = useState('Clause 5: Consideration and Payment');
  const [origText, setOrigText] = useState('');
  const [suggText, setSuggText] = useState('');
  const [explanation, setExplanation] = useState('');
  const [submittingSugg, setSubmittingSugg] = useState(false);

  // Suggestion action state (for owner)
  const [actioningSuggId, setActioningSuggId] = useState(null);

  // Discussion reply state: { [suggId]: 'message text' }
  const [replyInputs, setReplyInputs] = useState({});
  const [submittingReplyId, setSubmittingReplyId] = useState(null);

  // Status update modal / input (for lawyer)
  const [updatingReviewStatus, setUpdatingReviewStatus] = useState(false);
  const [reviewNotes, setReviewNotes] = useState('');

  const loadReview = useCallback(async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const data = await api.getLawyerReview(dealId);
      setReview(data);
    } catch (err) {
      setErrorMsg(err.message || 'Could not load lawyer review status.');
    } finally {
      setLoading(false);
    }
  }, [dealId]);

  useEffect(() => {
    loadReview();
  }, [loadReview]);

  async function handleCreateSuggestion(e) {
    e.preventDefault();
    if (!clauseRef.trim() || !suggText.trim() || !explanation.trim()) {
      alert('Please fill in the clause reference, suggested text, and legal explanation.');
      return;
    }

    setSubmittingSugg(true);
    setErrorMsg('');
    try {
      await api.createLawyerSuggestion(dealId, {
        clause_reference: clauseRef.trim(),
        original_text: origText.trim(),
        suggested_text: suggText.trim(),
        explanation: explanation.trim(),
      });
      setShowNewSuggestionForm(false);
      setOrigText('');
      setSuggText('');
      setExplanation('');
      loadReview();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to submit lawyer suggestion.');
    } finally {
      setSubmittingSugg(false);
    }
  }

  async function handleDecideSuggestion(suggId, decision) {
    let rejectionReason = '';
    if (decision === 'rejected') {
      const promptRes = prompt('Please enter the reason for rejecting this suggestion:');
      if (promptRes === null) return;
      rejectionReason = promptRes;
    }

    setActioningSuggId(suggId);
    setErrorMsg('');
    try {
      await api.decideLawyerSuggestion(dealId, suggId, {
        decision,
        rejection_reason: rejectionReason || undefined,
        apply_to_draft: decision === 'accepted',
      });
      if (decision === 'accepted' && onDraftUpdated) {
        onDraftUpdated();
      }
      loadReview();
    } catch (err) {
      setErrorMsg(err.message || `Failed to ${decision} suggestion.`);
    } finally {
      setActioningSuggId(null);
    }
  }

  async function handleSendReply(suggId) {
    const text = (replyInputs[suggId] || '').trim();
    if (!text) return;

    setSubmittingReplyId(suggId);
    setErrorMsg('');
    try {
      await api.postLawyerDiscussion(dealId, suggId, { message: text });
      setReplyInputs((prev) => ({ ...prev, [suggId]: '' }));
      loadReview();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to post reply.');
    } finally {
      setSubmittingReplyId(null);
    }
  }

  async function handleUpdateOverallStatus(newStatus) {
    setUpdatingReviewStatus(true);
    setErrorMsg('');
    try {
      await api.updateLawyerReviewStatus(dealId, {
        status: newStatus,
        overall_notes: reviewNotes.trim() || undefined,
      });
      loadReview();
      setReviewNotes('');
    } catch (err) {
      setErrorMsg(err.message || 'Failed to update review status.');
    } finally {
      setUpdatingReviewStatus(false);
    }
  }

  if (loading) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-slate-200">
        <RefreshCw className="w-6 h-6 text-indigo-600 animate-spin mx-auto mb-2" />
        <p className="text-xs text-slate-600 font-medium">Loading lawyer review folder...</p>
      </div>
    );
  }

  if (!review) return null;

  const isNotInvited = review.status === 'not_invited';
  const isInviteSent = review.status === 'invite_sent';
  const isInReview = review.status === 'in_review';
  const isChangesRecommended = review.status === 'changes_recommended';
  const isApproved = review.status === 'approved';
  const isDeclined = review.status === 'declined';

  return (
    <div className="space-y-6">
      {/* Lawyer Review Status Banner */}
      <div
        className={`p-5 rounded-xl border shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4 ${
          isApproved
            ? 'bg-gradient-to-r from-emerald-50 to-teal-50 border-emerald-300'
            : isChangesRecommended
            ? 'bg-gradient-to-r from-amber-50 to-orange-50 border-amber-300'
            : isDeclined
            ? 'bg-gradient-to-r from-red-50 to-rose-50 border-red-300'
            : isInviteSent
            ? 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200'
            : 'bg-gradient-to-r from-slate-50 to-indigo-50/40 border-slate-200'
        }`}
      >
        <div className="flex items-start space-x-3">
          <div
            className={`p-2.5 rounded-lg shrink-0 mt-0.5 ${
              isApproved
                ? 'bg-emerald-600 text-white'
                : isChangesRecommended
                ? 'bg-amber-600 text-white'
                : isDeclined
                ? 'bg-red-600 text-white'
                : 'bg-indigo-600 text-white'
            }`}
          >
            <Scale className="w-5 h-5" />
          </div>

          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-navy-900">
                {isApproved
                  ? 'Advocate Review Approved'
                  : isChangesRecommended
                  ? 'Advocate Suggested Modifications'
                  : isDeclined
                  ? 'Lawyer Review Invitation Declined'
                  : isInviteSent
                  ? 'Lawyer Review Invitation Sent'
                  : isInReview
                  ? 'Formal Legal Review in Progress'
                  : 'Independent Lawyer Review'}
              </h3>
              <span
                className={`text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full ${
                  isApproved
                    ? 'bg-emerald-100 text-emerald-800'
                    : isChangesRecommended
                    ? 'bg-amber-100 text-amber-800'
                    : isDeclined
                    ? 'bg-red-100 text-red-800'
                    : isInviteSent
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-slate-200 text-slate-700'
                }`}
              >
                {review.status.replace('_', ' ')}
              </span>
            </div>

            <p className="text-xs text-slate-600 mt-1">
              {isApproved ? (
                <span>
                  The designated advocate has reviewed and approved this agreement draft as legally enforceable under Indian law.
                </span>
              ) : isChangesRecommended ? (
                <span>
                  The reviewing lawyer has proposed specific modifications and statutory rationale below.
                </span>
              ) : isDeclined ? (
                <span>
                  The invited advocate declined to take up this review. Reason: <em>{review.decline_reason || 'Not specified'}</em>
                </span>
              ) : isInviteSent ? (
                <span>
                  Invitation link active for{' '}
                  <strong className="text-navy-900">{review.invitation_email || 'the invited lawyer'}</strong>. Awaiting acceptance.
                </span>
              ) : isInReview ? (
                <span>
                  Advocate <strong className="text-navy-900">{review.lawyer_name || 'Counsel'}</strong> has authenticated and is currently reviewing the clauses.
                </span>
              ) : (
                <span>
                  Invite an independent advocate or law firm to review this draft, suggest clause modifications, and certify legal enforceability.
                </span>
              )}
            </p>

            {review.overall_notes && (
              <p className="text-xs text-slate-700 mt-2 font-medium bg-white/70 p-2 rounded border border-slate-200">
                <strong>Advocate Notes:</strong> {review.overall_notes}
              </p>
            )}
          </div>
        </div>

        {/* Action Button: Invite Lawyer or Update Review */}
        <div className="shrink-0 flex items-center space-x-2">
          {isNotInvited || isDeclined ? (
            <button
              id="btn-invite-lawyer-panel"
              type="button"
              onClick={onOpenInviteModal}
              className="px-3.5 py-2 bg-navy-900 hover:bg-navy-800 text-white text-xs font-bold rounded-md shadow-sm transition-colors flex items-center space-x-1.5"
            >
              <UserPlus className="w-4 h-4 text-blue-300" />
              <span>Invite Lawyer for Review</span>
            </button>
          ) : isInviteSent ? (
            <button
              type="button"
              onClick={onOpenInviteModal}
              className="px-3.5 py-1.5 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-semibold rounded-md shadow-sm transition-colors flex items-center space-x-1"
            >
              <Clock className="w-3.5 h-3.5 text-blue-600" />
              <span>Resend / Copy Invite</span>
            </button>
          ) : isLawyer ? (
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => handleUpdateOverallStatus('approved')}
                disabled={updatingReviewStatus}
                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-md shadow-sm transition-colors flex items-center space-x-1 disabled:opacity-50"
              >
                <Check className="w-3.5 h-3.5" />
                <span>Approve Draft</span>
              </button>
              <button
                type="button"
                onClick={() => setShowNewSuggestionForm(!showNewSuggestionForm)}
                className="px-3 py-1.5 bg-navy-900 hover:bg-navy-800 text-white text-xs font-bold rounded-md shadow-sm transition-colors flex items-center space-x-1"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Suggest Modification</span>
              </button>
            </div>
          ) : null}
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Reviewer Mode Banner for Lawyer */}
      {isLawyer && (
        <div className="p-3.5 bg-blue-900 text-white rounded-lg flex items-center justify-between shadow-sm">
          <div className="flex items-center space-x-2 text-xs">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
            <div>
              <span className="font-bold">Logged in as Authorized Legal Counsel:</span>{' '}
              <span className="text-blue-200">
                You can review clauses, propose replacements, provide statutory explanations, and converse with the deal owner.
              </span>
            </div>
          </div>
          <button
            onClick={() => setShowNewSuggestionForm(true)}
            className="px-3 py-1 bg-white text-navy-900 font-bold rounded text-xs hover:bg-blue-50 transition-colors shrink-0"
          >
            + Add Suggestion
          </button>
        </div>
      )}

      {/* Form: Add Lawyer Suggestion (For Lawyer) */}
      {showNewSuggestionForm && (
        <div className="p-5 bg-white rounded-xl border border-blue-300 shadow-md space-y-4 animate-in fade-in">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
            <h4 className="text-xs font-bold text-navy-900 flex items-center space-x-2">
              <Scale className="w-4 h-4 text-blue-600" />
              <span>Propose Agreement Clause Modification</span>
            </h4>
            <button
              onClick={() => setShowNewSuggestionForm(false)}
              className="text-slate-400 hover:text-slate-600"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <form onSubmit={handleCreateSuggestion} className="space-y-3">
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                Clause Reference / Title
              </label>
              <input
                type="text"
                required
                value={clauseRef}
                onChange={(e) => setClauseRef(e.target.value)}
                placeholder="e.g. Clause 5: Consideration, or Clause 8: Breach and Remedies"
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 outline-none"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                Existing Text (Optional snippet from draft being modified)
              </label>
              <textarea
                rows={2}
                value={origText}
                onChange={(e) => setOrigText(e.target.value)}
                placeholder="Paste the current phrasing you wish to change..."
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 outline-none font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                Suggested Modified Text (Proposed Wording)
              </label>
              <textarea
                rows={3}
                required
                value={suggText}
                onChange={(e) => setSuggText(e.target.value)}
                placeholder="Enter your proposed legally sound clause wording..."
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 outline-none font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                Legal Explanation & Statutory Rationale
              </label>
              <textarea
                rows={2}
                required
                value={explanation}
                onChange={(e) => setExplanation(e.target.value)}
                placeholder="Explain why this change is necessary (e.g. compliance with Section 74 Indian Contract Act, stamp duty provisions, etc.)..."
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 outline-none"
              />
            </div>

            <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setShowNewSuggestionForm(false)}
                className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded text-xs font-semibold hover:bg-slate-200"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submittingSugg}
                className="px-4 py-1.5 bg-navy-900 text-white rounded text-xs font-bold hover:bg-navy-800 disabled:opacity-50 shadow-sm"
              >
                {submittingSugg ? 'Submitting...' : 'Submit Suggestion to Owner'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Suggestions List */}
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h4 className="text-xs font-bold text-navy-900 uppercase tracking-wider flex items-center space-x-1.5">
            <FileText className="w-3.5 h-3.5 text-slate-500" />
            <span>Advocate Clause Suggestions ({review.suggestions.length})</span>
          </h4>
        </div>

        {review.suggestions.length === 0 ? (
          <div className="p-8 text-center bg-white rounded-xl border border-slate-200">
            <FileCheck2 className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <h5 className="text-xs font-bold text-slate-700">No Clause Suggestions Recorded</h5>
            <p className="text-[11px] text-slate-500 mt-1 max-w-sm mx-auto">
              {isLawyer
                ? 'Click "+ Add Suggestion" to propose modifications to specific agreement clauses.'
                : 'When your invited lawyer reviews the agreement draft, their proposed clause modifications and rationale will appear here.'}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {review.suggestions.map((sugg) => {
              const isPending = sugg.status === 'pending';
              const isAccepted = sugg.status === 'accepted';
              const isRejected = sugg.status === 'rejected';

              return (
                <div
                  key={sugg.id}
                  className={`p-5 rounded-xl border bg-white shadow-sm space-y-4 transition-all ${
                    isAccepted
                      ? 'border-emerald-200'
                      : isRejected
                      ? 'border-red-200 bg-red-50/20'
                      : 'border-slate-200'
                  }`}
                >
                  {/* Suggestion Header */}
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-100 pb-3">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-xs text-navy-900">
                        {sugg.clause_reference}
                      </span>
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                          isAccepted
                            ? 'bg-emerald-100 text-emerald-800'
                            : isRejected
                            ? 'bg-red-100 text-red-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {sugg.status}
                      </span>
                    </div>

                    <div className="text-[11px] text-slate-400">
                      Suggested by <strong className="text-slate-700">{sugg.lawyer_name || 'Counsel'}</strong> on{' '}
                      {new Date(sugg.created_at).toLocaleDateString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                  </div>

                  {/* Original vs Suggested Text Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    {sugg.original_text && (
                      <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                          Current / Original Text:
                        </span>
                        <p className="font-mono text-slate-600 whitespace-pre-wrap leading-relaxed text-[11px]">
                          {sugg.original_text}
                        </p>
                      </div>
                    )}

                    <div
                      className={`p-3 rounded-lg border space-y-1 ${
                        isAccepted
                          ? 'bg-emerald-50/50 border-emerald-200'
                          : 'bg-blue-50/50 border-blue-200'
                      }`}
                    >
                      <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700 block">
                        Advocate Suggested Modification:
                      </span>
                      <p className="font-mono text-navy-950 font-medium whitespace-pre-wrap leading-relaxed text-[11px]">
                        {sugg.suggested_text}
                      </p>
                    </div>
                  </div>

                  {/* Legal Explanation */}
                  <div className="p-3 bg-amber-50/60 border border-amber-200 rounded-lg space-y-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800 block">
                      Advocate's Legal Explanation & Rationale:
                    </span>
                    <p className="text-xs text-amber-950 leading-relaxed font-normal">
                      {sugg.explanation}
                    </p>
                  </div>

                  {sugg.rejection_reason && (
                    <div className="p-2.5 bg-red-50 border border-red-200 rounded text-xs text-red-800">
                      <strong>Rejection Rationale:</strong> {sugg.rejection_reason}
                    </div>
                  )}

                  {/* Owner Action Buttons */}
                  {isOwner && isPending && (
                    <div className="flex items-center space-x-2 pt-2 border-t border-slate-100">
                      <button
                        type="button"
                        onClick={() => handleDecideSuggestion(sugg.id, 'accepted')}
                        disabled={actioningSuggId === sugg.id}
                        className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-md shadow-sm transition-colors flex items-center space-x-1 disabled:opacity-50"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Accept & Apply to Draft</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => handleDecideSuggestion(sugg.id, 'rejected')}
                        disabled={actioningSuggId === sugg.id}
                        className="px-3.5 py-1.5 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 text-xs font-semibold rounded-md transition-colors flex items-center space-x-1 disabled:opacity-50"
                      >
                        <X className="w-3.5 h-3.5" />
                        <span>Reject Suggestion</span>
                      </button>
                    </div>
                  )}

                  {/* Discussion Thread */}
                  <div className="space-y-2 pt-3 border-t border-slate-100">
                    <span className="text-[11px] font-bold text-slate-600 flex items-center space-x-1">
                      <MessageSquare className="w-3 h-3 text-slate-400" />
                      <span>Discussion Thread with Lawyer:</span>
                    </span>

                    {sugg.discussion_notes && sugg.discussion_notes.length > 0 && (
                      <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                        {sugg.discussion_notes.map((msg, mIdx) => (
                          <div
                            key={mIdx}
                            className={`p-2.5 rounded-lg text-xs space-y-0.5 ${
                              msg.role === 'lawyer'
                                ? 'bg-indigo-50/80 border border-indigo-100 ml-4'
                                : 'bg-slate-50 border border-slate-200 mr-4'
                            }`}
                          >
                            <div className="flex justify-between items-center text-[10px] text-slate-400">
                              <span className="font-bold text-slate-700">
                                {msg.author_name} ({msg.role === 'lawyer' ? 'Advocate' : 'Owner'})
                              </span>
                              <span>
                                {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                              </span>
                            </div>
                            <p className="text-slate-800 font-normal">{msg.message}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Reply Input */}
                    <div className="flex space-x-2 pt-1">
                      <input
                        type="text"
                        placeholder="Discuss this suggestion with the lawyer / owner..."
                        value={replyInputs[sugg.id] || ''}
                        onChange={(e) => setReplyInputs({ ...replyInputs, [sugg.id]: e.target.value })}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            handleSendReply(sugg.id);
                          }
                        }}
                        className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 outline-none"
                      />
                      <button
                        type="button"
                        onClick={() => handleSendReply(sugg.id)}
                        disabled={submittingReplyId === sugg.id || !(replyInputs[sugg.id] || '').trim()}
                        className="px-3 py-1.5 bg-navy-900 hover:bg-navy-800 text-white rounded-md text-xs font-semibold flex items-center space-x-1 shrink-0 disabled:opacity-50"
                      >
                        <Send className="w-3 h-3" />
                        <span>Reply</span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
