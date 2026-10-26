import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import {
  HelpCircle,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileText,
  ChevronDown,
  ChevronUp,
  Save,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  MessageSquare,
  Scale,
  RefreshCw,
  Info,
} from 'lucide-react';

export default function AgreementAssistancePanel({ dealId, currentVersion, onDraftUpdated }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [savingTopicId, setSavingTopicId] = useState(null);
  const [applyingDraft, setApplyingDraft] = useState(false);
  const [initializingTpl, setInitializingTpl] = useState(false);
  const [expandedTopicId, setExpandedTopicId] = useState(null);
  const [activeFilter, setActiveFilter] = useState('all'); // 'all' | 'pending' | 'discussed'

  // Local editing buffer for topics: { [topicId]: { answers: {...}, notes: '...', status: '...' } }
  const [formBuffer, setFormBuffer] = useState({});

  const loadAssistance = useCallback(async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const data = await api.getAgreementAssistance(dealId);
      setReport(data);

      // Initialize buffer from loaded answers
      const buf = {};
      data.topics.forEach((t) => {
        buf[t.topic_id] = {
          answers: { ...(t.answers || {}) },
          notes: t.notes || '',
          status: t.status || 'pending',
        };
      });
      setFormBuffer(buf);

      // Auto-expand first incomplete topic if none expanded
      if (!expandedTopicId) {
        const firstIncomplete = data.topics.find((t) => !t.is_complete);
        if (firstIncomplete) {
          setExpandedTopicId(firstIncomplete.topic_id);
        } else if (data.topics.length > 0) {
          setExpandedTopicId(data.topics[0].topic_id);
        }
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load agreement assistance data.');
    } finally {
      setLoading(false);
    }
  }, [dealId]);

  useEffect(() => {
    loadAssistance();
  }, [loadAssistance, currentVersion?.id]);

  function handleFieldChange(topicId, fieldKey, val) {
    setFormBuffer((prev) => ({
      ...prev,
      [topicId]: {
        ...prev[topicId],
        answers: {
          ...(prev[topicId]?.answers || {}),
          [fieldKey]: val,
        },
      },
    }));
  }

  function handleNotesChange(topicId, val) {
    setFormBuffer((prev) => ({
      ...prev,
      [topicId]: {
        ...prev[topicId],
        notes: val,
      },
    }));
  }

  function handleStatusToggle(topicId) {
    setFormBuffer((prev) => {
      const curr = prev[topicId]?.status;
      const next = curr === 'discussed' ? 'pending' : 'discussed';
      return {
        ...prev,
        [topicId]: {
          ...prev[topicId],
          status: next,
        },
      };
    });
  }

  async function handleSaveTopic(topicId) {
    const topicData = formBuffer[topicId];
    if (!topicData) return;

    setSavingTopicId(topicId);
    setErrorMsg('');
    try {
      await api.updateAssistanceTopic(dealId, topicId, {
        status: topicData.status,
        answers: topicData.answers,
        notes: topicData.notes,
      });

      // Reload report to refresh completion counts
      const updated = await api.getAgreementAssistance(dealId);
      setReport(updated);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to save topic details.');
    } finally {
      setSavingTopicId(null);
    }
  }

  async function handleApplyToDraft() {
    setApplyingDraft(true);
    setErrorMsg('');
    try {
      const res = await api.applyAssistanceToDraft(dealId);
      alert(res.message || 'Agreement draft updated with confirmed details.');
      if (onDraftUpdated) {
        onDraftUpdated();
      }
      loadAssistance();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to update agreement draft.');
    } finally {
      setApplyingDraft(false);
    }
  }

  async function handleInitializeTemplate() {
    if (
      !confirm(
        'This will populate the active draft with the General Agreement Template pre-filled with your deal details. Continue?'
      )
    ) {
      return;
    }
    setInitializingTpl(true);
    setErrorMsg('');
    try {
      const res = await api.initializeGeneralTemplate(dealId);
      alert(res.message || 'Initialized General Agreement Template.');
      if (onDraftUpdated) {
        onDraftUpdated();
      }
      loadAssistance();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to initialize template.');
    } finally {
      setInitializingTpl(false);
    }
  }

  if (loading) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-slate-200">
        <RefreshCw className="w-6 h-6 text-blue-600 animate-spin mx-auto mb-2" />
        <p className="text-xs text-slate-600 font-medium">
          Analyzing agreement draft against General Agreement Template...
        </p>
      </div>
    );
  }

  if (!report) {
    return null;
  }

  const filteredTopics = report.topics.filter((t) => {
    if (activeFilter === 'pending') return !t.is_complete;
    if (activeFilter === 'discussed') return t.is_complete;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Assistance Banner & Progress */}
      <div className="p-5 bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 text-white rounded-xl shadow-md space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-blue-500/20 border border-blue-400/30 rounded-lg">
              <Scale className="w-5 h-5 text-blue-300" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <span>Agreement Assistance</span>
                <span className="text-[10px] uppercase tracking-wider bg-blue-500/30 text-blue-200 px-2 py-0.5 rounded-full font-mono">
                  General Agreement Template
                </span>
              </h3>
              <p className="text-xs text-slate-300 mt-0.5">
                Guidance on required information and mutual counterparty discussions under Indian law.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2 shrink-0">
            <button
              id="btn-init-general-template"
              type="button"
              onClick={handleInitializeTemplate}
              disabled={initializingTpl}
              className="px-3 py-1.5 bg-white/10 hover:bg-white/20 border border-white/20 text-white text-xs font-semibold rounded-md transition-colors flex items-center space-x-1.5 disabled:opacity-50"
              title="Populates the General Agreement Template into the draft"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${initializingTpl ? 'animate-spin' : ''}`} />
              <span>{initializingTpl ? 'Populating...' : 'Reset to General Template'}</span>
            </button>

            <button
              id="btn-apply-assistance-draft"
              type="button"
              onClick={handleApplyToDraft}
              disabled={applyingDraft || report.discussed_topics === 0}
              className="px-3.5 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold rounded-md shadow-sm transition-colors flex items-center space-x-1.5 disabled:opacity-50"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{applyingDraft ? 'Updating Draft...' : 'Update Draft with Answers'}</span>
            </button>
          </div>
        </div>

        {/* Completion Progress Bar */}
        <div className="space-y-1.5 pt-2 border-t border-white/10">
          <div className="flex justify-between items-center text-xs text-slate-300">
            <span className="font-medium">
              Topics Discussed: <strong className="text-white">{report.discussed_topics}</strong> of{' '}
              {report.total_topics}
            </span>
            <span className="font-mono font-bold text-emerald-400">
              {report.completion_percentage}% Complete
            </span>
          </div>
          <div className="w-full bg-slate-800/80 rounded-full h-2 overflow-hidden">
            <div
              className="bg-emerald-400 h-full rounded-full transition-all duration-500"
              style={{ width: `${report.completion_percentage}%` }}
            />
          </div>
          <p className="text-[11px] text-slate-300">
            * All collected details update the draft while keeping the template clauses, structure, and numbering strictly identical.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-2">
        <div className="flex space-x-2 text-xs">
          <button
            type="button"
            onClick={() => setActiveFilter('all')}
            className={`px-3 py-1 rounded-full font-semibold transition-colors ${
              activeFilter === 'all'
                ? 'bg-navy-900 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            All Topics ({report.total_topics})
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter('pending')}
            className={`px-3 py-1 rounded-full font-semibold transition-colors flex items-center space-x-1 ${
              activeFilter === 'pending'
                ? 'bg-amber-600 text-white'
                : 'bg-amber-50 text-amber-800 hover:bg-amber-100 border border-amber-200'
            }`}
          >
            <Clock className="w-3 h-3" />
            <span>Pending Discussion ({report.pending_topics})</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter('discussed')}
            className={`px-3 py-1 rounded-full font-semibold transition-colors flex items-center space-x-1 ${
              activeFilter === 'discussed'
                ? 'bg-emerald-700 text-white'
                : 'bg-emerald-50 text-emerald-800 hover:bg-emerald-100 border border-emerald-200'
            }`}
          >
            <CheckCircle2 className="w-3 h-3" />
            <span>Discussed ({report.discussed_topics})</span>
          </button>
        </div>

        <span className="text-xs text-slate-500 font-medium hidden sm:inline">
          {report.missing_placeholders.length} template placeholders detected
        </span>
      </div>

      {/* Topics Accordion List */}
      <div className="space-y-3">
        {filteredTopics.map((topic, idx) => {
          const isExpanded = expandedTopicId === topic.topic_id;
          const currentBuf = formBuffer[topic.topic_id] || { answers: {}, notes: '', status: 'pending' };
          const isDiscussed = currentBuf.status === 'discussed';

          return (
            <div
              key={topic.topic_id}
              className={`rounded-xl border transition-all ${
                isDiscussed
                  ? 'bg-white border-emerald-200 shadow-sm'
                  : 'bg-white border-slate-200 shadow-sm'
              }`}
            >
              {/* Accordion Header */}
              <div
                onClick={() => setExpandedTopicId(isExpanded ? null : topic.topic_id)}
                className="p-4 flex items-center justify-between cursor-pointer select-none hover:bg-slate-50/70 rounded-t-xl transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                      isDiscussed
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    {idx + 1}
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <h4 className="text-xs font-bold text-navy-900">{topic.title}</h4>
                      <span className="text-[10px] font-mono font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                        {topic.clause_ref}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-1">
                      {topic.questions[0]}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-3 shrink-0">
                  {isDiscussed ? (
                    <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-[11px] font-bold flex items-center space-x-1">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                      <span>Discussed</span>
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 rounded-full text-[11px] font-medium flex items-center space-x-1">
                      <Clock className="w-3 h-3 text-amber-600" />
                      <span>Pending Discussion</span>
                    </span>
                  )}

                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  )}
                </div>
              </div>

              {/* Accordion Content Body */}
              {isExpanded && (
                <div className="px-5 pb-5 pt-2 border-t border-slate-100 space-y-4">
                  {/* Questions to Discuss with Counterparty */}
                  <div className="p-3.5 bg-blue-50/80 border border-blue-200 rounded-lg space-y-2">
                    <div className="flex items-center space-x-1.5 text-xs font-bold text-blue-900">
                      <MessageSquare className="w-4 h-4 text-blue-600" />
                      <span>Questions to Discuss with Counterparty:</span>
                    </div>
                    <ul className="list-disc list-inside space-y-1 text-xs text-blue-950">
                      {topic.questions.map((q, qIdx) => (
                        <li key={qIdx} className="leading-relaxed">
                          {q}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Why this question is legally important */}
                  <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-1.5">
                    <div className="flex items-center space-x-1.5 text-xs font-bold text-slate-800">
                      <Scale className="w-4 h-4 text-indigo-700" />
                      <span>Why this is legally important (Statutory Significance):</span>
                    </div>
                    <p className="text-xs text-slate-700 leading-relaxed font-normal">
                      {topic.importance}
                    </p>
                  </div>

                  {/* Template placeholders tracked */}
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500">
                    <span className="font-semibold text-slate-700">Template Placeholders:</span>
                    {topic.placeholders.map((p, pIdx) => (
                      <span
                        key={pIdx}
                        className="px-2 py-0.5 bg-slate-100 border border-slate-200 rounded text-slate-700 font-mono text-[10px]"
                      >
                        {p}
                      </span>
                    ))}
                  </div>

                  {/* Input Fields to Collect Answers */}
                  <div className="space-y-3 pt-2">
                    <h5 className="text-xs font-bold text-navy-900 uppercase tracking-wider">
                      Confirmed Answers & Terms:
                    </h5>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {topic.fields.map((field) => (
                        <div key={field.key} className="space-y-1">
                          <label className="block text-[11px] font-semibold text-slate-700">
                            {field.label}
                          </label>
                          <input
                            type="text"
                            placeholder={field.placeholder || ''}
                            value={currentBuf.answers[field.key] || ''}
                            onChange={(e) => handleFieldChange(topic.topic_id, field.key, e.target.value)}
                            className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 focus:border-navy-900 outline-none"
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Notes / Discussion Record */}
                  <div className="space-y-1">
                    <label className="block text-[11px] font-semibold text-slate-700">
                      Counterparty Discussion Notes (Optional):
                    </label>
                    <textarea
                      rows={2}
                      placeholder="e.g. Discussed with counterparty via phone call on 26 Oct; counterparty confirmed registered address and PAN."
                      value={currentBuf.notes || ''}
                      onChange={(e) => handleNotesChange(topic.topic_id, e.target.value)}
                      className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-md focus:ring-1 focus:ring-navy-900 outline-none"
                    />
                  </div>

                  {/* Actions for this Topic */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100">
                    <button
                      type="button"
                      onClick={() => handleStatusToggle(topic.topic_id)}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-md border transition-colors flex items-center space-x-1.5 ${
                        isDiscussed
                          ? 'bg-amber-50 text-amber-800 border-amber-300 hover:bg-amber-100'
                          : 'bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100'
                      }`}
                    >
                      {isDiscussed ? (
                        <>
                          <Clock className="w-3.5 h-3.5 text-amber-600" />
                          <span>Reopen / Mark as Pending Discussion</span>
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Mark as Discussed with Counterparty</span>
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      onClick={() => handleSaveTopic(topic.topic_id)}
                      disabled={savingTopicId === topic.topic_id}
                      className="px-4 py-1.5 bg-navy-900 hover:bg-navy-800 text-white text-xs font-bold rounded-md shadow-sm transition-colors flex items-center space-x-1.5 disabled:opacity-50"
                    >
                      <Save className="w-3.5 h-3.5" />
                      <span>{savingTopicId === topic.topic_id ? 'Saving...' : 'Save Topic Details'}</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
