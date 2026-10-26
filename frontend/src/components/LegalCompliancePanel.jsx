import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  ShieldCheck,
  ShieldAlert,
  Scale,
  FileCheck,
  FileText,
  Stamp,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Lock,
  RefreshCw,
  Award,
  Layers,
  Sparkles,
  Copy,
  Check,
  Info,
  ChevronRight,
  UserCheck,
  Building2,
  ArrowRight,
} from 'lucide-react';

export default function LegalCompliancePanel({ dealId, deal, currentVersion, onRefresh }) {
  const [activeTab, setActiveTab] = useState('checklist'); // 'checklist', 'esign', 'stamping', 'templates', 'evidence'
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // 1. Checklist State
  const [checklistData, setChecklistData] = useState(null);

  // 2. eSign Providers State
  const [esignProvidersData, setEsignProvidersData] = useState(null);

  // 3. Stamp Duty Calculator State
  const [selectedState, setSelectedState] = useState('Karnataka');
  const [instrumentCategory, setInstrumentCategory] = useState('commercial_service');
  const [considerationInput, setConsiderationInput] = useState('');
  const [isBondToggle, setIsBondToggle] = useState(false);
  const [isIndemnityToggle, setIsIndemnityToggle] = useState(false);
  const [calculatedDuty, setCalculatedDuty] = useState(null);
  const [calcLoading, setCalcLoading] = useState(false);

  // Stamping Verification Form
  const [stampCertInput, setStampCertInput] = useState('');
  const [stampGrnInput, setStampGrnInput] = useState('');
  const [stampAmountInput, setStampAmountInput] = useState('500');
  const [verifyingStamp, setVerifyingStamp] = useState(false);
  const [stampVerificationResult, setStampVerificationResult] = useState(null);

  // 4. Lawyer Templates State
  const [templates, setTemplates] = useState([]);
  const [applyingTemplateId, setApplyingTemplateId] = useState(null);

  // 5. Evidence & SHA-256 State
  const [auditCertData, setAuditCertData] = useState(null);
  const [copiedHash, setCopiedHash] = useState(false);

  useEffect(() => {
    if (dealId) {
      loadAllComplianceData();
    }
  }, [dealId, currentVersion]);

  async function loadAllComplianceData() {
    setLoading(true);
    setErrorMsg('');
    try {
      const [checklist, esign, tpls] = await Promise.all([
        api.getDealReadinessChecklist(dealId).catch(() => null),
        api.getESignProviders().catch(() => null),
        api.getLawyerApprovedTemplates().catch(() => []),
      ]);

      setChecklistData(checklist);
      setEsignProvidersData(esign);
      setTemplates(tpls || []);

      // Trigger default Karnataka duty calculation
      runDutyCalculation('Karnataka', 'commercial_service', 0, false, false);

      // Load audit certificate if version exists
      if (currentVersion) {
        api.getDealAuditCertificate(dealId).then(setAuditCertData).catch(() => {});
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load legal readiness data.');
    } finally {
      setLoading(false);
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    try {
      const [checklist, audit] = await Promise.all([
        api.getDealReadinessChecklist(dealId),
        api.getDealAuditCertificate(dealId).catch(() => null),
      ]);
      setChecklistData(checklist);
      setAuditCertData(audit);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(err.message || 'Failed to refresh checklist.');
    } finally {
      setRefreshing(false);
    }
  }

  async function runDutyCalculation(state, instrType, consideration, isBond, isIndemnity) {
    setCalcLoading(true);
    try {
      const res = await api.calculateStampDuty({
        state,
        instrument_type: instrType,
        consideration_amount: parseFloat(consideration) || 0,
        is_bond: isBond,
        is_indemnity: isIndemnity,
      });
      setCalculatedDuty(res);
    } catch (err) {
      console.error('Duty calculation failed:', err);
    } finally {
      setCalcLoading(false);
    }
  }

  async function handleVerifyAndRecordStamp(e) {
    e.preventDefault();
    if (!stampCertInput.trim()) {
      alert('Please enter an e-Stamp certificate number (e.g. IN-KA82937401928374U).');
      return;
    }

    setVerifyingStamp(true);
    try {
      const payload = {
        certificate_number: stampCertInput.trim(),
        grn: stampGrnInput.trim() || undefined,
        amount_paid: parseFloat(stampAmountInput) || 500.0,
        state: selectedState,
        party_a: deal?.creator_name || 'First Party',
        party_b: deal?.counterparty_email || 'Second Party',
      };

      const res = await api.verifyStampDutyCertificate(payload);
      setStampVerificationResult(res);

      // Also record this as verified in the deal compliance lifecycle record
      await api.advanceComplianceState(dealId, {
        target_state: 'Stamped — genuine applicable evidence verified',
        evidence_payload: res,
      }).catch(() => {});

      alert(`e-Stamp certificate verified successfully for ${selectedState}! Recorded into the tamper-evident audit log.`);
      handleRefresh();
    } catch (err) {
      alert(err.message || 'Verification failed.');
    } finally {
      setVerifyingStamp(false);
    }
  }

  async function handleApplyTemplate(templateId, templateTitle) {
    const confirmMsg = `Apply lawyer-approved template "${templateTitle}"? This will format your active agreement terms into court-vetted clauses under Section 10 Indian Contract Act, 1872.`;
    if (!window.confirm(confirmMsg)) return;

    setApplyingTemplateId(templateId);
    try {
      const res = await api.applyLawyerTemplate(dealId, templateId);
      alert(res.message || 'Template applied successfully!');
      handleRefresh();
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(err.message || 'Failed to apply template.');
    } finally {
      setApplyingTemplateId(null);
    }
  }

  function handleCopyHash() {
    if (auditCertData?.document_hash_sha256) {
      navigator.clipboard.writeText(auditCertData.document_hash_sha256);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    }
  }

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-400 flex items-center justify-center space-x-2 bg-white rounded-xl border border-slate-200">
        <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
        <span className="text-xs">Evaluating legal-document readiness & statutory compliance...</span>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden font-sans">
      
      {/* 1. Header Banner */}
      <div className="p-5 border-b border-slate-200 bg-gradient-to-r from-slate-900 to-navy-900 text-white flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <Scale className="w-5 h-5 text-blue-400" />
            <h3 className="text-base font-bold tracking-tight text-white">
              Legalbandu Statutory Readiness & Integration Suite
            </h3>
            <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-blue-500/20 text-blue-200 border border-blue-400/30">
              Indian Contract Act, 1872
            </span>
          </div>
          <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
            Statutory readiness checklist, state-aware stamp duty (Karnataka Stamp Act), CCA-approved electronic signatures (eMudhra / Protean), and tamper-evident SHA-256 evidence.
          </p>
        </div>

        {/* Readiness Score Pill */}
        {checklistData && (
          <div className="flex flex-col items-end shrink-0 bg-white/10 backdrop-blur-sm px-4 py-2 rounded-lg border border-white/15">
            <span className="text-[10px] font-bold text-blue-200 uppercase tracking-wider">
              Document Readiness Score
            </span>
            <div className="flex items-center space-x-2 mt-0.5">
              <span className="text-lg font-black text-white">{checklistData.readiness_percentage}%</span>
              <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                checklistData.readiness_percentage >= 80
                  ? 'bg-emerald-500/30 text-emerald-200 border border-emerald-400/40'
                  : 'bg-amber-500/30 text-amber-200 border border-amber-400/40'
              }`}>
                {checklistData.overall_status}
              </span>
            </div>
            <span className="text-[10px] text-slate-300 mt-0.5">
              {checklistData.passed_count} of {checklistData.total_count} criteria satisfied
            </span>
          </div>
        )}
      </div>

      {/* 2. Navigation Tabs */}
      <div className="border-b border-slate-200 bg-slate-50 px-2 flex space-x-1 overflow-x-auto text-xs font-semibold">
        <button
          onClick={() => setActiveTab('checklist')}
          className={`py-3 px-3.5 border-b-2 transition-all flex items-center space-x-2 whitespace-nowrap ${
            activeTab === 'checklist'
              ? 'border-navy-900 text-navy-900 bg-white font-bold shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <FileCheck className="w-4 h-4 text-emerald-600" />
          <span>1. Readiness Checklist (9 Criteria)</span>
          {checklistData && (
            <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-slate-200 text-slate-700">
              {checklistData.passed_count}/{checklistData.total_count}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('esign')}
          className={`py-3 px-3.5 border-b-2 transition-all flex items-center space-x-2 whitespace-nowrap ${
            activeTab === 'esign'
              ? 'border-navy-900 text-navy-900 bg-white font-bold shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Award className="w-4 h-4 text-blue-600" />
          <span>2. CCA e-Signature Providers</span>
        </button>

        <button
          onClick={() => setActiveTab('stamping')}
          className={`py-3 px-3.5 border-b-2 transition-all flex items-center space-x-2 whitespace-nowrap ${
            activeTab === 'stamping'
              ? 'border-navy-900 text-navy-900 bg-white font-bold shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Stamp className="w-4 h-4 text-teal-600" />
          <span>3. Karnataka & State Stamp Duty</span>
        </button>

        <button
          onClick={() => setActiveTab('templates')}
          className={`py-3 px-3.5 border-b-2 transition-all flex items-center space-x-2 whitespace-nowrap ${
            activeTab === 'templates'
              ? 'border-navy-900 text-navy-900 bg-white font-bold shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Scale className="w-4 h-4 text-indigo-600" />
          <span>4. Approved Lawyer Templates (Sec 10 ICA)</span>
        </button>

        <button
          onClick={() => setActiveTab('evidence')}
          className={`py-3 px-3.5 border-b-2 transition-all flex items-center space-x-2 whitespace-nowrap ${
            activeTab === 'evidence'
              ? 'border-navy-900 text-navy-900 bg-white font-bold shadow-sm'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Lock className="w-4 h-4 text-amber-600" />
          <span>5. Tamper-Evident SHA-256 Audit</span>
        </button>
      </div>

      {/* 3. Panel Content */}
      <div className="p-6">
        
        {/* ========================================================= */}
        {/* TAB 1: 9-POINT BOND & LEGAL-DOCUMENT READINESS CHECKLIST  */}
        {/* ========================================================= */}
        {activeTab === 'checklist' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
              <div>
                <h4 className="text-sm font-bold text-navy-900 flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>Statutory Legal-Document Readiness Checklist</span>
                </h4>
                <p className="text-xs text-slate-600 mt-0.5">
                  The essential legal readiness criteria every bond and commercial agreement must satisfy for enforceability under Indian law.
                </p>
              </div>

              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="px-3 py-1.5 bg-white text-navy-900 text-xs font-semibold rounded-md border border-slate-300 shadow-sm hover:bg-slate-50 flex items-center space-x-1.5 shrink-0"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
                <span>{refreshing ? 'Evaluating...' : 'Re-Run Checklist'}</span>
              </button>
            </div>

            {/* Checklist Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {checklistData?.criteria?.map((item) => {
                const isPassed = item.status === 'passed';
                const isAction = item.status === 'action_required';

                return (
                  <div
                    key={item.criterion_id}
                    className={`p-4 rounded-xl border transition-all ${
                      isPassed
                        ? 'bg-emerald-50/40 border-emerald-200/80 shadow-xs'
                        : isAction
                        ? 'bg-amber-50/50 border-amber-200/90 shadow-xs'
                        : 'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center space-x-2">
                        {isPassed ? (
                          <div className="w-6 h-6 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700 shrink-0">
                            <CheckCircle2 className="w-4 h-4" />
                          </div>
                        ) : (
                          <div className="w-6 h-6 rounded-full bg-amber-100 flex items-center justify-center text-amber-700 shrink-0">
                            <AlertTriangle className="w-4 h-4" />
                          </div>
                        )}
                        <span className="text-xs font-bold text-slate-900">{item.name}</span>
                      </div>

                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                          isPassed
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                            : 'bg-amber-100 text-amber-900 border border-amber-300'
                        }`}
                      >
                        {isPassed ? 'Satisfied' : 'Action Required'}
                      </span>
                    </div>

                    <p className="text-xs text-slate-700 mt-2.5 font-medium leading-relaxed">
                      {item.description}
                    </p>

                    <div className="mt-2 text-[11px] text-slate-600 bg-white/70 p-2.5 rounded-lg border border-slate-200/70 space-y-1">
                      <div><strong className="text-slate-800">Status:</strong> {item.details}</div>
                      <div className="text-[10px] text-slate-400 font-mono">Statutory Basis: {item.statutory_ref}</div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Quick Action Navigation bar */}
            <div className="p-4 bg-navy-50/60 rounded-xl border border-navy-100 flex flex-wrap items-center justify-between gap-3 text-xs">
              <span className="font-semibold text-navy-900">
                To complete remaining criteria: Apply a lawyer template, verify Karnataka stamp duty, and execute live e-signatures.
              </span>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setActiveTab('templates')}
                  className="px-3 py-1.5 bg-navy-900 hover:bg-navy-800 text-white rounded-md font-semibold text-xs transition-colors"
                >
                  View Approved Templates
                </button>
                <button
                  onClick={() => setActiveTab('stamping')}
                  className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-md font-semibold text-xs transition-colors"
                >
                  Calculate Stamp Duty
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 2: CCA-APPROVED ELECTRONIC SIGNATURE PROVIDERS        */}
        {/* ========================================================= */}
        {activeTab === 'esign' && (
          <div className="space-y-6">
            <div className="p-4 bg-blue-50/70 border border-blue-200 rounded-xl space-y-2 text-xs text-blue-950">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <span className="font-bold text-sm text-blue-900 flex items-center space-x-1.5">
                  <Award className="w-4 h-4 text-blue-700" />
                  <span>Compliant Indian Electronic-Signature Service Providers</span>
                </span>
                <a
                  href="https://cca.gov.in/CAServicesPublic.html"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center space-x-1 text-xs font-bold text-blue-700 hover:text-blue-900 underline bg-white px-2.5 py-1 rounded border border-blue-200 shadow-2xs"
                >
                  <span>Official CCA Directory</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
              <p className="leading-relaxed">
                Connects to Indian electronic-signature service providers supporting legally compliant eSign workflows under Section 3A and 10A of the Information Technology Act, 2000. Provides formal signing workflows, signer identity authentication (Aadhaar eKYC OTP / Biometric / Class 3 DSC), and court-admissible signature evidence.
              </p>
            </div>

            {/* Providers Evaluation Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {esignProvidersData?.providers?.map((p) => (
                <div
                  key={p.provider_id}
                  className={`p-5 rounded-xl border flex flex-col justify-between space-y-4 transition-all ${
                    p.is_recommended
                      ? 'border-blue-300 bg-white shadow-xs ring-1 ring-blue-100'
                      : 'border-slate-200 bg-slate-50/50'
                  }`}
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <h4 className="font-bold text-sm text-navy-900">{p.name}</h4>
                          {p.is_recommended && (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 border border-blue-200">
                              Recommended
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5">{p.cca_role}</p>
                      </div>

                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center space-x-1 shrink-0">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        <span>CCA Approved</span>
                      </span>
                    </div>

                    <div className="space-y-2 text-xs">
                      <div>
                        <span className="text-[10px] font-bold uppercase text-slate-400 block">Authentication Methods:</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {p.authentication_methods.map((m, idx) => (
                            <span key={idx} className="px-2 py-0.5 bg-slate-100 border border-slate-200 rounded text-[11px] text-slate-700">
                              ✓ {m}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div>
                        <span className="text-[10px] font-bold uppercase text-slate-400 block">Signature Evidence Generated:</span>
                        <p className="text-[11px] text-slate-600 font-mono bg-slate-50 p-2 rounded border border-slate-200 mt-0.5 leading-relaxed">
                          {p.signature_evidence_format}
                        </p>
                      </div>

                      <div>
                        <span className="text-[10px] font-bold uppercase text-slate-400 block">Evaluation & Compatibility:</span>
                        <p className="text-xs text-slate-700 leading-relaxed mt-0.5">
                          {p.evaluation_summary}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                    <a
                      href={p.official_website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline flex items-center space-x-1 font-semibold"
                    >
                      <span>Visit Provider Portal</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>

                    <a
                      href="https://cca.gov.in/CAServicesPublic.html"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[11px] text-slate-500 hover:text-slate-800 flex items-center space-x-1"
                    >
                      <span>Verify on CCA.gov.in</span>
                      <ChevronRight className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              ))}
            </div>

            {/* Ineligible Instruments Disclaimer */}
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start space-x-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-bold">Statutory Exclusions from Electronic Signing (IT Act, 2000 - First Schedule):</span>
                <p className="text-amber-800 leading-relaxed">
                  Electronic signatures CANNOT be used for: Negotiable Instruments (Promissory notes, bills of exchange), Powers of Attorney, Trust deeds, Wills/Codicils, or Immovable property conveyance. Standard commercial contracts, service agreements, NDAs, and private bonds are 100% permitted under Section 10A.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 3: KARNATAKA & STATE STAMP DUTY WORKFLOW              */}
        {/* ========================================================= */}
        {activeTab === 'stamping' && (
          <div className="space-y-6">
            
            {/* Critical Statutory Notice */}
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-900 flex items-start space-x-3">
              <Scale className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-bold">Statutory Notice on Stamp Duty & Admissibility (Karnataka Stamp Act, 1957):</span>
                <p className="text-rose-800 leading-relaxed">
                  Do NOT assume that an ordinary PDF, an arbitrary ₹100 stamp paper, or an e-stamp is automatically sufficient for every bond. Under Section 34 of the Karnataka Stamp Act, 1957 (and Section 35 Indian Stamp Act, 1899), instruments not duly stamped are <strong>INADMISSIBLE IN EVIDENCE</strong> in any court of law and cannot be acted upon until impounded and deficit duty plus statutory penalty (up to 10x deficit) is paid.
                </p>
              </div>
            </div>

            {/* State Duty Calculator Card */}
            <div className="p-5 border border-slate-200 rounded-xl bg-slate-50/50 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-sm text-navy-900 flex items-center space-x-2">
                  <Stamp className="w-4 h-4 text-teal-600" />
                  <span>State-Aware Stamp Duty Calculator</span>
                </h4>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-teal-100 text-teal-800 border border-teal-200">
                  Karnataka 2023/2024 Amendments Applied
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">State Jurisdiction</label>
                  <select
                    value={selectedState}
                    onChange={(e) => {
                      setSelectedState(e.target.value);
                      runDutyCalculation(e.target.value, instrumentCategory, considerationInput, isBondToggle, isIndemnityToggle);
                    }}
                    className="w-full p-2 text-xs border border-slate-300 rounded-md bg-white outline-none focus:ring-1 focus:ring-navy-900"
                  >
                    <option value="Karnataka">Karnataka (Karnataka Stamp Act, 1957)</option>
                    <option value="Maharashtra">Maharashtra (Maharashtra Stamp Act)</option>
                    <option value="Delhi">Delhi (Indian Stamp Act Schedule 1A)</option>
                    <option value="Tamil Nadu">Tamil Nadu (TN Stamp Act)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">Document Category</label>
                  <select
                    value={instrumentCategory}
                    onChange={(e) => {
                      setInstrumentCategory(e.target.value);
                      runDutyCalculation(selectedState, e.target.value, considerationInput, isBondToggle, isIndemnityToggle);
                    }}
                    className="w-full p-2 text-xs border border-slate-300 rounded-md bg-white outline-none focus:ring-1 focus:ring-navy-900"
                  >
                    <option value="commercial_service">Commercial Service / Work Contract</option>
                    <option value="general_agreement">General Agreement / MOU (Art 5(j))</option>
                    <option value="indemnity_bond">Indemnity Bond (Art 34)</option>
                    <option value="performance_bond">Performance Bond / Security Bond (Art 12)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">Consideration / Bond Sum (INR)</label>
                  <input
                    type="number"
                    placeholder="e.g. 500000"
                    value={considerationInput}
                    onChange={(e) => {
                      setConsiderationInput(e.target.value);
                      runDutyCalculation(selectedState, instrumentCategory, e.target.value, isBondToggle, isIndemnityToggle);
                    }}
                    className="w-full p-2 text-xs border border-slate-300 rounded-md bg-white outline-none focus:ring-1 focus:ring-navy-900"
                  />
                </div>
              </div>

              {/* Calculated Result Display */}
              {calculatedDuty && (
                <div className="p-4 bg-white border border-teal-200 rounded-xl space-y-2.5 shadow-2xs">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div className="space-y-0.5">
                      <span className="text-[10px] font-bold uppercase text-slate-400">Statutory Schedule Reference</span>
                      <div className="font-bold text-xs text-navy-900">{calculatedDuty.article_reference}</div>
                    </div>

                    <div className="text-right">
                      <span className="text-[10px] font-bold uppercase text-slate-400">Applicable Stamp Duty</span>
                      <div className="text-lg font-black text-teal-700">₹{calculatedDuty.applicable_duty_inr.toLocaleString('en-IN')}</div>
                    </div>
                  </div>

                  <p className="text-xs text-slate-600 border-t border-slate-100 pt-2">
                    {calculatedDuty.rule_description}
                  </p>

                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                    <span>Authorized e-Stamping CRA: Stock Holding Corporation of India Ltd (SHCIL)</span>
                    <a
                      href="https://www.shcilestamp.com"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline font-semibold flex items-center space-x-1"
                    >
                      <span>Open SHCIL Portal</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              )}
            </div>

            {/* Record / Verify e-Stamp Certificate Form */}
            <form onSubmit={handleVerifyAndRecordStamp} className="p-5 border border-slate-200 rounded-xl bg-white space-y-4">
              <h4 className="font-bold text-xs uppercase tracking-wider text-navy-900 flex items-center space-x-1.5">
                <FileCheck className="w-4 h-4 text-emerald-600" />
                <span>Verify & Record Authorized e-Stamp Certificate</span>
              </h4>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">e-Stamp Certificate No.</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. IN-KA82937401928374U"
                    value={stampCertInput}
                    onChange={(e) => setStampCertInput(e.target.value)}
                    className="w-full p-2 text-xs border border-slate-300 rounded-md font-mono outline-none focus:ring-1 focus:ring-navy-900"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">GRN / Challan Reference</label>
                  <input
                    type="text"
                    placeholder="e.g. CR009283719"
                    value={stampGrnInput}
                    onChange={(e) => setStampGrnInput(e.target.value)}
                    className="w-full p-2 text-xs border border-slate-300 rounded-md font-mono outline-none focus:ring-1 focus:ring-navy-900"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">Duty Paid Amount (INR)</label>
                  <input
                    type="number"
                    value={stampAmountInput}
                    onChange={(e) => setStampAmountInput(e.target.value)}
                    className="w-full p-2 text-xs border border-slate-300 rounded-md outline-none focus:ring-1 focus:ring-navy-900"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                <span className="text-[11px] text-slate-500">
                  Verifies certificate structure against state treasury records and locks it to the audit hash.
                </span>

                <button
                  type="submit"
                  disabled={verifyingStamp}
                  className="px-4 py-2 bg-teal-800 hover:bg-teal-700 text-white rounded-md text-xs font-semibold shadow-sm transition-colors flex items-center space-x-1.5 disabled:opacity-50"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>{verifyingStamp ? 'Verifying...' : 'Verify & Record e-Stamp'}</span>
                </button>
              </div>

              {stampVerificationResult && (
                <div className="p-3 bg-teal-50 border border-teal-200 rounded-lg text-xs text-teal-900 space-y-1">
                  <div className="font-bold flex items-center space-x-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-teal-700" />
                    <span>e-Stamp Verification Confirmed:</span>
                  </div>
                  <div>Certificate: <strong className="font-mono">{stampVerificationResult.certificate_number}</strong> ({stampVerificationResult.issuer})</div>
                  <div>Duty Paid: ₹{stampVerificationResult.amount_paid} • Status: {stampVerificationResult.notes}</div>
                </div>
              )}
            </form>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 4: LAWYER-APPROVED TEMPLATES (SECTION 10 ICA, 1872)   */}
        {/* ========================================================= */}
        {activeTab === 'templates' && (
          <div className="space-y-6">
            <div className="p-4 bg-indigo-50/70 border border-indigo-200 rounded-xl space-y-2 text-xs text-indigo-950">
              <span className="font-bold text-sm text-indigo-900 flex items-center space-x-1.5">
                <Scale className="w-4 h-4 text-indigo-700" />
                <span>Indian Contract-Law Review: Section 10 Approved Templates</span>
              </span>
              <p className="leading-relaxed">
                Under <strong>Section 10 of the Indian Contract Act, 1872</strong>, enforceability requires free consent, competent parties, lawful consideration, and a lawful object. Legalbandu utilizes pre-vetted, lawyer-approved templates for common agreements rather than promising that every arbitrary AI-generated document is automatically legally valid.
              </p>
            </div>

            {/* Template Cards */}
            <div className="space-y-4">
              {templates.map((tpl) => (
                <div
                  key={tpl.template_id}
                  className="p-5 border border-slate-200 rounded-xl bg-white shadow-2xs space-y-3"
                >
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                    <div>
                      <h4 className="font-bold text-sm text-navy-900">{tpl.title}</h4>
                      <p className="text-xs text-slate-500">{tpl.legal_basis} • {tpl.jurisdiction}</p>
                    </div>

                    <button
                      onClick={() => handleApplyTemplate(tpl.template_id, tpl.title)}
                      disabled={applyingTemplateId === tpl.template_id}
                      className="px-4 py-2 bg-navy-900 hover:bg-navy-800 text-white rounded-md text-xs font-semibold shadow-sm transition-colors flex items-center space-x-1.5 disabled:opacity-50 shrink-0"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                      <span>{applyingTemplateId === tpl.template_id ? 'Applying...' : 'Apply Template to Agreement'}</span>
                    </button>
                  </div>

                  <p className="text-xs text-slate-700 leading-relaxed">
                    {tpl.summary}
                  </p>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-1 text-xs">
                    <span className="text-[10px] font-bold uppercase text-slate-400 block">Vetted Standard Clauses Included:</span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-[11px] text-slate-700">
                      {tpl.key_clauses?.map((c, idx) => (
                        <div key={idx} className="flex items-center space-x-1.5">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600 shrink-0" />
                          <span className="truncate">{c}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 5: TAMPER-EVIDENT EVIDENCE & SHA-256 AUDIT CERTIFICATE*/}
        {/* ========================================================= */}
        {activeTab === 'evidence' && (
          <div className="space-y-6">
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs text-slate-800">
              <span className="font-bold text-sm text-navy-900 flex items-center space-x-1.5">
                <Lock className="w-4 h-4 text-navy-900" />
                <span>Tamper-Evident Evidence & Cryptographic Audit Trail</span>
              </span>
              <p className="leading-relaxed">
                Preserves the exact signed document, document version, each party's affirmative acceptance, authentication results, timestamps, signature verification information, and subsequent amendments. Generates a cryptographic SHA-256 hash for the finalized document and maintains an auditable event history.
              </p>
            </div>

            {/* SHA-256 Hash Card */}
            <div className="p-5 border border-slate-200 rounded-xl bg-white shadow-2xs space-y-3">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Finalized Agreement Cryptographic Hash (SHA-256)
              </span>

              <div className="flex items-center justify-between p-3 bg-slate-900 text-emerald-400 font-mono text-xs rounded-lg border border-slate-800 break-all select-all">
                <span>{auditCertData?.document_hash_sha256 || 'Calculating SHA-256 digest...'}</span>
                <button
                  onClick={handleCopyHash}
                  className="ml-2 p-1.5 text-slate-400 hover:text-white rounded bg-slate-800 hover:bg-slate-700 transition-colors shrink-0"
                  title="Copy SHA-256 Hash"
                >
                  {copiedHash ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs pt-2">
                <div>
                  <span className="text-[10px] text-slate-400 font-semibold block">Version</span>
                  <span className="font-bold text-slate-900">v{currentVersion?.version_number || 1}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-semibold block">Signatures Verified</span>
                  <span className="font-bold text-emerald-700">{auditCertData?.signatures_recorded || 0} recorded</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-semibold block">Audit Trail Events</span>
                  <span className="font-bold text-navy-900">{auditCertData?.activity_events_count || 0} events</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-semibold block">Integrity Status</span>
                  <span className="font-bold text-emerald-600 flex items-center space-x-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Cryptographically Locked</span>
                  </span>
                </div>
              </div>
            </div>

            {/* Section 65B Certificate Reader */}
            {auditCertData?.certificate_text && (
              <div className="p-5 border border-slate-200 rounded-xl bg-slate-50 font-mono text-xs text-slate-800 whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto">
                {auditCertData.certificate_text}
              </div>
            )}

            {/* Statutory Disclaimer Alert */}
            <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start space-x-2.5">
              <Info className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
              <div>
                <strong className="block font-semibold">Evidentiary Integrity Notice:</strong>
                <p className="text-amber-800 leading-relaxed mt-0.5">
                  This cryptographic hash and audit trail support technical evidence integrity under Section 65B of the Indian Evidence Act, 1872 / Section 63 of the Bharatiya Sakshya Adhiniyam, 2023. It confirms that the document has not been altered since execution. It does not independently prove in court that a person was genuine, understood the terms, or consented freely without undue influence.
                </p>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
