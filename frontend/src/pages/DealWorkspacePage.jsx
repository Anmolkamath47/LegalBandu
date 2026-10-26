import React, { useState, useEffect, useCallback, useRef } from 'react';
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
  Upload, 
  Sparkles, 
  Edit3, 
  Check, 
  X, 
  AlertTriangle,
  ShieldCheck,
  MessageCircle,
  HelpCircle,
  Mic,
  Scale,
  ShieldAlert,
  FileCheck2,
  PenTool,
  Image as ImageIcon,
  ChevronRight,
} from 'lucide-react';
import InviteModal from '../components/InviteModal';
import InviteLawyerModal from '../components/InviteLawyerModal';
import AIDetectorAlertModal from '../components/AIDetectorAlertModal';
import AudioPlayerWidget from '../components/AudioPlayerWidget';
import AudioCallRecorder from '../components/AudioCallRecorder';
import BondUploadWidget from '../components/BondUploadWidget';
import LegalCompliancePanel from '../components/LegalCompliancePanel';
import AgreementAssistancePanel from '../components/AgreementAssistancePanel';
import LawyerReviewPanel from '../components/LawyerReviewPanel';

export default function DealWorkspacePage() {
  const { dealId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [deal, setDeal] = useState(null);
  const [activeTab, setActiveTab] = useState('conversations'); // conversations | terms | agreement | amendments | audit | bonds
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  // Modals & Sub-states
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showInviteLawyerModal, setShowInviteLawyerModal] = useState(false);
  const [agreementSubView, setAgreementSubView] = useState('draft'); // 'draft' | 'assistance' | 'lawyer_review'
  const [showChangeRequestModal, setShowChangeRequestModal] = useState(false);
  const [changeRequestComment, setChangeRequestComment] = useState('');

  // Conversation Input Sub-mode: 'chat' | 'call_recording' | 'bond_detector'
  const [convInputMode, setConvInputMode] = useState('chat');

  // Bonds & AI Detector State
  const [bonds, setBonds] = useState([]);
  const [alertBond, setAlertBond] = useState(null);
  const [showAlertModal, setShowAlertModal] = useState(false);
  const [scanningBond, setScanningBond] = useState(false);
  const [applyingBond, setApplyingBond] = useState(false);

  // Conversations State
  const [conversations, setConversations] = useState([]);
  const [pasteContent, setPasteContent] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadType, setUploadType] = useState('text'); // 'text' | 'image'
  const [imagePreview, setImagePreview] = useState(null);
  const [importing, setImporting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [aiErrorMsg, setAiErrorMsg] = useState('');

  // Live E-Signature State
  const signatureCanvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasDrawn, setHasDrawn] = useState(false);
  const [signingAgreement, setSigningAgreement] = useState(false);

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

  const loadDealData = useCallback(async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const dealData = await api.getDeal(dealId);
      setDeal(dealData);

      // Concurrently load workspace resources
      const [convs, latestAnalysis, clars, vers, amends, logs, bondList] = await Promise.all([
        api.getConversations(dealId).catch(() => []),
        api.getLatestAnalysis(dealId).catch(() => null),
        api.getClarifications(dealId).catch(() => []),
        api.getAgreements(dealId).catch(() => []),
        api.getAmendments(dealId).catch(() => []),
        api.getActivity(dealId).catch(() => []),
        api.getBonds(dealId).catch(() => []),
      ]);

      setConversations(convs || []);
      setAnalysis(latestAnalysis?.analysis || null);
      setClarifications(clars || []);
      setVersions(vers || []);
      setAmendments(amends || []);
      setActivityLogs(logs || []);
      setBonds(bondList || []);

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
  }, [dealId]);

  useEffect(() => {
    loadDealData();
  }, [loadDealData]);

  function initEditFields(v) {
    if (!v) return;
    const json = v.agreement_json || {};
    setEditedWorkScope(json.work_scope || '');
    setEditedFinancials(json.financial_terms || '');
    setEditedTimeline(json.timeline || '');
    setEditedResponsibilities(json.responsibilities || '');
    setEditedAgreementText(v.agreement_text || '');
  }

  // 1. Conversation Import Handler (Text / Chat / Image)
  async function handleImportConversation(e) {
    e.preventDefault();
    if (!pasteContent.trim() && !uploadFile) {
      alert('Please provide conversation text, paste chat, or select an image / .txt file.');
      return;
    }

    setImporting(true);
    setAiErrorMsg('');
    try {
      const formData = new FormData();
      if (uploadFile) {
        formData.append('file', uploadFile);
        formData.append(
          'source_type',
          uploadType === 'image' || uploadFile.type?.startsWith('image/')
            ? 'image_upload'
            : 'file_upload'
        );
      } else {
        formData.append('content', pasteContent.trim());
        formData.append('source_type', 'paste');
      }

      const imported = await api.importConversation(dealId, formData);
      setConversations((prev) => [...prev, imported]);
      setPasteContent('');
      setUploadFile(null);
      setImagePreview(null);
      // Reload activity
      api.getActivity(dealId).then(setActivityLogs).catch(() => {});
    } catch (err) {
      alert(err.message || 'Failed to import conversation.');
    } finally {
      setImporting(false);
    }
  }

  // Live E-Signature Canvas Helpers
  function getCanvasPos(canvas, e) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  }

  function startDrawing(e) {
    const canvas = signatureCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const pos = getCanvasPos(canvas, e);
    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    setIsDrawing(true);
    setHasDrawn(true);
  }

  function draw(e) {
    if (!isDrawing) return;
    const canvas = signatureCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const pos = getCanvasPos(canvas, e);
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
  }

  function stopDrawing() {
    setIsDrawing(false);
  }

  function startDrawingTouch(e) {
    if (e.touches && e.touches.length === 1) {
      e.preventDefault();
      const touch = e.touches[0];
      const canvas = signatureCanvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const pos = getCanvasPos(canvas, touch);
      ctx.beginPath();
      ctx.moveTo(pos.x, pos.y);
      ctx.strokeStyle = '#0f172a';
      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      setIsDrawing(true);
      setHasDrawn(true);
    }
  }

  function drawTouch(e) {
    if (!isDrawing || !e.touches || e.touches.length !== 1) return;
    e.preventDefault();
    const touch = e.touches[0];
    const canvas = signatureCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const pos = getCanvasPos(canvas, touch);
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
  }

  function clearSignature() {
    const canvas = signatureCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setHasDrawn(false);
  }

  async function handleSignAgreement() {
    if (!currentVersion) return;
    const canvas = signatureCanvasRef.current;
    if (!canvas || !hasDrawn) {
      alert('Please draw your handwritten signature on the pad before stamping.');
      return;
    }

    const dataUrl = canvas.toDataURL('image/png');
    setSigningAgreement(true);
    try {
      const updatedV = await api.signAgreement(currentVersion.id, {
        signature_image: dataUrl,
        signer_name: user?.full_name || 'Participant',
      });
      setCurrentVersion(updatedV);
      setVersions((prev) => prev.map((v) => (v.id === updatedV.id ? updatedV : v)));
      // Refresh deal & activity
      api.getDeal(dealId).then(setDeal).catch(() => {});
      api.getActivity(dealId).then(setActivityLogs).catch(() => {});
    } catch (err) {
      alert(err.message || 'Failed to stamp live e-signature.');
    } finally {
      setSigningAgreement(false);
    }
  }

  // 1b. Call Recording & Audio Analysis Handler
  async function handleImportAudio({ file, transcript }) {
    setImporting(true);
    setAiErrorMsg('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('source_type', 'call_recording');
      if (transcript) {
        formData.append('content', transcript);
      }

      const imported = await api.importConversation(dealId, formData);
      setConversations((prev) => [...prev, imported]);

      // Automatically refresh AI analysis, deal status, and agreement version with extracted key points
      const [freshAnalysis, freshAgreements, freshDeal] = await Promise.all([
        api.getLatestAnalysis(dealId).catch(() => null),
        api.getAgreements(dealId).catch(() => []),
        api.getDeal(dealId).catch(() => null),
      ]);

      if (freshAnalysis?.analysis) setAnalysis(freshAnalysis.analysis);
      if (freshAgreements && freshAgreements.length > 0) {
        setVersions(freshAgreements);
        setCurrentVersion(freshAgreements[0]);
        initEditFields(freshAgreements[0]);
        // Immediately show the mutual agreement with the AI-extracted key points!
        setActiveTab('agreement');
      }
      if (freshDeal) setDeal(freshDeal);

      api.getActivity(dealId).then(setActivityLogs).catch(() => {});
    } catch (err) {
      if (err.status === 404 || err.message === 'Not Found' || err.message?.includes('Unsupported file format')) {
        alert('Backend Deployment Pending: The Render backend (https://legalbandu.onrender.com) is currently updating to the latest build with audio analysis. If this persists, please click "Manual Deploy" -> "Deploy latest commit" in your Render dashboard (https://dashboard.render.com).');
      } else {
        alert(err.message || 'Failed to analyze call recording.');
      }
    } finally {
      setImporting(false);
    }
  }

  // 1c. Bond Upload & AI Detector Handler
  async function handleUploadBond(formData) {
    setScanningBond(true);
    try {
      const uploadedBond = await api.uploadBond(dealId, formData);
      setBonds((prev) => [uploadedBond, ...prev]);

      // IMMEDIATELY TRIGGER ALERT IF DETECTED AS AI
      if (uploadedBond.is_ai_generated || uploadedBond.ai_alert_triggered) {
        setAlertBond(uploadedBond);
        setShowAlertModal(true);
      } else {
        // Authentic bond: auto-stored directly in legal agreement version!
        const [freshAgreements, freshDeal] = await Promise.all([
          api.getAgreements(dealId).catch(() => []),
          api.getDeal(dealId).catch(() => null),
        ]);

        if (freshAgreements && freshAgreements.length > 0) {
          setVersions(freshAgreements);
          setCurrentVersion(freshAgreements[0]);
          initEditFields(freshAgreements[0]);
          setActiveTab('agreement');
        }
        if (freshDeal) setDeal(freshDeal);
      }

      api.getActivity(dealId).then(setActivityLogs).catch(() => {});
    } catch (err) {
      if (err.status === 404 || err.message === 'Not Found') {
        alert('Backend Deployment Pending: The Render backend (https://legalbandu.onrender.com) is currently updating to the latest build with bond scanning. If this persists, please click "Manual Deploy" -> "Deploy latest commit" in your Render dashboard (https://dashboard.render.com).');
      } else {
        alert(err.message || 'Failed to scan and upload bond document.');
      }
    } finally {
      setScanningBond(false);
    }
  }

  // 1d. Convert Bond into Agreement Version
  async function handleApplyBondToAgreement(bondId) {
    setApplyingBond(true);
    try {
      const res = await api.applyBondToAgreement(dealId, bondId);
      setShowAlertModal(false);

      // Refresh agreements and deal info
      const [vers, freshDeal] = await Promise.all([
        api.getAgreements(dealId).catch(() => []),
        api.getDeal(dealId).catch(() => null),
      ]);

      if (vers && vers.length > 0) {
        setVersions(vers);
        const latest = vers[0];
        setCurrentVersion(latest);
        initEditFields(latest);
      }
      if (freshDeal) setDeal(freshDeal);

      setActiveTab('agreement');
      api.getActivity(dealId).then(setActivityLogs).catch(() => {});
      alert(res.message || 'Bond terms successfully integrated into agreement!');
    } catch (err) {
      alert(err.message || 'Failed to apply bond terms to agreement.');
    } finally {
      setApplyingBond(false);
    }
  }

  // 1e. Delete Bond
  async function handleDeleteBond(bondId) {
    if (!confirm('Are you sure you want to remove this bond document from the deal room?')) return;
    try {
      await api.deleteBond(dealId, bondId);
      setBonds((prev) => prev.filter((b) => b.id !== bondId));
      api.getActivity(dealId).then(setActivityLogs).catch(() => {});
    } catch (err) {
      alert(err.message || 'Failed to delete bond.');
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
      // Send the extracted terms to the backend.
      // The backend will auto-generate a complete, court-admissible
      // Indian law agreement (14 clauses, arbitration, governing law, etc.)
      const agreementJson = {
        work_scope:       analysis?.work_scope?.value              || deal.description || '',
        financial_terms:  analysis?.price?.value
          ? `${analysis.price.value} ${analysis?.currency?.value || deal.currency}. Payment: ${analysis?.payment_terms?.value || 'as mutually agreed.'}`
          : `As mutually agreed in ${deal.currency}.`,
        timeline:         (analysis?.start_date?.value || analysis?.completion_deadline?.value)
          ? `Start: ${analysis?.start_date?.value || 'As agreed'}. Completion: ${analysis?.completion_deadline?.value || 'As agreed.'}`
          : 'Timeline to be mutually agreed by the Parties in writing.',
        responsibilities: analysis?.responsibilities?.value        || '',
        delivery_acceptance:  analysis?.delivery_acceptance_conditions?.value  || '',
        cancellation_refunds: analysis?.cancellation_refund_conditions?.value  || '',
        warranty_revisions:   analysis?.warranty_revision_terms?.value         || '',
        unresolved_terms:     analysis?.unresolved_terms                        || [],
      };

      // Pass an empty agreement_text — the backend generates the full legal document
      const newV = await api.createAgreement(dealId, {
        agreement_json: agreementJson,
        agreement_text: '',
      });

      setVersions([newV, ...versions]);
      setCurrentVersion(newV);
      initEditFields(newV);
      setActiveTab('agreement');
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

  // Handle draft update from Assistance or Lawyer Suggestions
  const handleDraftUpdated = useCallback(async (newV) => {
    if (newV) {
      setVersions((prev) => [newV, ...prev.filter((v) => v.id !== newV.id)]);
      setCurrentVersion(newV);
      initEditFields(newV);
    }
    try {
      const [updatedDeal, vers] = await Promise.all([
        api.getDeal(dealId).catch(() => null),
        api.getAgreements(dealId).catch(() => []),
      ]);
      if (updatedDeal) setDeal(updatedDeal);
      if (vers && vers.length > 0) {
        setVersions(vers);
        if (!newV) {
          setCurrentVersion(vers[0]);
          initEditFields(vers[0]);
        }
      }
    } catch (e) {
      console.warn('Could not refresh deal after draft update:', e);
    }
  }, [dealId]);

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
  const lawyerParticipant = participants.find((p) => p.role === 'lawyer');
  const hasCounterpartyJoined = Boolean(counterparty && counterparty.user_id);
  const hasLawyerJoined = Boolean(lawyerParticipant && lawyerParticipant.user_id);

  // Check current user role and approval status for currentVersion
  const myParticipant = participants.find((p) => p.user_id === user?.id);
  const isLawyer = myParticipant?.role === 'lawyer';
  const isCreator = myParticipant?.role === 'creator' || deal.creator_id === user?.id;
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
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <button
            id="btn-invite-counterparty"
            onClick={() => setShowInviteModal(true)}
            className="px-3 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-semibold rounded-md shadow-sm flex items-center space-x-1.5 transition-colors"
          >
            <UserPlus className="w-4 h-4 text-blue-600" />
            <span>{hasCounterpartyJoined ? 'Invite Link' : 'Invite Counterparty'}</span>
          </button>

          <button
            id="btn-invite-lawyer"
            onClick={() => setShowInviteLawyerModal(true)}
            className="px-3 py-2 bg-purple-50 hover:bg-purple-100 text-purple-900 border border-purple-200 text-xs font-semibold rounded-md shadow-sm flex items-center space-x-1.5 transition-colors"
          >
            <Scale className="w-4 h-4 text-purple-600" />
            <span>{hasLawyerJoined ? 'Lawyer Review' : 'Invite Lawyer'}</span>
          </button>

          {!currentVersion ? (
            <button
              id="btn-header-generate-agreement"
              onClick={handleGenerateAgreement}
              disabled={submittingAction}
              className="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-md shadow-sm flex items-center space-x-1.5 transition-colors disabled:opacity-50"
            >
              <FileText className="w-4 h-4 text-blue-100" />
              <span>{submittingAction ? 'Generating...' : 'Generate Legal Agreement'}</span>
            </button>
          ) : (
            <button
              id="btn-header-view-agreement"
              onClick={() => {
                setActiveTab('agreement');
                setAgreementSubView('draft');
              }}
              className={`px-3 py-2 text-xs rounded-md shadow-sm flex items-center space-x-1.5 transition-colors border ${
                activeTab === 'agreement' && agreementSubView === 'draft'
                  ? 'bg-blue-50 text-blue-800 border-blue-300 font-bold'
                  : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-300 font-semibold'
              }`}
            >
              <FileText className="w-4 h-4 text-blue-600" />
              <span>Agreement v{currentVersion.version_number}.0</span>
            </button>
          )}

          {currentVersion && (
            <button
              id="btn-download-pdf"
              onClick={handleDownloadPdf}
              className="px-3 py-2 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm flex items-center space-x-1.5 transition-colors"
            >
              <Download className="w-4 h-4" />
              <span>Download PDF</span>
            </button>
          )}
        </div>
      </div>

      {/* Participants Verification Cards (Creator, Counterparty, Legal Counsel) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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
              <span className="text-xs font-bold text-slate-900 block truncate max-w-[120px]">
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
              <span className="text-xs font-bold text-slate-900 block truncate max-w-[120px]">
                {counterparty?.full_name || counterparty?.email || (hasCounterpartyJoined ? 'Joined' : 'Pending Invite')}
              </span>
            </div>
          </div>
          {hasCounterpartyJoined ? (
            <span className="text-[11px] font-semibold text-emerald-700 flex items-center space-x-1">
              <ShieldCheck className="w-4 h-4" />
              <span>Joined</span>
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

        {/* Legal Counsel Card */}
        <div className="p-4 bg-white rounded-lg border border-purple-100 shadow-sm flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-full bg-purple-100 text-purple-800 flex items-center justify-center font-bold text-xs">
              <Scale className="w-4 h-4 text-purple-700" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-purple-700 block">
                Legal Counsel
              </span>
              <span className="text-xs font-bold text-slate-900 block truncate max-w-[120px]">
                {lawyerParticipant?.full_name || lawyerParticipant?.email || (hasLawyerJoined ? 'Counsel Assigned' : 'Independent Review')}
              </span>
            </div>
          </div>
          {hasLawyerJoined ? (
            <button
              onClick={() => {
                setActiveTab('agreement');
                setAgreementSubView('lawyer_review');
              }}
              className="text-[11px] font-semibold text-purple-700 flex items-center space-x-1 hover:underline"
            >
              <ShieldCheck className="w-4 h-4 text-purple-600" />
              <span>Reviewing</span>
            </button>
          ) : (
            <button
              onClick={() => setShowInviteLawyerModal(true)}
              className="text-xs text-purple-700 hover:underline font-semibold"
            >
              Invite Lawyer
            </button>
          )}
        </div>
      </div>

      {/* Workspace Navigation Tabs */}
      <div className="border-b border-slate-200 bg-white px-2 rounded-t-lg shadow-sm">
        <nav className="flex space-x-2 sm:space-x-3 overflow-x-auto">
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
            <span>💬 Chat Messages ({conversations.length})</span>
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
            <span>Extracted Terms</span>
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

          <button
            id="tab-compliance"
            onClick={() => setActiveTab('compliance')}
            className={`py-3 px-3 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors flex items-center space-x-1.5 ${
              activeTab === 'compliance'
                ? 'border-navy-900 text-navy-900'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Scale className="w-3.5 h-3.5 text-blue-600" />
            <span>Legal Readiness & Checklist</span>
          </button>
        </nav>
      </div>




      {/* ========================================================= */}
      {/* TAB 1: CONVERSATIONS (IMPORT & CHAT BUBBLES)               */}
      {/* ========================================================= */}
      {activeTab === 'conversations' && (
        <div className="space-y-6">
          {/* Mode Switcher Tabs for Input */}
          <div className="flex items-center space-x-2 bg-slate-100 p-1 rounded-xl self-start">
            <button
              id="subtab-chat"
              type="button"
              onClick={() => setConvInputMode('chat')}
              className={`px-3.5 py-2 rounded-lg text-xs font-bold transition-all flex items-center space-x-2 ${
                convInputMode === 'chat'
                  ? 'bg-white text-navy-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>💬 Chat / WhatsApp</span>
            </button>

            <button
              id="subtab-call-recording"
              type="button"
              onClick={() => setConvInputMode('call_recording')}
              className={`px-3.5 py-2 rounded-lg text-xs font-bold transition-all flex items-center space-x-2 ${
                convInputMode === 'call_recording'
                  ? 'bg-white text-navy-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Mic className="w-3.5 h-3.5 text-blue-600" />
              <span>🎙️ Call Recording & Mic</span>
            </button>

            <button
              id="subtab-bond-detector"
              type="button"
              onClick={() => setConvInputMode('bond_detector')}
              className={`px-3.5 py-2 rounded-lg text-xs font-bold transition-all flex items-center space-x-2 ${
                convInputMode === 'bond_detector'
                  ? 'bg-white text-navy-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Scale className="w-3.5 h-3.5 text-amber-600" />
              <span>📜 Upload Bond / AI Detector</span>
            </button>
          </div>

          {/* MODE 1: CHAT / WHATSAPP IMPORT */}
          {convInputMode === 'chat' && (
            <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm">
              <h3 className="text-sm font-bold text-navy-900 mb-1">
                Import Business Conversation
              </h3>
              <p className="text-xs text-slate-500 mb-4">
                Paste chat messages from WhatsApp, email threads, or notes. Or upload an image screenshot (<code>.png</code>, <code>.jpg</code>, <code>.webp</code>) or exported <code>.txt</code> file.
              </p>

              <form onSubmit={handleImportConversation} className="space-y-4">
                <div>
                  <textarea
                    id="textarea-import-content"
                    rows={4}
                    placeholder="Example:&#10;[24/10/26, 10:00 AM] Rajesh: Can you complete the design work before 30 October?&#10;[24/10/26, 10:02 AM] Sunil: Yes, agreed on project scope and deliverables.&#10;[24/10/26, 10:05 AM] Rajesh: 50% advance upfront, balance upon completion. Deal?&#10;[24/10/26, 10:06 AM] Sunil: Confirmed, let's proceed."
                    value={pasteContent}
                    onChange={(e) => setPasteContent(e.target.value)}
                    className="w-full p-3 text-xs font-mono border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 outline-none"
                  />
                </div>

                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    {/* 1. Upload Image Option */}
                    <label className="cursor-pointer px-3 py-1.5 border border-purple-200 bg-purple-50/70 hover:bg-purple-100 text-purple-700 text-xs font-semibold rounded-md flex items-center space-x-1.5 transition-colors shadow-sm">
                      <ImageIcon className="w-3.5 h-3.5 text-purple-600" />
                      <span>Upload Chat Image / Screenshot</span>
                      <input
                        type="file"
                        accept="image/png,image/jpeg,image/webp,image/jpg"
                        className="hidden"
                        onChange={(e) => {
                          const f = e.target.files[0];
                          if (f) {
                            setUploadFile(f);
                            setUploadType('image');
                            setImagePreview(URL.createObjectURL(f));
                          }
                        }}
                      />
                    </label>

                    {/* 2. Upload .txt File Option */}
                    <label className="cursor-pointer px-3 py-1.5 border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-medium rounded-md flex items-center space-x-1.5 transition-colors">
                      <Upload className="w-3.5 h-3.5 text-slate-500" />
                      <span>Upload .txt File</span>
                      <input
                        type="file"
                        accept=".txt,.text,.chat"
                        className="hidden"
                        onChange={(e) => {
                          const f = e.target.files[0];
                          if (f) {
                            setUploadFile(f);
                            setUploadType('text');
                            setImagePreview(null);
                          }
                        }}
                      />
                    </label>

                    {/* Active Upload Badge & Thumbnail */}
                    {uploadFile && (
                      <div className="flex items-center space-x-2 px-2.5 py-1 bg-slate-100 border border-slate-200 rounded-md text-xs">
                        {imagePreview && (
                          <img
                            src={imagePreview}
                            alt="Preview"
                            className="w-6 h-6 object-cover rounded border border-slate-300"
                          />
                        )}
                        <span className="font-medium text-slate-700 max-w-[140px] truncate">
                          {uploadFile.name}
                        </span>
                        <button
                          type="button"
                          onClick={() => {
                            setUploadFile(null);
                            setImagePreview(null);
                          }}
                          className="text-slate-400 hover:text-red-600 font-bold ml-1"
                        >
                          ✕
                        </button>
                      </div>
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
                        <span>{analyzing ? 'Analyzing with AI...' : 'Analyze with AI'}</span>
                      </button>
                    )}
                  </div>
                </div>
              </form>

              {aiErrorMsg && (
                <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-800 flex items-start justify-between gap-2">
                  <div className="flex items-start space-x-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-600" />
                    <div>
                      <p className="font-semibold">AI Analysis Notice</p>
                      <p className="mt-0.5">{aiErrorMsg}</p>
                      <p className="mt-1 text-[11px] text-amber-700">
                        You can switch to the <b>Extracted Terms & Clarifications</b> tab to review or manually input agreement terms.
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setAiErrorMsg('')}
                    title="Dismiss notice"
                    className="text-amber-500 hover:text-amber-700 p-1 shrink-0"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          )}

          {/* MODE 2: CALL RECORDING & LIVE MIC */}
          {convInputMode === 'call_recording' && (
            <AudioCallRecorder 
              onImportAudio={handleImportAudio} 
              importing={importing} 
            />
          )}

          {/* MODE 3: UPLOAD BOND & AI DETECTOR */}
          {convInputMode === 'bond_detector' && (
            <div className="space-y-6">
              <BondUploadWidget 
                onUploadBond={handleUploadBond} 
                scanning={scanningBond} 
              />

              {/* List of Uploaded Bonds */}
              {bonds.length > 0 && (
                <div className="space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Uploaded Legal Bonds & Deeds ({bonds.length})
                  </h3>
                  {bonds.map((bond) => {
                    const scorePercent = Math.round((bond.ai_detection_score || 0) * 100);
                    const isAi = bond.is_ai_generated;
                    const terms = bond.extracted_terms || {};
                    const markers = bond.ai_markers || [];

                    return (
                      <div 
                        key={bond.id} 
                        className={`bg-white rounded-xl border shadow-sm overflow-hidden transition-all ${
                          isAi ? 'border-red-300 ring-1 ring-red-100' : 'border-slate-200'
                        }`}
                      >
                        {isAi && (
                          <div className="bg-gradient-to-r from-red-600 to-rose-600 px-4 py-2 text-white text-xs font-bold flex items-center justify-between">
                            <span className="flex items-center space-x-2">
                              <ShieldAlert className="w-4 h-4 animate-pulse" />
                              <span>AI DETECTOR WARNING: Synthetic boilerplate detected ({scorePercent}% AI score)</span>
                            </span>
                            <button
                              onClick={() => {
                                setAlertBond(bond);
                                setShowAlertModal(true);
                              }}
                              className="px-2 py-0.5 bg-white text-red-700 rounded text-[11px] font-bold hover:bg-red-50 transition-colors shadow-sm"
                            >
                              View Full Alert
                            </button>
                          </div>
                        )}

                        <div className="p-5 space-y-4">
                          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-100 pb-3">
                            <div>
                              <div className="flex items-center space-x-2">
                                <span className="text-sm font-bold text-navy-900">
                                  {bond.bond_type}
                                </span>
                                {bond.filename && (
                                  <span className="px-2 py-0.5 bg-slate-100 text-slate-600 font-mono text-[11px] rounded">
                                    {bond.filename}
                                  </span>
                                )}
                              </div>
                              <p className="text-[11px] text-slate-500 mt-0.5">
                                Uploaded by <strong className="text-slate-800">{bond.uploaded_by_name}</strong> • {new Date(bond.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                              </p>
                            </div>

                            <div className="flex items-center space-x-2">
                              {isAi ? (
                                <span className="px-3 py-1 rounded-full text-xs font-bold bg-red-100 text-red-800 border border-red-200 flex items-center space-x-1.5">
                                  <AlertTriangle className="w-3.5 h-3.5 text-red-600" />
                                  <span>{bond.ai_verdict} ({scorePercent}%)</span>
                                </span>
                              ) : (
                                <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center space-x-1.5">
                                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                                  <span>Authentic Legal Drafting ({scorePercent}%)</span>
                                </span>
                              )}
                            </div>
                          </div>

                          {markers.length > 0 && (
                            <div className="p-3 bg-red-50/70 border border-red-100 rounded-lg space-y-1.5">
                              <span className="text-[11px] font-bold text-red-900 block uppercase tracking-wider">
                                Flagged Synthetic Phrases ({markers.length}):
                              </span>
                              <div className="flex flex-wrap gap-1.5">
                                {markers.slice(0, 4).map((m, idx) => (
                                  <span key={idx} className="px-2 py-0.5 bg-white border border-red-200 rounded text-[11px] text-red-800 font-mono">
                                    ⚠️ {m.description || m.marker_type}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {terms && Object.keys(terms).length > 0 && (
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs bg-slate-50 p-3 rounded-lg border border-slate-200">
                              <div>
                                <span className="text-[10px] text-slate-400 font-semibold uppercase block">Obligor</span>
                                <span className="font-bold text-slate-800 truncate block">{terms.obligor || 'Principal'}</span>
                              </div>
                              <div>
                                <span className="text-[10px] text-slate-400 font-semibold uppercase block">Obligee</span>
                                <span className="font-bold text-slate-800 truncate block">{terms.obligee || 'Beneficiary'}</span>
                              </div>
                              <div>
                                <span className="text-[10px] text-slate-400 font-semibold uppercase block">Penal / Bond Sum</span>
                                <span className="font-bold text-emerald-700 block">
                                  {terms.bond_amount ? `₹${terms.bond_amount}` : 'Specified in clauses'}
                                </span>
                              </div>
                              <div>
                                <span className="text-[10px] text-slate-400 font-semibold uppercase block">Stamp Reference</span>
                                <span className="font-mono text-slate-700 truncate block">{terms.stamp_reference || 'Unregistered'}</span>
                              </div>
                            </div>
                          )}

                          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 max-h-32 overflow-y-auto font-mono text-[11px] text-slate-600 whitespace-pre-wrap">
                            {(bond.document_text || bond.content_text || '').slice(0, 600)}...
                          </div>

                          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pt-1 border-t border-slate-100">
                            <div className="text-[11px] text-slate-500">
                              {isAi ? (
                                <span className="text-amber-700 font-medium">
                                  ⚠️ Review carefully before adoption. Converts into plain-language deal terms.
                                </span>
                              ) : (
                                <span className="text-emerald-700 font-medium flex items-center space-x-1">
                                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 inline" />
                                  <span>✓ Authentic Document • Auto-stored in Agreement {bond.agreement_version_number ? `v${bond.agreement_version_number}` : ''}</span>
                                </span>
                              )}
                            </div>

                            <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
                              <button
                                type="button"
                                onClick={() => handleDeleteBond(bond.id)}
                                className="px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 rounded-md font-medium transition-colors"
                              >
                                Delete
                              </button>

                              {!isAi && (
                                <button
                                  type="button"
                                  onClick={() => setActiveTab('agreement')}
                                  className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-md shadow-sm transition-all flex items-center space-x-1.5"
                                >
                                  <FileCheck2 className="w-3.5 h-3.5 text-emerald-100" />
                                  <span>View in Agreement</span>
                                </button>
                              )}

                              <button
                                type="button"
                                onClick={() => handleApplyBondToAgreement(bond.id)}
                                disabled={applyingBond}
                                className="px-4 py-1.5 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm transition-all flex items-center space-x-1.5 disabled:opacity-50"
                              >
                                <FileCheck2 className="w-3.5 h-3.5 text-blue-300" />
                                <span>{applyingBond ? 'Converting...' : isAi ? 'Adopt into Agreement' : 'Re-apply to New Version'}</span>
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Imported Conversations Feed */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Imported Conversation History ({conversations.length} records)
            </h3>

            {conversations.length === 0 ? (
              <div className="p-8 text-center bg-white rounded-lg border border-slate-200 text-xs text-slate-400">
                No conversation transcripts imported yet. Paste chat text or upload a call recording above to begin analysis.
              </div>
            ) : (
              conversations.map((c) => (
                <div key={c.id} className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm space-y-3">
                  <div className="flex justify-between items-center text-xs text-slate-500 border-b border-slate-100 pb-2">
                    <span className="flex items-center space-x-1.5">
                      {c.source_type === 'call_recording' ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-blue-100 text-blue-800">
                          🎙️ Call Recording
                        </span>
                      ) : c.source_type === 'image_upload' || c.image_url ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-purple-100 text-purple-800 flex items-center space-x-1">
                          <ImageIcon className="w-3 h-3 text-purple-600" />
                          <span>Chat Image Screenshot</span>
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-100 text-slate-700">
                          💬 {c.source_type}
                        </span>
                      )}
                      <span>
                        Imported by <strong className="text-slate-800">{c.uploaded_by_name}</strong>
                      </span>
                    </span>
                    <span>{new Date(c.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</span>
                  </div>

                  {/* Image Display if this is an image upload */}
                  {c.image_url && (
                    <div className="my-2 p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center space-x-3">
                      <a href={c.image_url} target="_blank" rel="noopener noreferrer" title="View full image">
                        <img
                          src={c.image_url}
                          alt="Uploaded chat screenshot"
                          className="w-16 h-16 object-cover rounded border border-slate-300 hover:opacity-90 shadow-sm transition-opacity"
                        />
                      </a>
                      <div className="text-xs">
                        <p className="font-bold text-slate-800">Uploaded Chat / Document Screenshot</p>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          Gemini Vision multimodal OCR transcribed dialogue turns below. Click thumbnail to open image in new tab.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Audio Player if this is an audio recording */}
                  {(c.audio_url || c.source_type === 'call_recording') && (
                    <div className="my-2">
                      <AudioPlayerWidget 
                        audioUrl={c.audio_url} 
                        filename={c.audio_filename || "call_recording.wav"} 
                        duration={c.audio_duration} 
                      />
                    </div>
                  )}

                  {/* Messages / Transcript Dialogue */}
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

          {/* Notice banner if no conversation analysis exists */}
          {!analysis && (
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600 flex items-start space-x-2.5">
              <Sparkles className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-slate-800">No AI analysis executed yet</p>
                <p className="mt-0.5 text-slate-500">
                  Authentic terms will populate here once you import chat screenshots, text exports, or call recordings and click "Analyze with AI". You can also draft the agreement directly.
                </p>
              </div>
            </div>
          )}

          {/* Terms Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { label: 'Work Scope & Deliverables', data: analysis?.work_scope, fallback: deal.description || 'Pending scope definition by parties' },
              { label: 'Price & Compensation', data: analysis?.price, fallback: 'Not specified in conversation yet (Pending mutual agreement)' },
              { label: 'Payment Terms & Schedule', data: analysis?.payment_terms, fallback: 'Not specified in conversation yet (Pending mutual agreement)' },
              { label: 'Target Completion Deadline', data: analysis?.completion_deadline, fallback: 'Not specified in conversation yet (To be mutually agreed)' },
              { label: 'Responsibilities of Parties', data: analysis?.responsibilities, fallback: 'Subject to mutual agreement by parties' },
              { label: 'Delivery & Acceptance Criteria', data: analysis?.delivery_acceptance_conditions, fallback: 'Subject to mutual bilateral agreement' },
              { label: 'Cancellation & Refund Terms', data: analysis?.cancellation_refund_conditions, fallback: 'Requires bilateral written agreement' },
              { label: 'Warranty & Revision Terms', data: analysis?.warranty_revision_terms, fallback: 'Subject to mutual bilateral agreement' },
            ].map((term, i) => {
              const hasData = Boolean(term.data && term.data.value);
              const status = hasData ? (term.data.status || 'found_in_conversation') : 'not_specified';
              const val = hasData ? term.data.value : term.fallback;
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
                      status === 'not_specified' ? 'bg-slate-100 text-slate-500 border-slate-200' :
                      'bg-blue-50 text-blue-700 border-blue-200'
                    }`}>
                      {status === 'not_specified' ? 'Not specified yet' : status.replace(/_/g, ' ')}
                    </span>
                  </div>

                  <p className={`text-xs leading-relaxed ${hasData ? 'text-slate-800 font-medium' : 'text-slate-400 italic'}`}>
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
          {/* Lawyer review banner */}
          {isLawyer && (
            <div className="p-3.5 bg-purple-900 text-white rounded-lg flex items-center justify-between shadow-sm">
              <div className="flex items-center space-x-2 text-xs">
                <Scale className="w-4 h-4 text-purple-300 shrink-0" />
                <span>
                  <strong>Independent Legal Counsel Mode:</strong> You are authorized to review this commercial agreement draft, suggest clause amendments with statutory explanations, and provide guidance to the parties.
                </span>
              </div>
            </div>
          )}

          {/* Sub-navigation Tabs for Agreement */}
          <div className="flex items-center space-x-2 bg-slate-100 p-1 rounded-xl self-start">
            <button
              id="subtab-draft"
              type="button"
              onClick={() => setAgreementSubView('draft')}
              className={`px-3.5 py-2 rounded-lg text-xs font-bold transition-all flex items-center space-x-2 ${
                agreementSubView === 'draft'
                  ? 'bg-white text-navy-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>📄 Agreement Draft {currentVersion && `(v${currentVersion.version_number}.0)`}</span>
            </button>

            <button
              id="subtab-assistance"
              type="button"
              onClick={() => setAgreementSubView('assistance')}
              className={`px-3.5 py-2 rounded-lg text-xs font-bold transition-all flex items-center space-x-2 ${
                agreementSubView === 'assistance'
                  ? 'bg-white text-navy-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-blue-600" />
              <span>💡 Agreement Assistance</span>
            </button>

            <button
              id="subtab-lawyer-review"
              type="button"
              onClick={() => setAgreementSubView('lawyer_review')}
              className={`px-3.5 py-2 rounded-lg text-xs font-bold transition-all flex items-center space-x-2 ${
                agreementSubView === 'lawyer_review'
                  ? 'bg-white text-navy-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Scale className="w-3.5 h-3.5 text-purple-600" />
              <span>⚖️ Lawyer Review</span>
            </button>
          </div>

          {/* SUB-VIEW 1: AGREEMENT ASSISTANCE */}
          {agreementSubView === 'assistance' && (
            <AgreementAssistancePanel
              dealId={dealId}
              currentVersion={currentVersion}
              onDraftUpdated={handleDraftUpdated}
            />
          )}

          {/* SUB-VIEW 2: LAWYER REVIEW */}
          {agreementSubView === 'lawyer_review' && (
            <LawyerReviewPanel
              dealId={dealId}
              isOwner={isCreator}
              isLawyer={isLawyer}
              onOpenInviteModal={() => setShowInviteLawyerModal(true)}
              onDraftUpdated={handleDraftUpdated}
            />
          )}

          {/* SUB-VIEW 3: AGREEMENT DRAFT */}
          {agreementSubView === 'draft' && (
            <>
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
              {/* Legal Readiness Quick Status Banner */}
              <div className="p-3.5 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                <div className="flex items-center space-x-2 text-xs">
                  <Scale className="w-4 h-4 text-blue-700 shrink-0" />
                  <div>
                    <span className="font-bold text-navy-900">Legal Document Readiness & Statutory Integrations:</span>{' '}
                    <span className="text-slate-600">
                      Evaluated under Indian Contract Act 1872 (§ 10), Karnataka Stamp Act (Art 5/12/34), and CCA eSign standards.
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveTab('compliance')}
                  className="px-3 py-1 bg-navy-900 hover:bg-navy-800 text-white rounded text-xs font-semibold shrink-0 transition-colors flex items-center space-x-1"
                >
                  <span>Open Readiness Center</span>
                  <ChevronRight className="w-3 h-3" />
                </button>
              </div>


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
                      <label className="block text-xs font-bold text-slate-700 mb-1">5. Complete Legal Agreement Text (Clauses & Terms)</label>
                      <textarea
                        rows={6}
                        value={editedAgreementText}
                        onChange={(e) => setEditedAgreementText(e.target.value)}
                        className="w-full p-2.5 text-xs font-mono border border-slate-300 rounded-md outline-none focus:ring-1 focus:ring-navy-900"
                        placeholder="Complete legal agreement text..."
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
                    
                    {/* Primary Legal Agreement Text (Court-Admissible Instrument) */}
                    <div className="p-6 sm:p-8 bg-slate-50/80 border border-slate-200 rounded-xl space-y-4 shadow-sm">
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
                        <div className="flex items-center space-x-2">
                          <Scale className="w-4 h-4 text-navy-900" />
                          <span className="font-bold text-xs uppercase tracking-wider text-navy-900">
                            Court-Admissible Legal Agreement (IT Act, 2000 § 10A)
                          </span>
                        </div>
                        <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center space-x-1">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          <span>Indian Law Compliant</span>
                        </span>
                      </div>

                      {/* Full Formatted Legal Agreement Text */}
                      <div className="font-serif text-slate-900 text-xs sm:text-sm leading-relaxed whitespace-pre-wrap selection:bg-blue-100 max-h-[700px] overflow-y-auto pr-2 border-b border-slate-200/60 pb-4">
                        {currentVersion.agreement_text || (
                          <div className="text-slate-500 italic py-4">
                            No full agreement text recorded. Click 'Edit Terms' above to add custom clauses or regenerate.
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Commercial Terms Summary Breakdown */}
                    <div className="border border-slate-200 rounded-xl p-5 bg-white space-y-4">
                      <h4 className="font-bold text-navy-900 uppercase tracking-wider text-[11px] flex items-center space-x-1.5 border-b border-slate-100 pb-2">
                        <FileText className="w-3.5 h-3.5 text-blue-600" />
                        <span>Key Commercial Terms Summary</span>
                      </h4>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <span className="text-[10px] font-bold uppercase text-slate-400 block">1. Parties</span>
                          <p className="mt-0.5">
                            <strong className="text-slate-900">{creator?.full_name || deal.creator_name || 'Creator'}</strong> (First Party) & <strong className="text-slate-900">{counterparty?.full_name || counterparty?.email || 'Counterparty'}</strong> (Second Party)
                          </p>
                        </div>
                        <div>
                          <span className="text-[10px] font-bold uppercase text-slate-400 block">2. Financial Consideration</span>
                          <p className="mt-0.5 font-medium text-slate-900">
                            {currentVersion.agreement_json?.financial_terms || `Agreed in ${deal.currency}.`}
                          </p>
                        </div>
                        <div>
                          <span className="text-[10px] font-bold uppercase text-slate-400 block">3. Timeline</span>
                          <p className="mt-0.5">
                            {currentVersion.agreement_json?.timeline || 'As agreed between parties.'}
                          </p>
                        </div>
                        <div>
                          <span className="text-[10px] font-bold uppercase text-slate-400 block">4. Scope of Deliverables</span>
                          <p className="mt-0.5">
                            {currentVersion.agreement_json?.work_scope || deal.description || 'Mutual specifications.'}
                          </p>
                        </div>
                      </div>
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

                    {/* Section 7: Live Digital E-Signatures (On-Agreement Execution) */}
                    <div className="pt-6 border-t border-slate-200">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="font-bold text-navy-900 uppercase tracking-wider text-[11px] flex items-center space-x-1.5">
                          <PenTool className="w-3.5 h-3.5 text-blue-600" />
                          <span>7. LIVE DIGITAL E-SIGNATURES (AUTHENTIC EXECUTION)</span>
                        </h4>
                        {currentVersion.is_mutually_confirmed ? (
                          <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200 flex items-center space-x-1">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            <span>Mutually Accepted — Signing Unlocked</span>
                          </span>
                        ) : (
                          <span className="text-[10px] font-semibold text-amber-700 bg-amber-50 px-2.5 py-0.5 rounded-full border border-amber-200 flex items-center space-x-1">
                            <Clock className="w-3 h-3 text-amber-600" />
                            <span>Locked until both parties accept agreement</span>
                          </span>
                        )}
                      </div>

                      {!currentVersion.is_mutually_confirmed ? (
                        <div className="p-4 bg-slate-50 border border-dashed border-slate-300 rounded-lg text-center text-xs text-slate-500 space-y-1">
                          <p className="font-semibold text-slate-700">Live E-Signatures will unlock automatically once both parties confirm and approve this agreement.</p>
                          <p className="text-[11px] text-slate-400">Click "Confirm & Approve" at the top once you review and agree with the terms.</p>
                        </div>
                      ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          {participants.map((p) => {
                            const sig = currentVersion.agreement_json?.signatures?.[p.id];
                            const isMe = (p.id === myParticipant?.id);

                            return (
                              <div key={p.id} className="p-4 bg-slate-50/80 border border-slate-200 rounded-xl space-y-3">
                                <div className="flex justify-between items-center text-xs">
                                  <span className="text-[10px] uppercase font-bold text-slate-400">
                                    {p.role.toUpperCase()} SIGNATURE
                                  </span>
                                  {sig ? (
                                    <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-100 text-emerald-800 flex items-center space-x-1">
                                      <Check className="w-3 h-3 text-emerald-600" />
                                      <span>Digitally Signed</span>
                                    </span>
                                  ) : (
                                    <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-amber-100 text-amber-800">
                                      Signature Pending
                                    </span>
                                  )}
                                </div>

                                <div className="text-xs font-bold text-slate-900">
                                  {p.full_name || p.email || 'Participant'}
                                </div>

                                {/* Display signed authentic signature */}
                                {sig ? (
                                  <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-2">
                                    <div className="bg-slate-50 p-2 rounded flex items-center justify-center border border-dashed border-slate-200 min-h-[60px]">
                                      <img
                                        src={sig.signature_image}
                                        alt={`${p.full_name || 'Participant'} Signature`}
                                        className="max-h-16 object-contain"
                                      />
                                    </div>
                                    <div className="text-[10px] text-slate-500 space-y-0.5 pt-1 border-t border-slate-100">
                                      <p><strong>Signed by:</strong> {sig.signer_name}</p>
                                      <p><strong>Timestamp:</strong> {new Date(sig.signed_at).toLocaleString()}</p>
                                      <p className="font-mono text-[9px] text-blue-700"><strong>Seal:</strong> {sig.stamp_id}</p>
                                    </div>
                                  </div>
                                ) : isMe ? (
                                  /* Live Interactive Signature Pad for current user */
                                  <div className="space-y-2">
                                    <p className="text-[11px] text-slate-600 font-medium">
                                      Draw your signature below using mouse, stylus, or touchscreen:
                                    </p>
                                    <div className="bg-white border-2 border-dashed border-blue-400 rounded-lg overflow-hidden shadow-inner">
                                      <canvas
                                        ref={signatureCanvasRef}
                                        width={340}
                                        height={110}
                                        className="w-full h-24 cursor-crosshair touch-none bg-white block"
                                        onMouseDown={startDrawing}
                                        onMouseMove={draw}
                                        onMouseUp={stopDrawing}
                                        onMouseLeave={stopDrawing}
                                        onTouchStart={startDrawingTouch}
                                        onTouchMove={drawTouch}
                                        onTouchEnd={stopDrawing}
                                      />
                                    </div>
                                    <div className="flex items-center justify-between pt-1">
                                      <button
                                        type="button"
                                        onClick={clearSignature}
                                        className="px-2.5 py-1 text-slate-500 hover:text-slate-700 text-xs font-medium rounded hover:bg-slate-100 transition-colors"
                                      >
                                        Clear Pad
                                      </button>
                                      <button
                                        type="button"
                                        onClick={handleSignAgreement}
                                        disabled={signingAgreement}
                                        className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-md shadow-sm disabled:opacity-50 flex items-center space-x-1.5 transition-colors"
                                      >
                                        <PenTool className="w-3.5 h-3.5" />
                                        <span>{signingAgreement ? 'Stamping Seal...' : 'Stamp Live E-Signature'}</span>
                                      </button>
                                    </div>
                                  </div>
                                ) : (
                                  <div className="p-6 bg-white/60 border border-slate-200 rounded-lg text-center text-xs text-slate-400">
                                    Awaiting live handwritten e-signature from {p.full_name || 'counterparty'}.
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
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
        </>
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
              {activityLogs.map((log) => (
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

      {/* ========================================================= */}
      {/* TAB 6: LEGAL DOCUMENT READINESS & INTEGRATIONS            */}
      {/* ========================================================= */}
      {activeTab === 'compliance' && (
        <div className="space-y-6">
          <LegalCompliancePanel
            dealId={dealId}
            deal={deal}
            currentVersion={currentVersion}
            onRefresh={loadDealData}
          />
        </div>
      )}

      {/* Invite Modal */}
      <InviteModal
        isOpen={showInviteModal}
        onClose={() => setShowInviteModal(false)}
        dealId={deal.id}
        dealTitle={deal.title}
        creatorName={user?.user_metadata?.full_name || user?.email}
      />

      {/* Invite Real Lawyer Modal */}
      <InviteLawyerModal
        isOpen={showInviteLawyerModal}
        onClose={() => setShowInviteLawyerModal(false)}
        dealId={deal.id}
        dealTitle={deal.title}
        creatorName={creator?.full_name || deal.creator_name || user?.user_metadata?.full_name || user?.email}
        onInvited={loadDealData}
      />

      {/* Immediate AI Detector Alert Modal */}
      <AIDetectorAlertModal
        isOpen={showAlertModal}
        onClose={() => setShowAlertModal(false)}
        bond={alertBond}
        onApplyToAgreement={handleApplyBondToAgreement}
        applying={applyingBond}
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
