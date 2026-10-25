import React from 'react';
import { 
  AlertTriangle, 
  ShieldAlert, 
  X, 
  ArrowRight, 
  Scale, 
  FileCheck2
} from 'lucide-react';

export default function AIDetectorAlertModal({ 
  isOpen, 
  onClose, 
  bond, 
  onApplyToAgreement, 
  applying 
}) {
  if (!isOpen || !bond) return null;

  const scorePercent = Math.round((bond.ai_detection_score || 0) * 100);
  const markers = bond.ai_markers || [];
  const terms = bond.extracted_terms || {};

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn">
      <div 
        className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full border border-red-200 overflow-hidden transform transition-all animate-scaleUp"
        role="dialog"
        aria-modal="true"
        aria-labelledby="ai-alert-title"
      >
        {/* Top Warning Banner */}
        <div className="bg-gradient-to-r from-red-600 via-rose-600 to-amber-600 px-6 py-5 text-white flex items-start justify-between">
          <div className="flex items-start space-x-3.5">
            <div className="p-2.5 bg-white/20 rounded-xl backdrop-blur-md shadow-inner animate-pulse">
              <ShieldAlert className="w-7 h-7 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase tracking-wider bg-white text-red-700 shadow-sm">
                  CRITICAL ALERT
                </span>
                <span className="text-xs text-red-100 font-mono">
                  AI DETECTOR SCAN
                </span>
              </div>
              <h2 id="ai-alert-title" className="text-lg font-bold text-white mt-1">
                AI-Generated Legal Bond Detected!
              </h2>
              <p className="text-xs text-red-100 mt-0.5">
                The document "{bond.filename || bond.bond_type}" contains synthetic LLM boilerplate patterns.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white/80 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors"
            title="Close Alert"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
          {/* AI Probability Gauge */}
          <div className="p-4 bg-red-50/80 border border-red-200 rounded-xl">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-red-900 flex items-center space-x-1.5">
                <AlertTriangle className="w-4 h-4 text-red-600" />
                <span>Synthetic Content Probability</span>
              </span>
              <span className="text-sm font-extrabold font-mono text-red-700">
                {scorePercent}% AI Likely
              </span>
            </div>
            {/* Progress bar */}
            <div className="w-full bg-red-200 rounded-full h-3 overflow-hidden">
              <div 
                className="bg-gradient-to-r from-amber-500 to-red-600 h-full rounded-full transition-all duration-700 ease-out"
                style={{ width: `${Math.min(100, Math.max(10, scorePercent))}%` }}
              />
            </div>
            <div className="flex justify-between items-center text-[10px] text-slate-500 mt-1.5">
              <span>Human Drafted (0%)</span>
              <span className="font-semibold text-red-600 font-mono">{bond.ai_verdict}</span>
              <span>100% Synthetic</span>
            </div>
          </div>

          {/* Legal Enforceability Risk Advisory */}
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs space-y-2">
            <div className="flex items-center space-x-2 text-amber-900 font-bold">
              <Scale className="w-4 h-4 text-amber-700 shrink-0" />
              <span>Enforceability Risk & Statutory Notice</span>
            </div>
            <p className="text-amber-800 leading-relaxed text-[11px]">
              AI models (like ChatGPT/Claude) frequently generate generic clauses with phrases like <i>"laws of applicable jurisdiction"</i> and lack mandatory Indian Stamp Act citations, consideration clauses, or specific judicial recourse. Executing synthetic bonds without localized review can jeopardize evidentiary value in court.
            </p>
          </div>

          {/* Detected AI Hallmarks & Markers */}
          {markers.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center justify-between">
                <span>Flagged AI Markers ({markers.length})</span>
                <span className="text-[10px] font-normal text-slate-500 lowercase">detected in text</span>
              </h3>
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {markers.map((m, idx) => (
                  <div key={idx} className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-800 flex items-center space-x-1.5">
                        <span className={`w-2 h-2 rounded-full ${m.severity === 'high' ? 'bg-red-500' : 'bg-amber-500'}`} />
                        <span>{m.description || m.marker_type}</span>
                      </span>
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${
                        m.severity === 'high' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                      }`}>
                        {m.severity} severity
                      </span>
                    </div>
                    {m.excerpt && (
                      <p className="font-mono text-[11px] text-slate-600 bg-white p-1.5 rounded border border-slate-200 italic">
                        "{m.excerpt}"
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Extracted Key Terms from Bond */}
          {terms && Object.keys(terms).length > 0 && (
            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
              <span className="font-bold text-slate-900 flex items-center space-x-1.5">
                <FileCheck2 className="w-4 h-4 text-blue-600" />
                <span>Extracted Bond Covenants (Ready for Agreement)</span>
              </span>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="bg-white p-2 rounded border border-slate-200">
                  <span className="text-slate-400 block text-[10px] font-semibold uppercase">Bond Type</span>
                  <span className="font-bold text-slate-800">{terms.bond_type || 'Indemnity Bond'}</span>
                </div>
                <div className="bg-white p-2 rounded border border-slate-200">
                  <span className="text-slate-400 block text-[10px] font-semibold uppercase">Obligor</span>
                  <span className="font-bold text-slate-800">{terms.obligor || 'Party Executing Bond'}</span>
                </div>
                <div className="bg-white p-2 rounded border border-slate-200">
                  <span className="text-slate-400 block text-[10px] font-semibold uppercase">Penalty / Bond Sum</span>
                  <span className="font-bold text-emerald-700">{terms.bond_amount ? `₹${terms.bond_amount}` : 'As specified'}</span>
                </div>
                <div className="bg-white p-2 rounded border border-slate-200">
                  <span className="text-slate-400 block text-[10px] font-semibold uppercase">Stamp Reference</span>
                  <span className="font-mono text-slate-700">{terms.stamp_reference || 'Unregistered'}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer Actions */}
        <div className="bg-slate-50 px-6 py-4 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3">
          <button
            onClick={onClose}
            className="w-full sm:w-auto px-4 py-2 border border-slate-300 text-slate-700 hover:bg-slate-100 text-xs font-semibold rounded-lg transition-colors"
          >
            Acknowledge & Close
          </button>
          
          <button
            onClick={() => onApplyToAgreement(bond.id)}
            disabled={applying}
            className="w-full sm:w-auto px-5 py-2.5 bg-gradient-to-r from-blue-700 to-navy-900 hover:from-blue-800 hover:to-navy-950 text-white text-xs font-bold rounded-lg shadow-md hover:shadow-lg transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            <span>{applying ? 'Applying Terms...' : 'Convert Bond into Deal Agreement'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
