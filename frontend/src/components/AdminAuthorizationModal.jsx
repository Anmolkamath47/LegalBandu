import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  ShieldCheck,
  AlertTriangle,
  FileText,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Clock,
  Building2,
  Lock,
  X,
  RefreshCw,
  Info,
} from 'lucide-react';

const STATUS_CONFIG = {
  NOT_ASSESSED: { label: 'Not Assessed', bg: 'bg-slate-100 text-slate-700 border-slate-300' },
  ELIGIBILITY_REVIEW_REQUIRED: { label: 'Eligibility Review Required', bg: 'bg-amber-100 text-amber-800 border-amber-300' },
  APPLICATION_REQUIRED: { label: 'Application Required', bg: 'bg-blue-100 text-blue-800 border-blue-300' },
  APPLICATION_SUBMITTED: { label: 'Application Submitted', bg: 'bg-indigo-100 text-indigo-800 border-indigo-300' },
  APPROVED_PENDING_INTEGRATION: { label: 'Approved (Pending Integration)', bg: 'bg-cyan-100 text-cyan-800 border-cyan-300' },
  PRODUCTION_VERIFIED: { label: 'Production Verified (Authorized)', bg: 'bg-emerald-100 text-emerald-800 border-emerald-300' },
  EXPIRED: { label: 'Expired (Renewal Due)', bg: 'bg-rose-100 text-rose-800 border-rose-300' },
  SUSPENDED: { label: 'Suspended by Authority', bg: 'bg-red-100 text-red-800 border-red-300' },
  REJECTED: { label: 'Application Rejected', bg: 'bg-slate-200 text-slate-800 border-slate-400' },
};

