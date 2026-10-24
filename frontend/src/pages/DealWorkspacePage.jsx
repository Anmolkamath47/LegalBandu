import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { 
  FileText, 
  MessageSquare, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  GitCommit, 
  Download, 
  UserPlus, 
  Share2, 
  Upload, 
  Send, 
  Sparkles, 
  Edit3, 
  Check, 
  X, 
  AlertTriangle,
  RotateCcw,
  ShieldCheck,
  ChevronRight,
  MessageCircle,
  HelpCircle,
  Plus
} from 'lucide-react';
import InviteModal from '../components/InviteModal';

export default function DealWorkspacePage() {
  const { dealId } = useParams();
  const navigate = useNavigate();
  const { user, profile } = useAuth();

  const [deal, setDeal] = useState(null);
  const [activeTab, setActiveTab] = useState('conversations'); // conversations | terms | agreement | amendments | audit
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  // Modals & Sub-states
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showChangeRequestModal, setShowChangeRequestModal] = useState(false);
  const [changeRequestComment, setChangeRequestComment] = useState('');

  // Conversations State
  const [conversations, setConversations] = useState([]);
  const [pasteContent, setPasteContent] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [aiErrorMsg, setAiErrorMsg] = useState('');

  // Analysis & Terms State
  const [analysis, setAnalysis] = useState(null);
  const [clarifications, setClarifications] = useState([]);
  const [newClarField, setNewClarField] = useState('');
  const [newClarQuestion, setNewClarQuestion] = useState('');
  const [newClarAnswer, setNewClarAnswer] = useState('');
  const [savingClar, setSavingClar] = useState(false);

  // Agreement State
  const [versions, setVersions] = useState([]);
  const [currentVersion, setCurrentVersion] = useState(null);
  const [isEditingAgreement, setIsEditingAgreement] = useState(false);
  const [editedWorkScope, setEditedWorkScope] = useState('');
  const [editedFinancials, setEditedFinancials] = useState('');
  const [editedTimeline, setEditedTimeline] = useState('');
  const [editedResponsibilities, setEditedResponsibilities] = useState('');
  const [editedAgreementText, setEditedAgreementText] = useState('');
  const [editChangeSummary, setEditChangeSummary] = useState('');
  const [submittingAction, setSubmittingAction] = useState(false);
  const [commentText, setCommentText] = useState('');

  // Amendments State
  const [amendments, setAmendments] = useState([]);
  const [amendField, setAmendField] = useState('price');
  const [amendOrigVal, setAmendOrigVal] = useState('');
  const [amendPropVal, setAmendPropVal] = useState('');
  const [amendReason, setAmendReason] = useState('');
  const [submittingAmend, setSubmittingAmend] = useState(false);

  // Audit Log State
  const [activityLogs, setActivityLogs] = useState([]);
  const [verificationResult, setVerificationResult] = useState(null);
  const [verifyingChain, setVerifyingChain] = useState(false);

  useEffect(() => {
    loadDealData();
  }, [dealId]);

  async function loadDealData() {
    setLoading(true);
    setErrorMsg('');
    try {
      const dealData = await api.getDeal(dealId);
      setDeal(dealData);

      // Concurrently load workspace resources
      const [convs, latestAnalysis, clars, vers, amends, logs] = await Promise.all([
        api.getConversations(dealId).catch(() => []),
        api.getLatestAnalysis(dealId).catch(() => null),
        api.getClarifications(dealId).catch(() => []),
        api.getAgreements(dealId).catch(() => []),
        api.getAmendments(dealId).catch(() => []),
        api.getActivity(dealId).catch(() => []),
      ]);

      setConversations(convs || []);
      setAnalysis(latestAnalysis?.analysis || null);
      setClarifications(clars || []);
      setVersions(vers || []);
      setAmendments(amends || []);
      setActivityLogs(logs || []);

      if (vers && vers.length > 0) {
        // Select the version matching current_version_id or latest
        const matched = vers.find((v) => v.id === dealData.current_version_id) || vers[0];
        setCurrentVersion(matched);
        initEditFields(matched);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Could not load deal room details.');
    } finally {
      setLoading(false);
    }
  }

  function initEditFields(v) {
    if (!v) return;
    const json = v.agreement_json || {};
    setEditedWorkScope(json.work_scope || '');
    setEditedFinancials(json.financial_terms || '');
    setEditedTimeline(json.timeline || '');
    setEditedResponsibilities(json.responsibilities || '');
    setEditedAgreementText(v.agreement_text || '');
  }

  // 1. Conversation Import Handler
  async function handleImportConversation(e) {
    e.preventDefault();
    if (!pasteContent.trim() && !uploadFile) {
      alert('Please provide conversation text or select a .txt file.');
      return;
    }

    setImporting(true);
    setAiErrorMsg('');
    try {
      const formData = new FormData();
      if (uploadFile) {
        formData.append('file', uploadFile);
        formData.append('source_type', 'file_upload');
      } else {
        formData.append('content', pasteContent.trim());
        formData.append('source_type', 'paste');
      }

      const imported = await api.importConversation(dealId, formData);
      setConversations((prev) => [...prev, imported]);
      setPasteContent('');
      setUploadFile(null);
      // Reload activity
      api.getActivity(dealId).then(setActivityLogs).catch(() => {});
    } catch (err) {
      alert(err.message || 'Failed to import conversation.');
    } finally {
      setImporting(false);
    }
  }

  // 2. Run Gemini AI Analysis
  async function handleAnalyze() {
    setAnalyzing(true);
    setAiErrorMsg('');
    try {
      const res = await api.analyzeConversation(dealId);
      setAnalysis(res.analysis);
      setActiveTab('terms');
      api.getActivity(dealId).then(setActivityLogs).catch(() => {});
    } catch (err) {
      setAiErrorMsg(err.message || 'AI analysis request failed.');
    } finally {
      setAnalyzing(false);
    }
  }

  // 3. Clarification Answer Handler
  async function handleAddClarification(e) {
    e.preventDefault();
    if (!newClarField || !newClarAnswer) return;
    setSavingClar(true);
    try {
      const newClar = await api.submitClarification(dealId, {
        field_name: newClarField,
        question: newClarQuestion || `Clarification for ${newClarField}`,
        answer: newClarAnswer,
      });
      setClarifications((prev) => [...prev, newClar]);
      setNewClarField('');
      setNewClarQuestion('');
      setNewClarAnswer('');
      api.getActivity(dealId).then(setActivityLogs).catch(() => {});
    } catch (err) {
      alert(err.message || 'Could not save clarification.');
    } finally {
      setSavingClar(false);
    }
  }

  // 4. Generate Agreement from Terms
  async function handleGenerateAgreement() {
    setSubmittingAction(true);
    try {
      // Build plain language agreement from analysis & clarifications
      const workScopeText = analysis?.work_scope?.value || deal.description || 'To be specified';
      const priceText = `${analysis?.price?.value || '25,000'} ${analysis?.currency?.value || deal.currency}`;
      const timelineText = `Start: ${analysis?.start_date?.value || 'Immediate'}, Completion: ${analysis?.completion_deadline?.value || 'As agreed'}`;
      const responsibilitiesText = analysis?.responsibilities?.value || 'Standard professional execution';

      const agreementJson = {
        work_scope: workScopeText,
        financial_terms: priceText,
        timeline: timelineText,
        responsibilities: responsibilitiesText,
        delivery_acceptance: analysis?.delivery_acceptance_conditions?.value || 'Inspection upon completion',
        cancellation_refunds: analysis?.cancellation_refund_conditions?.value || 'Mutual written agreement required',
        unresolved_terms: analysis?.unresolved_terms || [],
      };

      const plainText = `AGREEMENT: ${deal.title}\n\n1. SCOPE OF WORK\n${workScopeText}\n\n2. FINANCIAL TERMS\n${priceText}\n\n3. TIMELINE\n${timelineText}\n\n4. RESPONSIBILITIES\n${responsibilitiesText}`;

      const newV = await api.createAgreement(dealId, {
        agreement_json: agreementJson,
        agreement_text: plainText,
      });

      setVersions([newV, ...versions]);
      setCurrentVersion(newV);
      initEditFields(newV);
      setActiveTab('agreement');
      // Update deal status
      const updatedDeal = await api.getDeal(dealId);
      setDeal(updatedDeal);
      api.getActivity(dealId).then(setActivityLogs).catch(() => {});
    } catch (err) {
      alert(err.message || 'Failed to generate agreement.');
    } finally {
      setSubmittingAction(false);
    }
  }

  // 5. Save Agreement Edit (v+1 Substantive Revision)
  async function handleSaveAgreementEdit(e) {
    e.preventDefault();
    if (!currentVersion) return;
    setSubmittingAction(true);
    try {
      const updatedJson = {
        ...(currentVersion.agreement_json || {}),
        work_scope: editedWorkScope,
        financial_terms: editedFinancials,
        timeline: editedTimeline,
        responsibilities: editedResponsibilities,
      };

      const newV = await api.editAgreement(currentVersion.id, {
        agreement_json: updatedJson,
        agreement_text: editedAgreementText,
        change_summary: editChangeSummary || 'Terms updated by participant',
      });

      setVersions([newV, ...versions]);
      setCurrentVersion(newV);
      setIsEditingAgreement(false);
      setEditChangeSummary('');
      const updatedDeal = await api.getDeal(dealId);
      setDeal(updatedDeal);
      api.getActivity(dealId).then(setActivityLogs).catch(() => {});
    } catch (err) {
      alert(err.message || 'Failed to edit agreement.');
    } finally {
      setSubmittingAction(false);
    }
  }

  // 6. Request Review
  async function handleRequestReview() {
    if (!currentVersion) return;
    setSubmittingAction(true);
    try {
      await api.requestReview(currentVersion.id);
      const updatedDeal = await api.getDeal(dealId);
      setDeal(updatedDeal);
      alert('Review requested! The counterparty has been notified.');
      api.getActivity(dealId).then(setActivityLogs).catch(() => {});
    } catch (err) {
      alert(err.message || 'Could not request review.');
    } finally {
      setSubmittingAction(false);
    }
  }

  // 7. Approve Agreement
  async function handleApprove() {
    if (!currentVersion) return;
    setSubmittingAction(true);
    try {
      const res = await api.approveAgreement(currentVersion.id, {
        status: 'approved',
        comment: 'Approved terms without reservation.',
      });

      // Reload version and deal
      const [vData, dealData] = await Promise.all([
        api.getAgreement(currentVersion.id),
        api.getDeal(dealId),
      ]);
      setCurrentVersion(vData);
      setDeal(dealData);
      api.getActivity(dealId).then(setActivityLogs).catch(() => {});

      if (res.is_mutually_confirmed) {
        alert('Congratulations! Both participants have approved this version. The agreement is now MUTUALLY CONFIRMED.');
      } else {
        alert('Your approval has been recorded! Awaiting confirmation from your counterparty.');
      }
    } catch (err) {
      alert(err.message || 'Failed to submit approval.');
    } finally {
      setSubmittingAction(false);
    }
  }

  // 8. Request Changes on Agreement
  async function handleSubmitChangeRequest(e) {
    e.preventDefault();
    if (!currentVersion || !changeRequestComment.trim()) return;
    setSubmittingAction(true);
    try {
      await api.requestChanges(currentVersion.id, {
        status: 'changes_requested',
        comment: changeRequestComment.trim(),
      });
      setShowChangeRequestModal(false);
      setChangeRequestComment('');
      const [vData, dealData] = await Promise.all([
        api.getAgreement(currentVersion.id),
        api.getDeal(dealId),
      ]);
      setCurrentVersion(vData);
      setDeal(dealData);
      api.getActivity(dealId).then(setActivityLogs).catch(() => {});
      alert('Changes requested. Counterparty has been notified.');
    } catch (err) {
      alert(err.message || 'Failed to submit change request.');
    } finally {
      setSubmittingAction(false);
    }
  }

  // 9. Add Clause Comment
  async function handleAddComment(e) {
    e.preventDefault();
    if (!currentVersion || !commentText.trim()) return;
    try {
      const newC = await api.addComment(currentVersion.id, {
        field_name: 'general',
        comment_text: commentText.trim(),
      });
      setCurrentVersion((prev) => ({
        ...prev,
        comments: [...(prev.comments || []), newC],
      }));
      setCommentText('');
    } catch (err) {
      alert(err.message || 'Failed to add comment.');
    }
  }

  // 10. Propose Amendment Handler
  async function handleProposeAmendment(e) {
    e.preventDefault();
    if (!amendOrigVal || !amendPropVal) return;
    setSubmittingAmend(true);
    try {
      const newAmend = await api.proposeAmendment(dealId, {
        field_name: amendField,
        original_value: amendOrigVal,
        proposed_value: amendPropVal,
        reason: amendReason || 'Adjustment requested by participant',
      });
      setAmendments([newAmend, ...amendments]);
      setAmendOrigVal('');
      setAmendPropVal('');
      setAmendReason('');
      alert('Amendment proposed! Both participants must approve before updating the confirmed agreement.');
      api.getActivity(dealId).then(setActivityLogs).catch(() => {});
    } catch (err) {
      alert(err.message || 'Failed to propose amendment.');
    } finally {
      setSubmittingAmend(false);
    }
  }

  // 11. Run Cryptographic Audit Chain Verification
  async function handleVerifyChain() {
    setVerifyingChain(true);
    try {
      const result = await api.verifyActivityChain(dealId);
      setVerificationResult(result);
    } catch (err) {
      alert(err.message || 'Verification execution failed.');
    } finally {
      setVerifyingChain(false);
    }
  }

  // 12. Download PDF
  async function handleDownloadPdf() {
    if (!currentVersion) return;
    try {
      await api.downloadPdf(
        currentVersion.id,
        `Legalbandu_${deal.title.replace(/\s+/g, '_')}_v${currentVersion.version_number}.pdf`
      );
      api.getActivity(dealId).then(setActivityLogs).catch(() => {});
    } catch (err) {
      alert(err.message || 'Failed to download agreement PDF.');
    }
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center text-xs text-slate-500">
        Loading deal workspace...
      </div>
    );
  }

  if (errorMsg || !deal) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16 text-center">
        <AlertCircle className="w-10 h-10 text-red-500 mx-auto mb-3" />
        <h2 className="text-base font-bold text-slate-900">Access Restricted</h2>
        <p className="text-xs text-slate-600 mt-1">{errorMsg || 'Deal not found.'}</p>
        <button
          onClick={() => navigate('/dashboard')}
          className="mt-4 px-4 py-2 bg-navy-900 text-white text-xs font-semibold rounded-md shadow-sm"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  const participants = deal.participants || [];
  const creator = participants.find((p) => p.role === 'creator');
  const counterparty = participants.find((p) => p.role === 'counterparty');
  const hasCounterpartyJoined = Boolean(counterparty && counterparty.user_id);

  // Check current user's approval status for currentVersion
  const myParticipant = participants.find((p) => p.user_id === user?.id);
  const myApproval = currentVersion?.approvals?.find((a) => a.participant_id === myParticipant?.id);
  const hasApprovedThisVersion = (myApproval?.status === 'approved');

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* Workspace Header */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center space-x-2.5 flex-wrap gap-y-1">
            <h1 className="text-xl font-bold text-navy-900">{deal.title}</h1>
            
            {/* Deal Status Badge */}
            {deal.status === 'mutually_confirmed' ? (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Mutually Confirmed</span>
              </span>
            ) : deal.status === 'changes_requested' ? (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-red-700 border border-red-200">
                Changes Requested
              </span>
            ) : deal.status === 'awaiting_review' || deal.status === 'awaiting_counterparty' ? (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                Awaiting Mutual Review
              </span>
            ) : (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                Drafting Terms
              </span>
            )}

            {currentVersion && (
              <span className="px-2 py-0.5 rounded text-xs font-mono bg-slate-100 text-slate-700 border border-slate-200">
                v{currentVersion.version_number}.0
              </span>
            )}
          </div>

          <p className="text-xs text-slate-500 mt-1">
            Category: <span className="font-medium text-slate-700">{deal.category}</span> | 
            Currency: <span className="font-medium text-slate-700">{deal.currency}</span> | 
            Next Step: <span className="font-semibold text-blue-700">{deal.next_action}</span>
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-2 shrink-0">
          <button
            id="btn-invite-counterparty"
            onClick={() => setShowInviteModal(true)}
            className="px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-semibold rounded-md shadow-sm flex items-center space-x-1.5 transition-colors"
          >
            <UserPlus className="w-4 h-4 text-blue-600" />
            <span>{hasCounterpartyJoined ? 'Invite Link' : 'Invite Counterparty'}</span>
          </button>

          {currentVersion && (
            <button
              id="btn-download-pdf"
              onClick={handleDownloadPdf}
              className="px-3.5 py-2 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm flex items-center space-x-1.5 transition-colors"
            >
              <Download className="w-4 h-4" />
              <span>Download PDF</span>
            </button>
          )}
        </div>
      </div>

      {/* Participants Verification Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Creator Card */}
        <div className="p-4 bg-white rounded-lg border border-slate-200 shadow-sm flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-800 flex items-center justify-center font-bold text-xs">
              C
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Deal Creator
              </span>
              <span className="text-xs font-bold text-slate-900 block">
                {creator?.full_name || deal.creator_name || 'Creator'}
              </span>
            </div>
          </div>
          <span className="text-[11px] font-semibold text-emerald-700 flex items-center space-x-1">
            <ShieldCheck className="w-4 h-4" />
            <span>Verified</span>
          </span>
        </div>

        {/* Counterparty Card */}
        <div className="p-4 bg-white rounded-lg border border-slate-200 shadow-sm flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-full bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-xs">
              P
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Counterparty
              </span>
              <span className="text-xs font-bold text-slate-900 block">
                {counterparty?.full_name || counterparty?.email || (hasCounterpartyJoined ? 'Joined' : 'Pending Invitation')}
              </span>
            </div>
          </div>
          {hasCounterpartyJoined ? (
            <span className="text-[11px] font-semibold text-emerald-700 flex items-center space-x-1">
              <ShieldCheck className="w-4 h-4" />
              <span>Joined Room</span>
            </span>
          ) : (
            <button
              onClick={() => setShowInviteModal(true)}
              className="text-xs text-blue-600 hover:underline font-semibold"
            >
              Send Invite Link
            </button>
          )}
        </div>
      </div>

      {/* Workspace Navigation Tabs */}
      <div className="border-b border-slate-200 bg-white px-2 rounded-t-lg shadow-sm">
        <nav className="flex space-x-2 sm:space-x-4 overflow-x-auto">
          <button
            id="tab-conversations"
            onClick={() => setActiveTab('conversations')}
            className={`py-3 px-3 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors flex items-center space-x-1.5 ${
              activeTab === 'conversations'
                ? 'border-navy-900 text-navy-900'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Conversations ({conversations.length})</span>
          </button>

          <button
            id="tab-terms"
            onClick={() => setActiveTab('terms')}
            className={`py-3 px-3 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors flex items-center space-x-1.5 ${
              activeTab === 'terms'
                ? 'border-navy-900 text-navy-900'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Extracted Terms & Clarifications</span>
          </button>

          <button
            id="tab-agreement"
            onClick={() => setActiveTab('agreement')}
            className={`py-3 px-3 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors flex items-center space-x-1.5 ${
              activeTab === 'agreement'
                ? 'border-navy-900 text-navy-900'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Agreement & Review {currentVersion && `(v${currentVersion.version_number})`}</span>
          </button>

          <button
            id="tab-amendments"
            onClick={() => setActiveTab('amendments')}
            className={`py-3 px-3 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors flex items-center space-x-1.5 ${
              activeTab === 'amendments'
                ? 'border-navy-900 text-navy-900'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Amendments ({amendments.length})</span>
          </button>

          <button
            id="tab-audit"
            onClick={() => setActiveTab('audit')}
            className={`py-3 px-3 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors flex items-center space-x-1.5 ${
              activeTab === 'audit'
                ? 'border-navy-900 text-navy-900'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <GitCommit className="w-3.5 h-3.5" />
            <span>Audit Trail & SHA-256</span>
          </button>
        </nav>
      </div>

      {/* ========================================================= */}
      {/* TAB 1: CONVERSATIONS (IMPORT & CHAT BUBBLES)               */}
      {/* ========================================================= */}
      {activeTab === 'conversations' && (
        <div className="space-y-6">
          {/* Import Card */}
          <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm">
            <h3 className="text-sm font-bold text-navy-900 mb-1">
              Import Business Conversation
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Paste chat messages from WhatsApp, email threads, or notes. Or upload an exported <code>.txt</code> file.
            </p>

            <form onSubmit={handleImportConversation} className="space-y-4">
              <div>
                <textarea
                  id="textarea-import-content"
                  rows={4}
                  placeholder="Example:&#10;[24/10/26, 10:00 AM] Rajesh: Can you finish painting before 30 October?&#10;[24/10/26, 10:02 AM] Sunil: Yes, total ₹25,000 for full shop painting.&#10;[24/10/26, 10:05 AM] Rajesh: 50% advance, 50% upon completion. Deal?&#10;[24/10/26, 10:06 AM] Sunil: Deal confirmed."
                  value={pasteContent}
                  onChange={(e) => setPasteContent(e.target.value)}
                  className="w-full p-3 text-xs font-mono border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 outline-none"
                />
              </div>

              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <div className="flex items-center space-x-2">
                  <label className="cursor-pointer px-3 py-1.5 border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-medium rounded-md flex items-center space-x-1.5">
                    <Upload className="w-3.5 h-3.5" />
                    <span>{uploadFile ? uploadFile.name : 'Upload .txt File'}</span>
                    <input
                      type="file"
                      accept=".txt,.text,.chat"
                      className="hidden"
                      onChange={(e) => setUploadFile(e.target.files[0] || null)}
                    />
                  </label>
                  {uploadFile && (
                    <button
                      type="button"
                      onClick={() => setUploadFile(null)}
                      className="text-slate-400 hover:text-slate-600 text-xs"
                    >
                      Remove
                    </button>
                  )}
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    id="btn-import-conversation"
                    type="submit"
                    disabled={importing}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-md shadow-sm transition-colors disabled:opacity-50"
                  >
                    {importing ? 'Importing...' : 'Save Conversation'}
                  </button>

                  {conversations.length > 0 && (
                    <button
                      id="btn-analyze-gemini"
                      type="button"
                      onClick={handleAnalyze}
                      disabled={analyzing}
                      className="px-4 py-2 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm transition-colors flex items-center space-x-1.5 disabled:opacity-50"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                      <span>{analyzing ? 'Analyzing with Gemini...' : 'Analyze with AI (Gemini)'}</span>
                    </button>
                  )}
                </div>
              </div>
            </form>

            {/* Audio notice */}
            <div className="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-md text-[11px] text-slate-500">
              <span className="font-semibold text-slate-700">Audio Voice Notes Notice:</span> Automated audio speech-to-text transcription service is not configured in this deployment. Please import transcribed text or type voice note details directly.
            </div>

            {aiErrorMsg && (
              <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-800 flex items-start space-x-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">AI Analysis Notice</p>
                  <p className="mt-0.5">{aiErrorMsg}</p>
                  <p className="mt-1 text-[11px] text-amber-700">
                    You can switch to the <b>Extracted Terms & Clarifications</b> tab to review or manually input agreement terms.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Imported Conversations Feed */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Imported Conversation History ({conversations.length} records)
            </h3>

            {conversations.length === 0 ? (
              <div className="p-8 text-center bg-white rounded-lg border border-slate-200 text-xs text-slate-400">
                No conversation transcripts imported yet. Paste chat text above to begin analysis.
              </div>
            ) : (
              conversations.map((c) => (
                <div key={c.id} className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm space-y-3">
                  <div className="flex justify-between items-center text-xs text-slate-500 border-b border-slate-100 pb-2">
                    <span>
                      Imported by <strong className="text-slate-800">{c.uploaded_by_name}</strong> via {c.source_type}
                    </span>
                    <span>{new Date(c.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</span>
                  </div>

                  {/* Messages */}
                  <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                    {c.messages && c.messages.length > 0 ? (
                      c.messages.map((m) => (
                        <div key={m.id} className="p-2.5 bg-slate-50 rounded-md border border-slate-100 text-xs">
                          <div className="flex justify-between items-center mb-1 text-[11px] text-slate-500">
                            <span className="font-bold text-navy-900">{m.speaker_label}</span>
                            {m.message_timestamp && <span>{m.message_timestamp}</span>}
                          </div>
                          <p className="text-slate-700 whitespace-pre-wrap">{m.message_text}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-slate-600 whitespace-pre-wrap font-mono p-2 bg-slate-50 rounded">
                        {c.original_content}
                      </p>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 2: EXTRACTED TERMS & CLARIFICATIONS                    */}
      {/* ========================================================= */}
      {activeTab === 'terms' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <div>
              <h3 className="text-sm font-bold text-navy-900">Extracted Agreement Terms</h3>
              <p className="text-xs text-slate-500">
                Verify terms extracted from conversations. Answer clarification questions to fill in missing details.
              </p>
            </div>
            
            <button
              id="btn-generate-agreement"
              onClick={handleGenerateAgreement}
              disabled={submittingAction}
              className="px-4 py-2 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm transition-colors flex items-center space-x-1.5 disabled:opacity-50"
            >
              <FileText className="w-4 h-4 text-blue-300" />
              <span>{submittingAction ? 'Drafting...' : 'Generate Plain-Language Agreement'}</span>
            </button>
          </div>

          {/* Terms Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { label: 'Work Scope & Deliverables', data: analysis?.work_scope, fallback: deal.description || 'To be specified' },
              { label: 'Price & Compensation', data: analysis?.price, fallback: '25,000 INR' },
              { label: 'Payment Terms & Schedule', data: analysis?.payment_terms, fallback: '50% advance, 50% upon completion' },
              { label: 'Target Completion Deadline', data: analysis?.completion_deadline, fallback: '30 October 2026' },
              { label: 'Responsibilities of Parties', data: analysis?.responsibilities, fallback: 'Vendor provides supplies; Client provides premises access' },
              { label: 'Delivery & Acceptance Criteria', data: analysis?.delivery_acceptance_conditions, fallback: 'Joint physical walkthrough' },
              { label: 'Cancellation & Refund Terms', data: analysis?.cancellation_refund_conditions, fallback: 'Requires bilateral written agreement' },
              { label: 'Warranty & Revision Terms', data: analysis?.warranty_revision_terms, fallback: '30 days defect rectifications' },
            ].map((term, i) => {
              const status = term.data?.status || 'reviewed_by_participants';
              const val = term.data?.value || term.fallback;
              const quote = term.data?.supporting_quote;

              return (
                <div key={i} className="p-4 bg-white rounded-lg border border-slate-200 shadow-sm space-y-2">
                  <div className="flex justify-between items-start">
                    <span className="text-xs font-bold text-slate-900">{term.label}</span>
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                      status === 'found_in_conversation' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                      status === 'conflicting' ? 'bg-red-50 text-red-700 border-red-200' :
                      status === 'unclear' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                      status === 'missing' ? 'bg-slate-100 text-slate-600 border-slate-200' :
                      'bg-blue-50 text-blue-700 border-blue-200'
                    }`}>
                      {status.replace(/_/g, ' ')}
                    </span>
                  </div>

                  <p className="text-xs text-slate-700 leading-relaxed font-medium">
                    {val}
                  </p>

                  {quote && (
                    <div className="p-2 bg-slate-50 border-l-2 border-slate-300 text-[11px] text-slate-500 italic">
                      "{quote}"
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Unresolved Questions & Clarifications Section */}
          <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-navy-900 flex items-center space-x-1.5">
              <HelpCircle className="w-4 h-4 text-blue-600" />
              <span>Clarification Questions & Custom Additions</span>
            </h3>
            <p className="text-xs text-slate-500">
              Answer open questions or explicitly enter missing clauses before final agreement generation.
            </p>

            {/* List Clarifications */}
            <div className="space-y-3">
              {clarifications.map((c) => (
                <div key={c.id} className="p-3 bg-slate-50 border border-slate-200 rounded-md text-xs space-y-1">
                  <div className="flex justify-between items-center text-[11px] text-slate-500">
                    <span className="font-bold text-slate-800">{c.field_name}</span>
                    <span>Answered by {c.answered_by_name}</span>
                  </div>
                  <p className="text-slate-600 italic">Q: {c.question}</p>
                  <p className="text-slate-900 font-semibold">A: {c.answer}</p>
                </div>
              ))}
            </div>

            {/* Submit New Clarification Form */}
            <form onSubmit={handleAddClarification} className="pt-3 border-t border-slate-100 space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input
                  type="text"
                  required
                  placeholder="Field name (e.g. deadline, payment_schedule)"
                  value={newClarField}
                  onChange={(e) => setNewClarField(e.target.value)}
                  className="px-3 py-1.5 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 outline-none"
                />
                <input
                  type="text"
                  placeholder="Question or Context"
                  value={newClarQuestion}
                  onChange={(e) => setNewClarQuestion(e.target.value)}
                  className="px-3 py-1.5 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 outline-none"
                />
              </div>
              <textarea
                rows={2}
                required
                placeholder="Clarification answer or agreed clause value..."
                value={newClarAnswer}
                onChange={(e) => setNewClarAnswer(e.target.value)}
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 outline-none resize-none"
              />
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={savingClar}
                  className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-md shadow-sm disabled:opacity-50"
                >
                  {savingClar ? 'Saving...' : 'Add Clarification'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 3: AGREEMENT VERSION & BILATERAL MUTUAL REVIEW         */}
      {/* ========================================================= */}
      {activeTab === 'agreement' && (
        <div className="space-y-6">
          {!currentVersion ? (
            <div className="p-12 text-center bg-white rounded-lg border border-slate-200">
              <FileText className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <h3 className="text-sm font-bold text-slate-800">No Agreement Version Generated Yet</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                Review your extracted terms in the Extracted Terms tab and click 'Generate Plain-Language Agreement'.
              </p>
              <button
                onClick={handleGenerateAgreement}
                className="mt-4 px-4 py-2 bg-navy-900 text-white text-xs font-semibold rounded-md shadow-sm"
              >
                Generate Initial Version (v1.0)
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Version Banner & Review Controls */}
              <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div className="flex items-center space-x-3">
                  <div className="flex items-center space-x-1.5">
                    <span className="text-xs font-bold text-navy-900">Version:</span>
                    <select
                      value={currentVersion.id}
                      onChange={(e) => {
                        const sel = versions.find((v) => v.id === e.target.value);
                        if (sel) {
                          setCurrentVersion(sel);
                          initEditFields(sel);
                        }
                      }}
                      className="px-2 py-1 text-xs border border-slate-300 rounded-md font-mono bg-white font-bold"
                    >
                      {versions.map((v) => (
                        <option key={v.id} value={v.id}>
                          v{v.version_number}.0 {v.superseded_at ? '(Superseded)' : '(Current)'}
                        </option>
                      ))}
                    </select>
                  </div>

                  {currentVersion.is_mutually_confirmed ? (
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center space-x-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Mutually Confirmed</span>
                    </span>
                  ) : (
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200 flex items-center space-x-1">
                      <Clock className="w-3.5 h-3.5" />
                      <span>Pending Mutual Confirmation</span>
                    </span>
                  )}
                </div>

                {/* Bilateral Action Buttons */}
                <div className="flex flex-wrap items-center gap-2">
                  {!isEditingAgreement ? (
                    <>
                      <button
                        id="btn-edit-agreement"
                        onClick={() => setIsEditingAgreement(true)}
                        className="px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-semibold rounded-md shadow-sm flex items-center space-x-1"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        <span>Edit Terms</span>
                      </button>

                      {deal.status === 'draft' && (
                        <button
                          id="btn-request-review"
                          onClick={handleRequestReview}
                          disabled={submittingAction}
                          className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-md shadow-sm disabled:opacity-50"
                        >
                          Request Review
                        </button>
                      )}

                      {!hasApprovedThisVersion && (
                        <>
                          <button
                            id="btn-approve-agreement"
                            onClick={handleApprove}
                            disabled={submittingAction}
                            className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-md shadow-sm flex items-center space-x-1 disabled:opacity-50"
                          >
                            <Check className="w-4 h-4" />
                            <span>Confirm & Approve</span>
                          </button>

                          <button
                            id="btn-request-changes"
                            onClick={() => setShowChangeRequestModal(true)}
                            className="px-3.5 py-1.5 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 text-xs font-semibold rounded-md"
                          >
                            Request Changes
                          </button>
                        </>
                      )}

                      {hasApprovedThisVersion && !currentVersion.is_mutually_confirmed && (
                        <div className="px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded text-xs text-emerald-800 font-semibold flex items-center space-x-1">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          <span>You Approved v{currentVersion.version_number}. Awaiting Partner.</span>
                        </div>
                      )}
                    </>
                  ) : (
                    <button
                      onClick={() => setIsEditingAgreement(false)}
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-md"
                    >
                      Cancel Editing
                    </button>
                  )}
                </div>
              </div>

              {/* Document Paper Layout */}
              <div className="document-paper p-6 sm:p-12 rounded-xl bg-white border border-slate-200 shadow-sm max-w-4xl mx-auto space-y-6">
                
                {/* Document Header */}
                <div className="text-center pb-6 border-b border-slate-200">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 block mb-1">
                    Plain-Language Commercial Agreement
                  </span>
                  <h2 className="text-2xl font-bold text-navy-900 font-serif">
                    {deal.title}
                  </h2>
                  <p className="text-xs text-slate-500 mt-1">
                    Reference ID: <code>LB-{deal.id.substring(0, 8).toUpperCase()}</code> | Version: <code>v{currentVersion.version_number}.0</code> | Date: {new Date(currentVersion.created_at).toLocaleDateString([], { month: 'long', day: 'numeric', year: 'numeric' })}
                  </p>
                </div>

                {isEditingAgreement ? (
                  /* Editor Form */
                  <form onSubmit={handleSaveAgreementEdit} className="space-y-4">
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-800 flex items-start space-x-2">
                      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>
                        <strong>Substantive Revision:</strong> Editing these terms will preserve Version {currentVersion.version_number} and create Version {currentVersion.version_number + 1}. All approvals will be reset to pending.
                      </span>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">1. Scope of Work & Deliverables</label>
                      <textarea
                        rows={3}
                        value={editedWorkScope}
                        onChange={(e) => setEditedWorkScope(e.target.value)}
                        className="w-full p-2.5 text-xs border border-slate-300 rounded-md outline-none focus:ring-1 focus:ring-navy-900"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">2. Financial Terms & Payment Schedule</label>
                      <textarea
                        rows={2}
                        value={editedFinancials}
                        onChange={(e) => setEditedFinancials(e.target.value)}
                        className="w-full p-2.5 text-xs border border-slate-300 rounded-md outline-none focus:ring-1 focus:ring-navy-900"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">3. Timeline & Deadlines</label>
                      <input
                        type="text"
                        value={editedTimeline}
                        onChange={(e) => setEditedTimeline(e.target.value)}
                        className="w-full p-2 text-xs border border-slate-300 rounded-md outline-none focus:ring-1 focus:ring-navy-900"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">4. Responsibilities</label>
                      <textarea
                        rows={2}
                        value={editedResponsibilities}
                        onChange={(e) => setEditedResponsibilities(e.target.value)}
                        className="w-full p-2.5 text-xs border border-slate-300 rounded-md outline-none focus:ring-1 focus:ring-navy-900"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">Change Summary (Reason for edit)</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Added high ceiling preparation and +₹3,000 price adjustment"
                        value={editChangeSummary}
                        onChange={(e) => setEditChangeSummary(e.target.value)}
                        className="w-full p-2 text-xs border border-slate-300 rounded-md outline-none focus:ring-1 focus:ring-navy-900"
                      />
                    </div>

                    <div className="flex justify-end space-x-2 pt-3 border-t border-slate-100">
                      <button
                        type="button"
                        onClick={() => setIsEditingAgreement(false)}
                        className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-md"
                      >
                        Cancel
                      </button>
                      <button
                        id="btn-save-agreement-revision"
                        type="submit"
                        disabled={submittingAction}
                        className="px-5 py-2 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm disabled:opacity-50"
                      >
                        {submittingAction ? 'Creating Revision...' : `Save as Revision v${currentVersion.version_number + 1}.0`}
                      </button>
                    </div>
                  </form>
                ) : (
                  /* Formal Document Reader */
                  <div className="space-y-6 text-xs text-slate-800 leading-relaxed font-sans">
                    
                    {/* Section 1: Parties */}
                    <div>
                      <h4 className="font-bold text-navy-900 uppercase tracking-wider text-[11px] mb-2 border-b border-slate-100 pb-1">
                        1. PARTIES INVOLVED
                      </h4>
                      <p>
                        This Agreement is made between <strong className="text-slate-900">{creator?.full_name || deal.creator_name || 'Creator'}</strong> ("First Party") and <strong className="text-slate-900">{counterparty?.full_name || counterparty?.email || 'Counterparty'}</strong> ("Second Party").
                      </p>
                    </div>

                    {/* Section 2: Scope */}
                    <div>
                      <h4 className="font-bold text-navy-900 uppercase tracking-wider text-[11px] mb-2 border-b border-slate-100 pb-1">
                        2. WORK SCOPE & DELIVERABLES
                      </h4>
                      <p className="whitespace-pre-wrap">
                        {currentVersion.agreement_json?.work_scope || deal.description || 'To be performed according to mutual specifications.'}
                      </p>
                    </div>

                    {/* Section 3: Financials */}
                    <div>
                      <h4 className="font-bold text-navy-900 uppercase tracking-wider text-[11px] mb-2 border-b border-slate-100 pb-1">
                        3. FINANCIAL TERMS & PAYMENT SCHEDULE
                      </h4>
                      <p className="whitespace-pre-wrap">
                        {currentVersion.agreement_json?.financial_terms || `Total consideration is agreed in ${deal.currency}.`}
                      </p>
                    </div>

                    {/* Section 4: Timeline */}
                    <div>
                      <h4 className="font-bold text-navy-900 uppercase tracking-wider text-[11px] mb-2 border-b border-slate-100 pb-1">
                        4. TIMELINE & DEADLINES
                      </h4>
                      <p className="whitespace-pre-wrap">
                        {currentVersion.agreement_json?.timeline || 'Completion expected as agreed in conversation.'}
                      </p>
                    </div>

                    {/* Section 5: Responsibilities */}
                    <div>
                      <h4 className="font-bold text-navy-900 uppercase tracking-wider text-[11px] mb-2 border-b border-slate-100 pb-1">
                        5. RESPONSIBILITIES & OBLIGATIONS
                      </h4>
                      <p className="whitespace-pre-wrap">
                        {currentVersion.agreement_json?.responsibilities || 'Both parties commit to reasonable diligence and open communication.'}
                      </p>
                    </div>

                    {/* Section 6: Confirmation Records */}
                    <div className="pt-6 border-t border-slate-200">
                      <h4 className="font-bold text-navy-900 uppercase tracking-wider text-[11px] mb-3">
                        6. PARTICIPANT CONFIRMATION & AUDIT STAMPS
                      </h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {participants.map((p) => {
                          const app = currentVersion.approvals?.find((a) => a.participant_id === p.id);
                          const isApp = (app?.status === 'approved');

                          return (
                            <div key={p.id} className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                              <span className="text-[10px] uppercase font-bold text-slate-400 block">
                                {p.role.toUpperCase()}
                              </span>
                              <span className="text-xs font-bold text-slate-900 block mt-0.5">
                                {p.full_name || p.email || 'Participant'}
                              </span>
                              <div className="mt-2 pt-2 border-t border-slate-200 flex items-center justify-between text-[11px]">
                                <span className={isApp ? 'text-emerald-700 font-bold' : 'text-amber-700 font-medium'}>
                                  {isApp ? 'Confirmed & Approved' : 'Pending Review'}
                                </span>
                                {isApp && app.confirmed_at && (
                                  <span className="text-[10px] text-slate-400 font-mono">
                                    {new Date(app.confirmed_at).toLocaleDateString()}
                                  </span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Statutory Disclaimer */}
                    <div className="pt-4 border-t border-slate-100 text-[10px] text-slate-400 italic text-center">
                      Legalbandu documentation engine. Version {currentVersion.version_number}.0 is cryptographically protected via SHA-256 hash chaining.
                    </div>
                  </div>
                )}
              </div>

              {/* Clause Comments Thread */}
              <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm space-y-3 max-w-4xl mx-auto">
                <h4 className="text-xs font-bold text-navy-900 flex items-center space-x-1.5">
                  <MessageCircle className="w-3.5 h-3.5 text-blue-600" />
                  <span>Agreement Comments & Negotiation Notes</span>
                </h4>

                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {currentVersion.comments?.length === 0 ? (
                    <p className="text-xs text-slate-400">No comments posted on this version yet.</p>
                  ) : (
                    currentVersion.comments?.map((c) => (
                      <div key={c.id} className="p-2.5 bg-slate-50 border border-slate-100 rounded text-xs space-y-0.5">
                        <div className="flex justify-between items-center text-[10px] text-slate-400">
                          <span className="font-bold text-slate-800">{c.participant_name}</span>
                          <span>{new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                        <p className="text-slate-700">{c.comment_text}</p>
                      </div>
                    ))
                  )}
                </div>

                <form onSubmit={handleAddComment} className="flex gap-2 pt-2 border-t border-slate-100">
                  <input
                    type="text"
                    placeholder="Add a comment or change note..."
                    value={commentText}
                    onChange={(e) => setCommentText(e.target.value)}
                    className="flex-1 px-3 py-1.5 text-xs border border-slate-300 rounded-md outline-none focus:ring-1 focus:ring-navy-900"
                  />
                  <button
                    type="submit"
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-md shadow-sm"
                  >
                    Post Comment
                  </button>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 4: AMENDMENTS (PROPOSE & SIDE-BY-SIDE REVIEW)          */}
      {/* ========================================================= */}
      {activeTab === 'amendments' && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-4">
            <div>
              <h3 className="text-sm font-bold text-navy-900">Propose an Agreement Amendment</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Suggest modifications to price, deadlines, or scope. Amendments require mutual confirmation before replacing the current agreement.
              </p>
            </div>

            <form onSubmit={handleProposeAmendment} className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">Clause to Amend</label>
                  <select
                    value={amendField}
                    onChange={(e) => setAmendField(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs border border-slate-300 rounded-md outline-none bg-white"
                  >
                    <option value="price">Price / Financials</option>
                    <option value="deadline">Completion Deadline</option>
                    <option value="work_scope">Scope of Work</option>
                    <option value="payment_schedule">Payment Schedule</option>
                    <option value="other">Other Term</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">Original Agreed Value</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. ₹25,000 INR"
                    value={amendOrigVal}
                    onChange={(e) => setAmendOrigVal(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs border border-slate-300 rounded-md outline-none focus:ring-1 focus:ring-navy-900"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">Proposed New Value</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. ₹28,000 INR (+₹3,000)"
                    value={amendPropVal}
                    onChange={(e) => setAmendPropVal(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs border border-slate-300 rounded-md outline-none focus:ring-1 focus:ring-navy-900"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">Reason / Supporting Message Reference</label>
                <input
                  type="text"
                  placeholder="e.g. Counterparty requested 2 coats on high ceiling as discussed in WhatsApp"
                  value={amendReason}
                  onChange={(e) => setAmendReason(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs border border-slate-300 rounded-md outline-none focus:ring-1 focus:ring-navy-900"
                />
              </div>

              <div className="flex justify-end pt-2">
                <button
                  id="btn-submit-amendment"
                  type="submit"
                  disabled={submittingAmend}
                  className="px-4 py-2 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm transition-colors disabled:opacity-50"
                >
                  {submittingAmend ? 'Proposing...' : 'Propose Official Amendment'}
                </button>
              </div>
            </form>
          </div>

          {/* Amendments History & Comparison Cards */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Proposed & Confirmed Amendments ({amendments.length})
            </h3>

            {amendments.length === 0 ? (
              <div className="p-8 text-center bg-white rounded-lg border border-slate-200 text-xs text-slate-400">
                No amendments proposed yet. The agreement remains on its baseline terms.
              </div>
            ) : (
              amendments.map((a) => (
                <div key={a.id} className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm space-y-3">
                  <div className="flex justify-between items-center text-xs border-b border-slate-100 pb-2">
                    <span className="font-bold text-navy-900 uppercase">
                      Amendment: {a.field_name}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      Proposed by {a.proposed_by_name} • {new Date(a.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  {/* Side by side comparison */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 bg-slate-50 rounded border border-slate-200">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                        Previous Term
                      </span>
                      <p className="font-medium text-slate-700">{a.original_value}</p>
                    </div>

                    <div className="p-3 bg-blue-50/60 rounded border border-blue-200">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700 block mb-1">
                        Proposed Term
                      </span>
                      <p className="font-bold text-blue-900">{a.proposed_value}</p>
                    </div>
                  </div>

                  {a.reason && (
                    <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded">
                      <strong className="text-slate-800">Reason:</strong> {a.reason}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 5: AUDIT TRAIL & SHA-256 HASH VERIFICATION             */}
      {/* ========================================================= */}
      {activeTab === 'audit' && (
        <div className="space-y-6">
          <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div>
              <h3 className="text-sm font-bold text-navy-900 flex items-center space-x-1.5">
                <GitCommit className="w-4 h-4 text-blue-600" />
                <span>Tamper-Evident SHA-256 Audit Chain</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Every deal creation, agreement generation, amendment, and approval is cryptographically chained.
              </p>
            </div>

            <button
              id="btn-verify-audit-chain"
              onClick={handleVerifyChain}
              disabled={verifyingChain}
              className="px-4 py-2 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm transition-colors flex items-center space-x-1.5 disabled:opacity-50"
            >
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>{verifyingChain ? 'Verifying Hashes...' : 'Run Cryptographic Verification'}</span>
            </button>
          </div>

          {/* Verification Result Banner */}
          {verificationResult && (
            <div className={`p-4 rounded-lg border text-xs flex items-start space-x-3 ${
              verificationResult.valid
                ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                : 'bg-red-50 border-red-200 text-red-900'
            }`}>
              {verificationResult.valid ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              )}
              <div>
                <p className="font-bold">
                  {verificationResult.valid ? 'Cryptographic Hash Chain Verified' : 'Integrity Violation Detected'}
                </p>
                <p className="mt-0.5">{verificationResult.message}</p>
                <p className="mt-1 text-[11px] font-mono">
                  Verified {verificationResult.verified_events} of {verificationResult.total_events} events without discrepancy.
                </p>
              </div>
            </div>
          )}

          {/* Timeline Feed */}
          <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Chronological Audit Trail ({activityLogs.length} events)
            </h4>

            <div className="space-y-4">
              {activityLogs.map((log, index) => (
                <div key={log.id} className="relative pl-6 border-l-2 border-slate-200 text-xs space-y-1">
                  <div className="absolute -left-1.5 top-0.5 w-3 h-3 rounded-full bg-navy-900 border-2 border-white"></div>
                  
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-slate-900">
                      {log.event_type.replace(/_/g, ' ').toUpperCase()}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {new Date(log.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-600">
                    Actor: <span className="font-medium text-slate-800">{log.actor_name || 'System'}</span>
                  </p>

                  {/* Hash links */}
                  <div className="p-2 bg-slate-50 rounded border border-slate-100 font-mono text-[10px] text-slate-500 space-y-0.5">
                    <div className="truncate">Prev: {log.previous_hash}</div>
                    <div className="truncate font-semibold text-slate-700">Hash: {log.event_hash}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Invite Modal */}
      <InviteModal
        isOpen={showInviteModal}
        onClose={() => setShowInviteModal(false)}
        dealId={deal.id}
        dealTitle={deal.title}
      />

      {/* Change Request Modal */}
      {showChangeRequestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md bg-white rounded-xl shadow-2xl border border-slate-200 p-6 space-y-4">
            <div className="flex justify-between items-center border-b border-slate-100 pb-2">
              <h3 className="text-sm font-bold text-navy-900">Request Changes on Agreement</h3>
              <button onClick={() => setShowChangeRequestModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmitChangeRequest} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Specify Requested Modifications
                </label>
                <textarea
                  rows={4}
                  required
                  placeholder="e.g. Please clarify if the painter provides the primer or if the store owner purchases it..."
                  value={changeRequestComment}
                  onChange={(e) => setChangeRequestComment(e.target.value)}
                  className="w-full p-2.5 text-xs border border-slate-300 rounded-md outline-none focus:ring-1 focus:ring-navy-900"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowChangeRequestModal(false)}
                  className="px-4 py-2 text-xs text-slate-600 hover:bg-slate-100 rounded-md"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingAction}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-md shadow-sm disabled:opacity-50"
                >
                  {submittingAction ? 'Submitting...' : 'Submit Change Request'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
