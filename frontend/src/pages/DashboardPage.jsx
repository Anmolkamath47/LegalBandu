import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { 
  FileText, 
  Plus, 
  Search, 
  Filter, 
  CheckCircle2, 
  AlertCircle, 
  ChevronRight, 
  Users, 
  RotateCcw,
  Trash2,
  Mic,
  Scale,
  X
} from 'lucide-react';
import AudioCallRecorder from '../components/AudioCallRecorder';
import BondUploadWidget from '../components/BondUploadWidget';
import AIDetectorAlertModal from '../components/AIDetectorAlertModal';

export default function DashboardPage({ onOpenNewDeal }) {
  const { user, profile } = useAuth();
  const navigate = useNavigate();

  const [deals, setDeals] = useState([]);
  const [stats, setStats] = useState({
    total_deals: 0,
    draft_deals: 0,
    awaiting_action: 0,
    mutually_confirmed: 0,
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [deletingId, setDeletingId] = useState(null);

  // Fast Feature 1: Call Recording to Agreement Modal
  const [showAudioModal, setShowAudioModal] = useState(false);
  const [audioDealTitle, setAudioDealTitle] = useState('');
  const [audioCategory, setAudioCategory] = useState('Services');
  const [audioProcessing, setAudioProcessing] = useState(false);

  // Fast Feature 2: Bond Upload & AI Detector Modal
  const [showBondModal, setShowBondModal] = useState(false);
  const [bondDealTitle, setBondDealTitle] = useState('');
  const [bondCategory, setBondCategory] = useState('Services');
  const [bondScanning, setBondScanning] = useState(false);
  const [detectedBond, setDetectedBond] = useState(null);
  const [targetDealId, setTargetDealId] = useState(null);
  const [showAiAlertModal, setShowAiAlertModal] = useState(false);
  const [applyingBondTerms, setApplyingBondTerms] = useState(false);

  useEffect(() => {
    loadDashboardData();
  }, [categoryFilter, statusFilter]);

  async function loadDashboardData() {
    setLoading(true);
    setErrorMsg('');
    try {
      const [statsData, dealsData] = await Promise.all([
        api.getDashboardStats(),
        api.getDeals({
          q: searchQuery.trim() || undefined,
          category: categoryFilter,
          status: statusFilter,
        }),
      ]);
      setStats(statsData);
      setDeals(dealsData || []);
    } catch (err) {
      setErrorMsg(err.message || 'Unable to connect to the backend server. Please verify the service is running.');
    } finally {
      setLoading(false);
    }
  }

  function handleSearchSubmit(e) {
    e.preventDefault();
    loadDashboardData();
  }

  async function handleDeleteDeal(dealId, dealTitle, e) {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete "${dealTitle}"? This will permanently remove this deal room and all related data.`)) {
      return;
    }
    try {
      setDeletingId(dealId);
      await api.deleteDeal(dealId);
      await loadDashboardData();
    } catch (err) {
      alert(err.message || 'Failed to delete deal');
    } finally {
      setDeletingId(null);
    }
  }

  // Feature 1 Handler: Call Recording -> Transcribe -> AI Key Points -> Agreement -> Navigate
  async function handleDashboardAudioStart({ file, transcript }) {
    setAudioProcessing(true);
    try {
      const today = new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
      const title = audioDealTitle.trim() || `Call Recording Agreement (${today})`;
      const deal = await api.createDeal({
        title,
        category: audioCategory || 'Services',
        currency: 'INR',
        description: 'Auto-created from call recording transcription and key points analysis.'
      });

      const formData = new FormData();
      formData.append('file', file);
      formData.append('source_type', 'call_recording');
      if (transcript) formData.append('content', transcript);

      await api.importConversation(deal.id, formData);
      setShowAudioModal(false);
      navigate(`/deal/${deal.id}`);
    } catch (err) {
      alert(err.message || 'Failed to analyze call recording.');
    } finally {
      setAudioProcessing(false);
    }
  }

  // Feature 2 Handler: Bond Upload -> AI Detector -> Immediate Alert -> Convert to Agreement
  async function handleDashboardBondStart(formData) {
    setBondScanning(true);
    try {
      const today = new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
      const title = bondDealTitle.trim() || `Legal Bond Agreement (${today})`;
      const deal = await api.createDeal({
        title,
        category: bondCategory || 'Services',
        currency: 'INR',
        description: 'Created from legal bond document scan and AI detector analysis.'
      });
      setTargetDealId(deal.id);

      const uploadedBond = await api.uploadBond(deal.id, formData);
      
      if (uploadedBond.is_ai_generated || uploadedBond.ai_alert_triggered) {
        setDetectedBond(uploadedBond);
        setShowBondModal(false);
        setShowAiAlertModal(true);
      } else {
        await api.applyBondToAgreement(deal.id, uploadedBond.id);
        setShowBondModal(false);
        navigate(`/deal/${deal.id}`);
      }
    } catch (err) {
      alert(err.message || 'Failed to scan and process bond document.');
    } finally {
      setBondScanning(false);
    }
  }

  async function handleApplyAlertBondToAgreement(bondId) {
    if (!targetDealId) return;
    setApplyingBondTerms(true);
    try {
      await api.applyBondToAgreement(targetDealId, bondId);
      setShowAiAlertModal(false);
      navigate(`/deal/${targetDealId}`);
    } catch (err) {
      alert(err.message || 'Failed to convert bond into agreement.');
    } finally {
      setApplyingBondTerms(false);
    }
  }

  const displayName = profile?.full_name || user?.full_name || user?.email?.split('@')[0] || 'User';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Welcome Banner */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center pb-6 border-b border-slate-200 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">
            Welcome back, {displayName}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage your deal rooms, imported conversations, and bilateral confirmations.
          </p>
        </div>

        <button
          id="btn-create-deal-dashboard"
          onClick={onOpenNewDeal}
          className="inline-flex items-center space-x-1.5 px-4 py-2 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Create New Deal</span>
        </button>
      </div>

      {/* 2 Primary Core Features Quick-Action Hub */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Feature 1: Call Recording to Agreement */}
        <div className="bg-gradient-to-br from-blue-950 via-slate-900 to-navy-900 rounded-2xl p-5 text-white shadow-md border border-blue-800/60 flex flex-col justify-between relative overflow-hidden group">
          <div className="space-y-2.5">
            <div className="flex items-center space-x-2">
              <span className="p-2 bg-blue-500/20 text-blue-400 rounded-lg">
                <Mic className="w-5 h-5 text-blue-400" />
              </span>
              <span className="text-[10px] font-bold uppercase tracking-wider bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded-full border border-blue-500/30">
                FEATURE 1 • AUDIO CALL TO AGREEMENT
              </span>
            </div>
            <h3 className="text-base font-bold text-white">
              Call Recording & AI Key Points Agreement
            </h3>
            <p className="text-xs text-blue-100/80 leading-relaxed">
              Record a live call or upload audio recordings (.mp3, .wav, .m4a, .webm). 
              AI automatically transcribes dialogues, extracts deliverables & payment terms, 
              and puts key points directly into the mutual agreement!
            </p>
          </div>
          <div className="mt-5 pt-3 border-t border-blue-800/40 flex items-center justify-between">
            <span className="text-[11px] text-blue-300/80">Supports mic & audio files</span>
            <button
              id="btn-dashboard-record-call"
              onClick={() => {
                const today = new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
                setAudioDealTitle(`Phone Call Discussion (${today})`);
                setShowAudioModal(true);
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold shadow-md transition-all active:scale-95 flex items-center space-x-1.5"
            >
              <Mic className="w-3.5 h-3.5" />
              <span>Record or Upload Audio</span>
            </button>
          </div>
        </div>

        {/* Feature 2: Bond Upload & AI Detector */}
        <div className="bg-gradient-to-br from-amber-950 via-slate-900 to-navy-900 rounded-2xl p-5 text-white shadow-md border border-amber-800/60 flex flex-col justify-between relative overflow-hidden group">
          <div className="space-y-2.5">
            <div className="flex items-center space-x-2">
              <span className="p-2 bg-amber-500/20 text-amber-400 rounded-lg">
                <Scale className="w-5 h-5 text-amber-400" />
              </span>
              <span className="text-[10px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full border border-amber-500/30">
                FEATURE 2 • BOND SCAN & AI DETECTOR
              </span>
            </div>
            <h3 className="text-base font-bold text-white">
              Upload Bond & AI Synthetic Detector
            </h3>
            <p className="text-xs text-amber-100/80 leading-relaxed">
              Upload legal bonds, indemnity bonds, or e-stamps. 
              Our multi-vector detector scans for ChatGPT/synthetic AI markers with an immediate alert, 
              and converts covenants directly into a verified deal agreement.
            </p>
          </div>
          <div className="mt-5 pt-3 border-t border-amber-800/40 flex items-center justify-between">
            <span className="text-[11px] text-amber-300/80">Instant AI Alert + Conversion</span>
            <button
              id="btn-dashboard-upload-bond"
              onClick={() => {
                const today = new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
                setBondDealTitle(`Legal Bond Agreement (${today})`);
                setShowBondModal(true);
              }}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-bold shadow-md transition-all active:scale-95 flex items-center space-x-1.5"
            >
              <Scale className="w-3.5 h-3.5" />
              <span>Upload & Verify Bond</span>
            </button>
          </div>
        </div>
      </div>

      {/* Error Banner with Retry */}
      {errorMsg && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 text-xs text-red-800">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={loadDashboardData}
            className="px-3 py-1 bg-red-100 hover:bg-red-200 text-red-900 font-semibold rounded text-xs flex items-center space-x-1"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Retry Connection</span>
          </button>
        </div>
      )}

      {/* Real Statistics Cards */}
      <div className="mt-6 grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 bg-white rounded-lg border border-slate-200 shadow-sm">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
            Total Deals
          </span>
          <p className="mt-2 text-2xl font-bold text-navy-900">{stats.total_deals}</p>
          <span className="text-[11px] text-slate-400 mt-1 block">Active deal rooms</span>
        </div>

        <div className="p-4 bg-white rounded-lg border border-slate-200 shadow-sm">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
            Draft Deals
          </span>
          <p className="mt-2 text-2xl font-bold text-slate-700">{stats.draft_deals}</p>
          <span className="text-[11px] text-slate-400 mt-1 block">Importing & scoping</span>
        </div>

        <div className="p-4 bg-white rounded-lg border border-slate-200 shadow-sm">
          <span className="text-[11px] font-semibold text-amber-700 uppercase tracking-wider block">
            Awaiting Action
          </span>
          <p className="mt-2 text-2xl font-bold text-amber-600">{stats.awaiting_action}</p>
          <span className="text-[11px] text-slate-400 mt-1 block">Review or confirmation</span>
        </div>

        <div className="p-4 bg-white rounded-lg border border-slate-200 shadow-sm">
          <span className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wider block">
            Mutually Confirmed
          </span>
          <p className="mt-2 text-2xl font-bold text-emerald-600">{stats.mutually_confirmed}</p>
          <span className="text-[11px] text-slate-400 mt-1 block">Bilateral approvals</span>
        </div>
      </div>

      {/* Filters & Search */}
      <div className="mt-8 bg-white p-3 sm:p-4 rounded-lg border border-slate-200 shadow-sm">
        <div className="flex flex-col md:flex-row gap-3 justify-between items-center">
          
          {/* Search Input */}
          <form onSubmit={handleSearchSubmit} className="relative w-full md:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              id="input-deal-search"
              type="text"
              placeholder="Search by title or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 focus:border-navy-900 outline-none"
            />
          </form>

          {/* Category & Status Filters */}
          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
            <div className="flex items-center space-x-1 text-xs text-slate-500">
              <Filter className="w-3.5 h-3.5" />
              <span>Category:</span>
            </div>
            <select
              id="filter-category"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-2.5 py-1.5 text-xs border border-slate-300 rounded-md outline-none bg-white text-slate-700"
            >
              <option value="all">All Categories</option>
              <option value="Services">Services</option>
              <option value="Retail">Retail</option>
              <option value="Freelance">Freelance</option>
              <option value="Consulting">Consulting</option>
              <option value="Construction">Construction</option>
              <option value="Technology">Technology</option>
              <option value="Other">Other</option>
            </select>

            <select
              id="filter-status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2.5 py-1.5 text-xs border border-slate-300 rounded-md outline-none bg-white text-slate-700"
            >
              <option value="all">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="awaiting_review">Awaiting Review</option>
              <option value="changes_requested">Changes Requested</option>
              <option value="awaiting_counterparty">Awaiting Counterparty</option>
              <option value="mutually_confirmed">Mutually Confirmed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Deals List */}
      <div className="mt-6">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-400 bg-white rounded-lg border border-slate-200">
            Loading deal rooms...
          </div>
        ) : deals.length === 0 ? (
          /* Honest Empty State */
          <div className="p-12 text-center bg-white rounded-lg border border-dashed border-slate-300">
            <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-sm font-bold text-slate-800">No deals found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              {searchQuery || categoryFilter !== 'all' || statusFilter !== 'all'
                ? 'No deals matched your search criteria. Try resetting the filters.'
                : 'You have not created or joined any deal rooms yet. Create your first deal room to start converting informal messages into confirmed contracts.'}
            </p>
            <button
              id="btn-empty-state-create"
              onClick={onOpenNewDeal}
              className="mt-5 inline-flex items-center space-x-1.5 px-4 py-2 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Create Your First Deal</span>
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-slate-200 divide-y divide-slate-100 shadow-sm overflow-hidden">
            {deals.map((deal) => {
              const counterparty = deal.counterparty;
              const counterpartyName = counterparty?.full_name || counterparty?.email || 'Not Invited Yet';

              return (
                <div
                  key={deal.id}
                  id={`deal-card-${deal.id}`}
                  onClick={() => navigate(`/deal/${deal.id}`)}
                  className="p-4 sm:p-5 hover:bg-slate-50/80 cursor-pointer transition-colors flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2.5">
                      <span className="text-sm font-bold text-navy-900 truncate">
                        {deal.title}
                      </span>
                      
                      {/* Status Badges */}
                      {deal.status === 'mutually_confirmed' ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center space-x-1 shrink-0">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Mutually Confirmed</span>
                        </span>
                      ) : deal.status === 'changes_requested' ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-50 text-red-700 border border-red-200 shrink-0">
                          Changes Requested
                        </span>
                      ) : deal.status === 'awaiting_review' || deal.status === 'awaiting_counterparty' ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 shrink-0">
                          Awaiting Review
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200 shrink-0">
                          Draft
                        </span>
                      )}

                      {deal.current_version_number && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-100 text-slate-600 border border-slate-200 shrink-0">
                          v{deal.current_version_number}.0
                        </span>
                      )}
                    </div>

                    <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                      <span className="flex items-center space-x-1">
                        <Users className="w-3.5 h-3.5 text-slate-400" />
                        <span>Partner: {counterpartyName}</span>
                      </span>
                      <span>•</span>
                      <span>Category: {deal.category}</span>
                      <span>•</span>
                      <span>Currency: {deal.currency}</span>
                      <span>•</span>
                      <span>Updated: {new Date(deal.updated_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                    </div>
                  </div>

                  {/* Next Required Action Badge & Actions */}
                  <div className="flex items-center space-x-3 shrink-0 w-full sm:w-auto justify-between sm:justify-end">
                    <div className="text-right">
                      <span className="text-[10px] font-medium text-slate-400 block uppercase tracking-wider">
                        Next Action
                      </span>
                      <span className="text-xs font-semibold text-blue-700 block">
                        {deal.next_action}
                      </span>
                    </div>

                    {/* Delete Deal Action */}
                    <button
                      id={`btn-delete-deal-${deal.id}`}
                      title="Delete deal room"
                      disabled={deletingId === deal.id}
                      onClick={(e) => handleDeleteDeal(deal.id, deal.title, e)}
                      className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>

                    <ChevronRight className="w-4 h-4 text-slate-400" />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Feature 1 Modal: Call Recording to Agreement */}
      {showAudioModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm animate-in fade-in">
          <div 
            className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 bg-blue-100 text-blue-700 rounded-lg">
                  <Mic className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-navy-900">
                    Call Recording & AI Agreement Generator
                  </h3>
                  <p className="text-xs text-slate-500">
                    AI transcribes dialogues and automatically extracts key points into the bilateral agreement.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowAudioModal(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200/60"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Deal Room Title
                  </label>
                  <input
                    type="text"
                    value={audioDealTitle}
                    onChange={(e) => setAudioDealTitle(e.target.value)}
                    placeholder="e.g. Phone Discussion - Shop Painting"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg outline-none focus:border-navy-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Category
                  </label>
                  <select
                    value={audioCategory}
                    onChange={(e) => setAudioCategory(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg outline-none bg-white focus:border-navy-900"
                  >
                    <option value="Services">Services</option>
                    <option value="Construction">Construction</option>
                    <option value="Sales">Sales & Trade</option>
                    <option value="Freelance">Freelance & Tech</option>
                    <option value="Real Estate">Real Estate</option>
                  </select>
                </div>
              </div>

              {/* Embed Audio Recorder / Uploader */}
              <AudioCallRecorder 
                onImportAudio={handleDashboardAudioStart} 
                importing={audioProcessing} 
              />
            </div>
          </div>
        </div>
      )}

      {/* Feature 2 Modal: Bond Upload & AI Detector */}
      {showBondModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm animate-in fade-in">
          <div 
            className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 bg-amber-100 text-amber-700 rounded-lg">
                  <Scale className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-navy-900">
                    Upload Bond & AI Synthetic Detector
                  </h3>
                  <p className="text-xs text-slate-500">
                    Multi-vector scan for synthetic ChatGPT phrases with immediate alert and agreement conversion.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowBondModal(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200/60"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Deal Room Title
                  </label>
                  <input
                    type="text"
                    value={bondDealTitle}
                    onChange={(e) => setBondDealTitle(e.target.value)}
                    placeholder="e.g. Indemnity Bond - Apex Infra"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg outline-none focus:border-navy-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Category
                  </label>
                  <select
                    value={bondCategory}
                    onChange={(e) => setBondCategory(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg outline-none bg-white focus:border-navy-900"
                  >
                    <option value="Services">Services</option>
                    <option value="Construction">Construction</option>
                    <option value="Financial">Financial / Bond</option>
                    <option value="Sales">Sales & Trade</option>
                    <option value="Real Estate">Real Estate</option>
                  </select>
                </div>
              </div>

              {/* Embed Bond Upload Widget */}
              <BondUploadWidget 
                onUploadBond={handleDashboardBondStart} 
                scanning={bondScanning} 
              />
            </div>
          </div>
        </div>
      )}

      {/* Immediate AI Detector Alert Modal if Synthetic Content Found */}
      <AIDetectorAlertModal
        isOpen={showAiAlertModal}
        onClose={() => {
          setShowAiAlertModal(false);
          if (targetDealId) navigate(`/deal/${targetDealId}`);
        }}
        bond={detectedBond}
        onApplyToAgreement={handleApplyAlertBondToAgreement}
        applying={applyingBondTerms}
      />
    </div>
  );
}