export default function AdminAuthorizationModal({ isOpen, onClose }) {
  const [providers, setProviders] = useState([]);
  const [exclusions, setExclusions] = useState([]);
  const [activeTab, setActiveTab] = useState('providers');
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [updating, setUpdating] = useState(false);

  // Edit form state
  const [editStatus, setEditStatus] = useState('');
  const [editRef, setEditRef] = useState('');
  const [editEvidenceNote, setEditEvidenceNote] = useState('');

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen]);

  async function loadData() {
    setLoading(true);
    setErrorMsg('');
    try {
      const [provList, exclList] = await Promise.all([
        api.getAuthorizationProviders(),
        api.getStatutoryExclusions(),
      ]);
      setProviders(provList);
      setExclusions(exclList);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load authorization register.');
    } finally {
      setLoading(false);
    }
  }

  function handleSelectProvider(prov) {
    setSelectedProvider(prov);
    setEditStatus(prov.authorization_status);
    setEditRef(prov.approval_reference || '');
    setEditEvidenceNote(prov.supporting_evidence?.verification_note || '');
  }

  async function handleSaveProviderUpdate(e) {
    e.preventDefault();
    if (!selectedProvider) return;
    if (editStatus === 'PRODUCTION_VERIFIED' && !editRef.trim()) {
      alert('Production Acceptance Rule: Cannot mark PRODUCTION_VERIFIED without an official government approval/contract reference.');
      return;
    }

    setUpdating(true);
    try {
      const payload = {
        authorization_status: editStatus,
        approval_reference: editRef.trim() || null,
        supporting_evidence: {
          ...selectedProvider.supporting_evidence,
          verification_note: editEvidenceNote.trim(),
          updated_at: new Date().toISOString(),
        },
      };

      const updated = await api.updateAuthorizationProvider(selectedProvider.provider_code, payload);
      setProviders((prev) => prev.map((p) => (p.provider_code === updated.provider_code ? updated : p)));
      setSelectedProvider(updated);
      alert(`Integration status for ${updated.name} updated successfully.`);
    } catch (err) {
      alert(err.message || 'Failed to update provider status.');
    } finally {
      setUpdating(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
      <div 
        className="w-full max-w-4xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-navy-900 text-white rounded-lg shadow-sm">
              <ShieldCheck className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h2 className="text-base font-bold text-navy-900 flex items-center space-x-2">
                <span>Government Authorization & Compliance Register</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider bg-blue-100 text-blue-800 border border-blue-200">
                  Administrator View
                </span>
              </h2>
              <p className="text-xs text-slate-500">
                Statutory licensing, e-stamping CRA onboarding, IT Act First Schedule exclusions, and production status.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-200/50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Regulatory Disclosure Banner */}
        <div className="px-6 py-3 bg-amber-50 border-b border-amber-200 flex items-start space-x-3 text-xs text-amber-900">
          <Info className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">MANDATORY STATUTORY NOTICE: </span>
            Legalbandu operates as a Technology Intermediary under Section 2(1)(w) of the IT Act, 2000. Sandbox access is <b>NOT</b> government authorization. A provider's licensing does not authorize Legalbandu to represent itself as a government agency or issuer. Only genuine, verified production credentials permit live processing.
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 bg-slate-100/50 px-6">
          <button
            onClick={() => { setActiveTab('providers'); setSelectedProvider(null); }}
            className={`py-3 px-4 text-xs font-bold border-b-2 transition-colors flex items-center space-x-1.5 ${
              activeTab === 'providers'
                ? 'border-navy-900 text-navy-900 bg-white'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Building2 className="w-3.5 h-3.5" />
            <span>Authorized Providers Register ({providers.length})</span>
          </button>
          <button
            onClick={() => { setActiveTab('exclusions'); setSelectedProvider(null); }}
            className={`py-3 px-4 text-xs font-bold border-b-2 transition-colors flex items-center space-x-1.5 ${
              activeTab === 'exclusions'
                ? 'border-navy-900 text-navy-900 bg-white'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Lock className="w-3.5 h-3.5" />
            <span>IT Act Statutory Exclusions ({exclusions.length})</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {loading ? (
            <div className="py-12 text-center text-slate-400 flex flex-col items-center justify-center space-y-2">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
              <span className="text-xs">Loading compliance register...</span>
            </div>
          ) : errorMsg ? (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
              {errorMsg}
            </div>
          ) : activeTab === 'providers' ? (
            <div className="space-y-4">
              {selectedProvider ? (
                /* Detail / Update View */
                <div className="space-y-4 bg-slate-50 p-5 rounded-xl border border-slate-200">
                  <div className="flex justify-between items-start">
                    <div>
                      <button
                        onClick={() => setSelectedProvider(null)}
                        className="text-xs text-blue-600 hover:underline mb-1 font-semibold"
                      >
                        ← Back to Provider List
                      </button>
                      <h3 className="text-sm font-bold text-navy-900">{selectedProvider.name}</h3>
                      <p className="text-xs text-slate-500">{selectedProvider.authority_type}</p>
                    </div>
                    <span className={`text-[10px] px-2.5 py-1 rounded-full font-bold border ${STATUS_CONFIG[selectedProvider.authorization_status]?.bg}`}>
                      {STATUS_CONFIG[selectedProvider.authorization_status]?.label}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-1.5">
                      <div className="font-semibold text-slate-700">Statutory Authority / License:</div>
                      <div className="text-slate-600">{selectedProvider.authorization_type}</div>
                      <div className="font-semibold text-slate-700 pt-1">Official Portal:</div>
                      <a href={selectedProvider.official_website} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline flex items-center space-x-1">
                        <span>{selectedProvider.official_website}</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>

                    <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-1.5">
                      <div className="font-semibold text-slate-700">Coverage & Restrictions:</div>
                      <div className="text-slate-600">{selectedProvider.geographic_coverage}</div>
                      <div className="text-[11px] text-amber-800 bg-amber-50 p-2 rounded border border-amber-200 mt-1">
                        {selectedProvider.restrictions || 'No active restrictions recorded.'}
                      </div>
                    </div>
                  </div>

                  {/* Update Form */}
                  <form onSubmit={handleSaveProviderUpdate} className="bg-white p-4 rounded-lg border border-slate-200 space-y-3">
                    <h4 className="text-xs font-bold text-slate-800">Update Onboarding & Production Status</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Authorization Status
                        </label>
                        <select
                          value={editStatus}
                          onChange={(e) => setEditStatus(e.target.value)}
                          className="w-full text-xs p-2 border border-slate-300 rounded-md bg-white font-medium outline-none focus:border-navy-900"
                        >
                          {Object.keys(STATUS_CONFIG).map((st) => (
                            <option key={st} value={st}>{STATUS_CONFIG[st].label}</option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Official Approval / Contract Ref #
                        </label>
                        <input
                          type="text"
                          value={editRef}
                          onChange={(e) => setEditRef(e.target.value)}
                          placeholder="e.g. NESL-DDE-2026-APP-8841"
                          className="w-full text-xs p-2 border border-slate-300 rounded-md outline-none focus:border-navy-900"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Audit & Verification Evidence Note
                      </label>
                      <textarea
                        rows={2}
                        value={editEvidenceNote}
                        onChange={(e) => setEditEvidenceNote(e.target.value)}
                        placeholder="Document the genuine agreement date, security audit reference, or official communication..."
                        className="w-full text-xs p-2 border border-slate-300 rounded-md outline-none focus:border-navy-900"
                      />
                    </div>

                    <div className="flex justify-end space-x-2 pt-2">
                      <button
                        type="button"
                        onClick={() => setSelectedProvider(null)}
                        className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-md"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={updating}
                        className="px-4 py-1.5 bg-navy-900 text-white text-xs font-bold rounded-md hover:bg-navy-800 disabled:opacity-50"
                      >
                        {updating ? 'Saving...' : 'Save Authorization Record'}
                      </button>
                    </div>
                  </form>
                </div>
              ) : (
                /* Provider List */
                <div className="space-y-3">
                  {providers.map((prov) => {
                    const st = STATUS_CONFIG[prov.authorization_status] || STATUS_CONFIG.NOT_ASSESSED;
                    return (
                      <div
                        key={prov.provider_code}
                        onClick={() => handleSelectProvider(prov)}
                        className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm hover:border-blue-400 hover:shadow-md transition-all cursor-pointer flex flex-col md:flex-row justify-between items-start md:items-center gap-3"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2">
                            <span className="font-bold text-xs text-navy-900">{prov.name}</span>
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                              {prov.provider_code}
                            </span>
                          </div>
                          <p className="text-xs text-slate-500">{prov.authority_type}</p>
                          <div className="text-[11px] text-slate-400 flex items-center space-x-3 pt-0.5">
                            <span>Coverage: <b>{prov.geographic_coverage}</b></span>
                            <span>•</span>
                            <span>Eligible: <b>{prov.eligible_legal_entity}</b></span>
                          </div>
                        </div>

                        <div className="flex items-center space-x-3 shrink-0">
                          <span className={`text-[10px] px-2.5 py-1 rounded-full font-bold border ${st.bg}`}>
                            {st.label}
                          </span>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleSelectProvider(prov); }}
                            className="px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-md border border-slate-300"
                          >
                            Inspect & Audit
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            /* Exclusions Tab */
            <div className="space-y-3">
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800">
                <span className="font-bold">Information Technology Act, 2000 — First Schedule [Section 1(4)]: </span>
                Electronic signatures and electronic contracts have <b>NO statutory validity</b> for the following instruments under Indian law. Legalbandu strictly blocks electronic execution for any document classified under these categories.
              </div>

              {exclusions.map((excl) => (
                <div key={excl.exclusion_code} className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm space-y-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-bold text-xs text-red-900 flex items-center space-x-2">
                        <Lock className="w-3.5 h-3.5 text-red-600" />
                        <span>{excl.instrument_name}</span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">{excl.statutory_source} — <code>{excl.section_reference}</code></p>
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-rose-100 text-rose-800 border border-rose-300">
                      Physical Paper Mandatory
                    </span>
                  </div>

                  <div className="p-2.5 bg-slate-50 rounded-lg text-xs text-slate-700 border border-slate-200 space-y-1">
                    <div><span className="font-semibold text-slate-900">Required Physical Formalities:</span> {excl.required_physical_formalities}</div>
                    <div><span className="font-semibold text-slate-900">Statutory Exceptions:</span> <span className="text-slate-600">{excl.statutory_exceptions}</span></div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex justify-between items-center text-xs text-slate-500">
          <div>Legalbandu Compliance Audit Engine • Version 2.0</div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-800 text-xs font-semibold rounded-md"
          >
            Close Register
          </button>
        </div>
      </div>
    </div>
  );
}
