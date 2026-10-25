import React, { useState } from 'react';
import { 
  FileText, 
  Upload, 
  ShieldAlert, 
  Sparkles, 
  Scale, 
  Check, 
  FileCheck
} from 'lucide-react';

const BOND_TYPES = [
  "Indemnity Bond",
  "Surety Bond",
  "Performance Bond",
  "Stamp Paper Agreement",
  "Security Deposit Bond",
  "Promissory Note",
  "Fidelity Bond",
  "Service Agreement Bond"
];

export default function BondUploadWidget({ onUploadBond, scanning }) {
  const [activeMode, setActiveMode] = useState('upload'); // 'upload' | 'paste'
  const [bondType, setBondType] = useState('Indemnity Bond');
  const [selectedFile, setSelectedFile] = useState(null);
  const [pastedText, setPastedText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();

    if (activeMode === 'upload') {
      if (!selectedFile) {
        alert('Please select a PDF or text document of the bond.');
        return;
      }
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('bond_type', bondType);
      onUploadBond(formData);
    } else {
      if (!pastedText.trim()) {
        alert('Please paste the bond clauses or stamp paper text.');
        return;
      }
      const formData = new FormData();
      formData.append('content', pastedText.trim());
      formData.append('bond_type', bondType);
      onUploadBond(formData);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
      {/* Header and Mode Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div>
          <h4 className="text-sm font-bold text-navy-900 flex items-center space-x-2">
            <Scale className="w-4 h-4 text-amber-600" />
            <span>Upload Existing Bond & AI Detector Verification</span>
          </h4>
          <p className="text-xs text-slate-500 mt-0.5">
            Upload legal bonds or e-stamps. Our multi-vector detector scans for synthetic AI generation and alerts immediately if detected.
          </p>
        </div>

        <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-lg self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setActiveMode('upload')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center space-x-1.5 ${
              activeMode === 'upload' 
                ? 'bg-white text-navy-900 shadow-sm' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload PDF/File</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveMode('paste')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center space-x-1.5 ${
              activeMode === 'paste' 
                ? 'bg-white text-navy-900 shadow-sm' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Paste Bond Text</span>
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Bond Type Selector */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-[11px] font-bold text-slate-700 mb-1">
              Select Bond / Agreement Category:
            </label>
            <select
              value={bondType}
              onChange={(e) => setBondType(e.target.value)}
              className="w-full p-2 text-xs border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-navy-900 bg-white"
            >
              {BOND_TYPES.map((bt) => (
                <option key={bt} value={bt}>{bt}</option>
              ))}
            </select>
          </div>

          <div className="p-2.5 bg-blue-50/70 border border-blue-200 rounded-lg text-[11px] text-blue-900 flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-blue-600 shrink-0" />
            <span>
              <b>Real-time AI Detector:</b> Scans for LLM signatures, burstiness, and Indian statutory markers.
            </span>
          </div>
        </div>

        {/* Upload Mode */}
        {activeMode === 'upload' && (
          <div className="border-2 border-dashed border-slate-200 hover:border-amber-400 rounded-xl p-5 text-center transition-colors bg-slate-50/50">
            <input
              id="bond-file-input"
              type="file"
              accept=".pdf,.txt,.docx,.doc"
              className="hidden"
              onChange={(e) => setSelectedFile(e.target.files[0] || null)}
            />
            <label 
              htmlFor="bond-file-input" 
              className="cursor-pointer flex flex-col items-center justify-center space-y-2"
            >
              <div className="w-10 h-10 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center">
                <FileCheck className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xs font-bold text-navy-900 hover:underline">
                  {selectedFile ? selectedFile.name : 'Select Bond Document (.PDF, .DOCX, .TXT)'}
                </span>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  PDF legal bonds with digital e-stamps or plain text contracts (Max 25MB)
                </p>
              </div>
            </label>

            {selectedFile && (
              <div className="mt-3 flex items-center justify-center space-x-3 text-xs">
                <span className="text-emerald-700 font-semibold flex items-center space-x-1">
                  <Check className="w-3.5 h-3.5" />
                  <span>Document Selected ({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                </span>
                <button
                  type="button"
                  onClick={() => setSelectedFile(null)}
                  className="text-red-600 hover:underline text-[11px]"
                >
                  Change
                </button>
              </div>
            )}
          </div>
        )}

        {/* Paste Mode */}
        {activeMode === 'paste' && (
          <div>
            <label className="block text-[11px] font-bold text-slate-700 mb-1">
              Paste Legal Bond Clauses / Text:
            </label>
            <textarea
              rows={4}
              placeholder="Paste bond recitals, indemnity clauses, penal sum, or draft stamp text here..."
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              className="w-full p-3 text-xs font-mono border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-navy-900"
            />
          </div>
        )}

        {/* Submit */}
        <div className="flex items-center justify-end space-x-3 pt-2">
          <button
            type="submit"
            disabled={scanning || (activeMode === 'upload' && !selectedFile) || (activeMode === 'paste' && !pastedText.trim())}
            className="px-5 py-2.5 bg-gradient-to-r from-amber-600 to-navy-900 hover:from-amber-700 hover:to-navy-950 text-white text-xs font-bold rounded-lg shadow-sm flex items-center space-x-2 transition-all disabled:opacity-50"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-amber-200" />
            <span>{scanning ? 'Scanning Document & Running AI Detector...' : 'Upload & Run AI Detector'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
