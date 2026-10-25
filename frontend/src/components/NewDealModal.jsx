import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { 
  X, 
  FileText, 
  AlertCircle, 
  Mic, 
  Scale 
} from 'lucide-react';
import AudioCallRecorder from './AudioCallRecorder';
import BondUploadWidget from './BondUploadWidget';
import AIDetectorAlertModal from './AIDetectorAlertModal';

export default function NewDealModal({ isOpen, onClose }) {
  const navigate = useNavigate();
  const [creationMode, setCreationMode] = useState('standard'); // 'standard' | 'audio' | 'bond'
  
  // Standard Form State
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('Services');
  const [description, setDescription] = useState('');
  const [currency, setCurrency] = useState('INR');
  const [counterpartyName, setCounterpartyName] = useState('');
  const [counterpartyEmail, setCounterpartyEmail] = useState('');
  const [startDate, setStartDate] = useState('');
  const [completionDate, setCompletionDate] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Bond & AI Alert State
  const [detectedBond, setDetectedBond] = useState(null);
  const [targetDealId, setTargetDealId] = useState(null);
  const [showAiAlertModal, setShowAiAlertModal] = useState(false);
  const [applyingBondTerms, setApplyingBondTerms] = useState(false);

  if (!isOpen) return null;

  async function handleSubmitStandard(e) {
    e.preventDefault();
    if (!title.trim()) {
      setErrorMsg('Please enter a descriptive deal title.');
      return;
    }

    setSubmitting(true);
    setErrorMsg('');

    try {
      const payload = {
        title: title.trim(),
        category,
        description: description.trim(),
        currency,
        counterparty_name: counterpartyName.trim() || undefined,
        counterparty_email: counterpartyEmail.trim() || undefined,
        expected_start_date: startDate || undefined,
        expected_completion_date: completionDate || undefined,
      };

      const newDeal = await api.createDeal(payload);
      onClose();
      navigate(`/deal/${newDeal.id}`);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to create deal. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  // Feature 1: Call Recording -> Create Deal -> Upload Audio -> AI Key Points Agreement -> Route
  async function handleAudioSubmit({ file, transcript }) {
    setSubmitting(true);
    setErrorMsg('');
    try {
      const today = new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
      const dealTitle = title.trim() || `Phone Discussion Deal (${today})`;
      
      const newDeal = await api.createDeal({
        title: dealTitle,
        category,
        currency,
        description: description.trim() || 'Created from call recording transcription and AI key points agreement.',
      });

      const formData = new FormData();
      formData.append('file', file);
      formData.append('source_type', 'call_recording');
      if (transcript) formData.append('content', transcript);

      await api.importConversation(newDeal.id, formData);
      onClose();
      navigate(`/deal/${newDeal.id}`);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to analyze call recording.');
    } finally {
      setSubmitting(false);
    }
  }

  // Feature 2: Bond Upload -> Create Deal -> AI Detector -> Immediate Alert -> Route
  async function handleBondSubmit(formData) {
    setSubmitting(true);
    setErrorMsg('');
    try {
      const today = new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
      const dealTitle = title.trim() || `Legal Bond Agreement (${today})`;

      const newDeal = await api.createDeal({
        title: dealTitle,
        category,
        currency,
        description: description.trim() || 'Created from legal bond document scan and AI detector analysis.',
      });
      setTargetDealId(newDeal.id);

      const uploadedBond = await api.uploadBond(newDeal.id, formData);

      if (uploadedBond.is_ai_generated || uploadedBond.ai_alert_triggered) {
        setDetectedBond(uploadedBond);
        setShowAiAlertModal(true);
      } else {
        await api.applyBondToAgreement(newDeal.id, uploadedBond.id);
        onClose();
        navigate(`/deal/${newDeal.id}`);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to process bond document.');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleApplyAlertBondToAgreement(bondId) {
    if (!targetDealId) return;
    setApplyingBondTerms(true);
    try {
      await api.applyBondToAgreement(targetDealId, bondId);
      setShowAiAlertModal(false);
      onClose();
      navigate(`/deal/${targetDealId}`);
    } catch (err) {
      alert(err.message || 'Failed to convert bond into agreement.');
    } finally {
      setApplyingBondTerms(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
      <div 
        className="w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
          <div>
            <h2 className="text-base font-bold text-navy-900 flex items-center space-x-2">
              <FileText className="w-4 h-4 text-blue-600" />
              <span>Create New Deal Room</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Select how you want to initiate this business agreement.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-200/50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 3 Creation Mode Tabs */}
        <div className="grid grid-cols-3 p-2 bg-slate-100 border-b border-slate-200 gap-1 text-xs font-bold">
          <button
            type="button"
            onClick={() => setCreationMode('standard')}
            className={`py-2 px-2 rounded-lg flex items-center justify-center space-x-1.5 transition-all ${
              creationMode === 'standard' 
                ? 'bg-white text-navy-900 shadow-sm' 
                : 'text-slate-600 hover:text-navy-900'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Standard Deal</span>
          </button>

          <button
            type="button"
            onClick={() => setCreationMode('audio')}
            className={`py-2 px-2 rounded-lg flex items-center justify-center space-x-1.5 transition-all ${
              creationMode === 'audio' 
                ? 'bg-blue-600 text-white shadow-sm' 
                : 'text-slate-600 hover:text-blue-700'
            }`}
          >
            <Mic className="w-3.5 h-3.5" />
            <span>🎙️ Call Recording</span>
          </button>

          <button
            type="button"
            onClick={() => setCreationMode('bond')}
            className={`py-2 px-2 rounded-lg flex items-center justify-center space-x-1.5 transition-all ${
              creationMode === 'bond' 
                ? 'bg-amber-600 text-white shadow-sm' 
                : 'text-slate-600 hover:text-amber-700'
            }`}
          >
            <Scale className="w-3.5 h-3.5" />
            <span>📜 Bond / AI Detector</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
          {errorMsg && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md flex items-start space-x-2 text-red-700 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Quick Title and Category inputs common to all modes */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Deal Room Title {creationMode === 'standard' && <span className="text-red-500">*</span>}
              </label>
              <input
                id="input-deal-title"
                type="text"
                placeholder={creationMode === 'audio' ? 'e.g. Phone Discussion with Sunil' : creationMode === 'bond' ? 'e.g. Indemnity Bond - Apex Infra' : 'e.g. Retail Shop Interior Painting'}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 focus:border-navy-900 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Category
              </label>
              <select
                id="select-deal-category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 focus:border-navy-900 outline-none bg-white"
              >
                <option value="Services">Services</option>
                <option value="Construction">Construction</option>
                <option value="Financial">Financial / Bond</option>
                <option value="Sales">Sales & Trade</option>
                <option value="Freelance">Freelance</option>
                <option value="Real Estate">Real Estate</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Currency
              </label>
              <select
                id="select-deal-currency"
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 focus:border-navy-900 outline-none bg-white"
              >
                <option value="INR">INR (₹)</option>
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
                <option value="AED">AED (د.إ)</option>
              </select>
            </div>
          </div>

          {/* MODE 1: Standard Details Form */}
          {creationMode === 'standard' && (
            <form onSubmit={handleSubmitStandard} className="space-y-4 pt-2">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Scope of Work / Deal Intent
                </label>
                <textarea
                  id="textarea-deal-desc"
                  rows={2}
                  placeholder="Outline the agreed services, deliverables, or objectives..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 focus:border-navy-900 outline-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Partner Name (Optional)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Sunil Sharma"
                    value={counterpartyName}
                    onChange={(e) => setCounterpartyName(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Partner Email (Optional)
                  </label>
                  <input
                    type="email"
                    placeholder="sunil@business.com"
                    value={counterpartyEmail}
                    onChange={(e) => setCounterpartyEmail(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Expected Start Date (Optional)
                  </label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md outline-none bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Completion Deadline (Optional)
                  </label>
                  <input
                    type="date"
                    value={completionDate}
                    onChange={(e) => setCompletionDate(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md outline-none bg-white"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-md"
                >
                  Cancel
                </button>
                <button
                  id="btn-submit-new-deal"
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 bg-navy-900 hover:bg-navy-800 text-white text-xs font-semibold rounded-md shadow-sm transition-colors disabled:opacity-50"
                >
                  {submitting ? 'Creating Room...' : 'Create Deal Room'}
                </button>
              </div>
            </form>
          )}

          {/* MODE 2: Call Recording & Live Mic */}
          {creationMode === 'audio' && (
            <div className="pt-2">
              <AudioCallRecorder 
                onImportAudio={handleAudioSubmit} 
                importing={submitting} 
              />
            </div>
          )}

          {/* MODE 3: Bond Upload & AI Detector */}
          {creationMode === 'bond' && (
            <div className="pt-2">
              <BondUploadWidget 
                onUploadBond={handleBondSubmit} 
                scanning={submitting} 
              />
            </div>
          )}
        </div>
      </div>

      {/* Immediate Alert Modal if AI Detected in Bond */}
      <AIDetectorAlertModal
        isOpen={showAiAlertModal}
        onClose={() => {
          setShowAiAlertModal(false);
          onClose();
          if (targetDealId) navigate(`/deal/${targetDealId}`);
        }}
        bond={detectedBond}
        onApplyToAgreement={handleApplyAlertBondToAgreement}
        applying={applyingBondTerms}
      />
    </div>
  );
}
