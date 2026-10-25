import React from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  ArrowRight, 
  GitCommit, 
  Download, 
  AlertTriangle,
  Scale,
  Users,
  Mic,
  CheckCircle2,
  Clock
} from 'lucide-react';

export default function LandingPage({ onOpenAuth, onOpenNewDeal }) {
  const { user } = useAuth();

  function handlePrimaryCTA() {
    if (user) {
      onOpenNewDeal();
    } else {
      onOpenAuth('signup');
    }
  }

  function handleSecondaryCTA() {
    document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' });
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between">
      {/* Hero Section */}
      <section className="relative pt-12 pb-20 md:pt-20 md:pb-28 overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          
          <div className="text-center max-w-3xl mx-auto">
            {/* Tagline Badge */}
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-200/70 border border-slate-300 text-slate-800 text-xs font-semibold uppercase tracking-wider mb-6">
              <Scale className="w-3.5 h-3.5 text-navy-900" />
              <span>Legalbandu — From Handshake to Contract</span>
            </div>

            <h1 className="text-3xl sm:text-5xl font-extrabold text-navy-900 tracking-tight leading-tight">
              Transform Informal Conversations Into Confirmed Business Agreements
            </h1>

            <p className="mt-5 text-base sm:text-lg text-slate-600 leading-relaxed max-w-2xl mx-auto">
              People frequently agree on deals over WhatsApp, emails, and phone calls. 
              Legalbandu extracts the agreed terms, highlights missing deadlines and price ambiguities, 
              and creates a version-controlled document confirmed by both parties.
            </p>

            {/* CTAs */}
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center space-y-3 sm:space-y-0 sm:space-x-4">
              <button
                id="btn-hero-create-deal"
                onClick={handlePrimaryCTA}
                className="w-full sm:w-auto px-6 py-3 bg-navy-900 hover:bg-navy-800 text-white font-semibold text-sm rounded-lg shadow-sm transition-all flex items-center justify-center space-x-2"
              >
                <span>Create a Deal</span>
                <ArrowRight className="w-4 h-4" />
              </button>
              
              <button
                id="btn-hero-how-it-works"
                onClick={handleSecondaryCTA}
                className="w-full sm:w-auto px-6 py-3 bg-white hover:bg-slate-100 text-slate-800 border border-slate-300 font-semibold text-sm rounded-lg shadow-sm transition-colors"
              >
                How It Works
              </button>
            </div>
          </div>

          {/* Restrained Product Interface Preview (The Painter Scenario) */}
          <div className="mt-14 max-w-4xl mx-auto">
            <div className="document-paper rounded-xl p-5 sm:p-8 bg-white border border-slate-200 shadow-md">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-2">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 rounded bg-navy-900 text-white flex items-center justify-center font-bold text-xs">
                    LB
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-navy-900">Retail Shop Renovation & Painting</h3>
                    <p className="text-[11px] text-slate-500">Ref: LB-7F4B92 | Bilateral Agreement</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="px-2.5 py-1 rounded bg-amber-50 border border-amber-200 text-amber-800 font-semibold text-[11px]">
                    Amendment Proposed (Revision v2)
                  </span>
                </div>
              </div>

              {/* Side-by-Side Comparison Mockup */}
              <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-2">
                    Original Confirmed Agreement (v1)
                  </span>
                  <div className="space-y-2 text-xs text-slate-700">
                    <p><span className="font-semibold text-slate-900">Total Price:</span> ₹25,000 INR</p>
                    <p><span className="font-semibold text-slate-900">Completion Deadline:</span> 30 October 2026</p>
                    <p><span className="font-semibold text-slate-900">Scope:</span> Wall priming and 2 coats painting</p>
                  </div>
                  <div className="mt-3 pt-2 border-t border-slate-200 flex items-center space-x-1.5 text-[11px] text-emerald-700">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Mutually Confirmed on 20 Oct</span>
                  </div>
                </div>

                <div className="p-4 bg-blue-50/50 border border-blue-200 rounded-lg">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700 block mb-2">
                    Proposed Amendment (v2 Under Review)
                  </span>
                  <div className="space-y-2 text-xs text-slate-700">
                    <p>
                      <span className="font-semibold text-slate-900">Total Price:</span>{' '}
                      <span className="line-through text-slate-400">₹25,000</span>{' '}
                      <span className="font-bold text-blue-800">₹28,000 INR (+₹3,000)</span>
                    </p>
                    <p>
                      <span className="font-semibold text-slate-900">Completion Deadline:</span>{' '}
                      <span className="line-through text-slate-400">30 Oct</span>{' '}
                      <span className="font-bold text-blue-800">01 Nov 2026 (+2 days)</span>
                    </p>
                    <p><span className="font-semibold text-slate-900">Reason:</span> High ceiling plaster prep requested</p>
                  </div>
                  <div className="mt-3 pt-2 border-t border-blue-100 flex items-center space-x-1.5 text-[11px] text-amber-700">
                    <Clock className="w-3.5 h-3.5" />
                    <span>Awaiting Counterparty Approval</span>
                  </div>
                </div>
              </div>

              {/* Audit seal preview */}
              <div className="mt-5 pt-3 border-t border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center text-[11px] text-slate-500 gap-2">
                <span className="flex items-center space-x-1 font-mono text-[10px]">
                  <GitCommit className="w-3.5 h-3.5 text-slate-400" />
                  <span>SHA-256 Link: 8f9b...3c1a → 4e7d...9a2e</span>
                </span>
                <span className="text-slate-400">Tamper-evident version chain intact</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-16 bg-white border-y border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 className="text-2xl font-bold text-navy-900">How Legalbandu Works</h2>
            <p className="mt-2 text-sm text-slate-600">
              A transparent, four-stage workflow from informal messages to a mutually confirmed document.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="p-5 rounded-lg border border-slate-200 bg-slate-50">
              <div className="w-9 h-9 rounded-md bg-navy-900 text-white flex items-center justify-center font-bold text-sm mb-3">
                1
              </div>
              <h3 className="text-sm font-bold text-navy-900">Create Room & Invite</h3>
              <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
                Set up a private deal room and generate a cryptographically secured invitation token for your business partner.
              </p>
            </div>

            <div className="p-5 rounded-lg border border-slate-200 bg-slate-50">
              <div className="w-9 h-9 rounded-md bg-navy-900 text-white flex items-center justify-center font-bold text-sm mb-3">
                2
              </div>
              <h3 className="text-sm font-bold text-navy-900">Import & AI Extract</h3>
              <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
                Paste conversation text or upload chat exports. Google Gemini extracts prices, scopes, deadlines, and flags missing or conflicting terms.
              </p>
            </div>

            <div className="p-5 rounded-lg border border-slate-200 bg-slate-50">
              <div className="w-9 h-9 rounded-md bg-navy-900 text-white flex items-center justify-center font-bold text-sm mb-3">
                3
              </div>
              <h3 className="text-sm font-bold text-navy-900">Clarify & Draft</h3>
              <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
                Resolve unanswered questions, review supporting quotes, and generate an editable plain-language agreement.
              </p>
            </div>

            <div className="p-5 rounded-lg border border-slate-200 bg-slate-50">
              <div className="w-9 h-9 rounded-md bg-navy-900 text-white flex items-center justify-center font-bold text-sm mb-3">
                4
              </div>
              <h3 className="text-sm font-bold text-navy-900">Bilateral Confirmation</h3>
              <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
                Both parties review and confirm the identical version. Substantive amendments create new revisions and reset approvals.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Core Platform Capabilities */}
      <section className="py-16 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 className="text-2xl font-bold text-navy-900">Built for Authentic Business Protection</h2>
            <p className="mt-2 text-sm text-slate-600">
              Every feature is built around genuine two-party transparency and verifiable records.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 bg-white rounded-lg border border-slate-200 shadow-sm">
              <div className="w-8 h-8 rounded bg-blue-100 text-blue-700 flex items-center justify-center mb-3">
                <Mic className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-navy-900">1. Call Recording to Agreement</h3>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                Record phone calls with live mic or upload audio recordings (.mp3, .wav, .m4a, .webm). 
                AI transcribes dialogue turns and extracts scope, pricing, and deadlines directly into agreement clauses.
              </p>
            </div>

            <div className="p-6 bg-white rounded-lg border border-slate-200 shadow-sm">
              <div className="w-8 h-8 rounded bg-amber-100 text-amber-700 flex items-center justify-center mb-3">
                <Scale className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-navy-900">2. Bond Upload & AI Detector</h3>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                Upload indemnity bonds, surety deeds, or e-stamps. Multi-vector algorithmic scanner instantly flags ChatGPT/synthetic AI text with immediate alerts and converts covenants into mutual contracts.
              </p>
            </div>

            <div className="p-6 bg-white rounded-lg border border-slate-200 shadow-sm">
              <div className="w-8 h-8 rounded bg-blue-100 text-blue-700 flex items-center justify-center mb-3">
                <Users className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-navy-900">True Bilateral Approval</h3>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                An agreement becomes mutually confirmed only when both authenticated participants approve the exact same version. Neither party can confirm on behalf of the other.
              </p>
            </div>

            <div className="p-6 bg-white rounded-lg border border-slate-200 shadow-sm">
              <div className="w-8 h-8 rounded bg-emerald-100 text-emerald-700 flex items-center justify-center mb-3">
                <GitCommit className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-navy-900">Tamper-Evident SHA-256 Audit Trail</h3>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                Every event, amendment, and approval is cryptographically chained using SHA-256 hashes. You can run instant verification on the stored chain at any time.
              </p>
            </div>

            <div className="p-6 bg-white rounded-lg border border-slate-200 shadow-sm md:col-span-2">
              <div className="w-8 h-8 rounded bg-slate-100 text-slate-700 flex items-center justify-center mb-3">
                <Download className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-navy-900">ReportLab Legal PDF Export</h3>
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                Download cleanly formatted, plain-language PDF documents complete with party identification, clause breakdown, timestamped approval stamps, and cryptographic verification seals.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Legal & Privacy Disclaimer Section */}
      <section className="py-12 bg-white border-t border-slate-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center space-x-2 text-amber-700 font-semibold text-xs mb-2">
            <AlertTriangle className="w-4 h-4" />
            <span>Important Legal Notice</span>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">
            Legalbandu is a business productivity and agreement documentation tool. 
            AI-assisted document generation organizes statements made by participants into readable contracts. 
            Legalbandu does not provide formal legal advice, guarantee legal enforceability in specific jurisdictions, 
            or replace qualified legal representation.
          </p>
        </div>
      </section>

      {/* Professional Footer */}
      <footer className="bg-navy-950 text-slate-400 py-10 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row justify-between items-center space-y-4 sm:space-y-0">
            <div className="flex items-center space-x-2.5">
              <div className="w-7 h-7 rounded bg-blue-600 text-white flex items-center justify-center font-bold text-xs">
                LB
              </div>
              <div>
                <span className="text-sm font-bold text-white block">Legalbandu</span>
                <span className="text-[10px] text-slate-400 block">From Handshake to Contract</span>
              </div>
            </div>

            <div className="flex items-center space-x-6 text-xs">
              <span className="text-slate-400 hover:text-white cursor-pointer">About</span>
              <span className="text-slate-400 hover:text-white cursor-pointer">Privacy Policy</span>
              <span className="text-slate-400 hover:text-white cursor-pointer">Terms of Service</span>
              <span className="text-slate-400 hover:text-white cursor-pointer">Contact Support</span>
            </div>
          </div>

          <div className="mt-6 pt-6 border-t border-slate-900 text-center text-[11px] text-slate-500">
            &copy; {new Date().getFullYear()} Legalbandu. Built with genuine two-party transparency.
          </div>
        </div>
      </footer>
    </div>
  );
}
