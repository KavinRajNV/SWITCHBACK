import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { askQA, searchSkills } from '../lib/api';

export const WhatIfSlider: React.FC = () => {
  const { sessionId, pathData } = useApp();

  const [hypotheticalSkill, setHypotheticalSkill] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<string | null>('Python');
  const [loading, setLoading] = useState(false);
  const [whatIfResult, setWhatIfResult] = useState<any | null>(null);

  // Search candidate skills
  const handleInputChange = async (val: string) => {
    setHypotheticalSkill(val);
    if (val.trim().length > 0) {
      const results = await searchSkills(val);
      setSuggestions(results);
    } else {
      setSuggestions([]);
    }
  };

  const handleSelectSkill = (skill: string) => {
    setSelectedSkill(skill);
    setHypotheticalSkill(skill);
    setSuggestions([]);
  };

  // Debounced API call (300ms)
  useEffect(() => {
    if (!sessionId || !selectedSkill) return;

    const handler = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await askQA(sessionId, 'what_if_i_already_know_x', selectedSkill);
        const payload = res.structured_payload || {};
        // The engine returns the recomputed path as `new_path`; derive which of
        // the learner's current milestones drop out of it.
        const newPathSkills = new Set<string>((payload.new_path || []).map((m: any) => (m.skill || '').toLowerCase()));
        const currentMilestoneSkills = (pathData?.milestones || []).map((m) => m.skill);
        const removed = currentMilestoneSkills.filter((s) => !newPathSkills.has(s.toLowerCase()));
        setWhatIfResult({
          answerText: res.answer_text,
          payload: { ...payload, removed_milestones: removed },
        });
      } catch (err: any) {
        console.error('What-If simulation error:', err);
        setWhatIfResult(null);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(handler);
  }, [sessionId, selectedSkill, pathData]);

  const presetSkills = ['Python', 'SQL', 'AWS', 'Power BI', 'Machine Learning'];

  return (
    <div className="p-6 rounded-2xl bg-paper border border-contour/80 shadow-md space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-contour/60 pb-4">
        <div>
          <h2 className="font-heading text-xl font-bold text-ink flex items-center gap-2">
            <span>⚡ Interactive "What-If" Scenario Simulator</span>
          </h2>
          <p className="text-xs text-muted">
            Toggle hypothetical candidate skills to simulate real Dijkstra graph path recomputation & milestone savings
          </p>
        </div>

        <span className="text-[11px] font-semibold text-amber-dark bg-amber/10 px-3 py-1 rounded-full border border-amber/30">
          300ms Debounced Backend QA Engine
        </span>
      </div>

      {/* Preset Skill Buttons */}
      <div className="space-y-2">
        <label className="text-xs font-heading font-bold uppercase tracking-wider text-muted block">
          Quick Preset Hypothetical Skills:
        </label>
        <div className="flex flex-wrap gap-2">
          {presetSkills.map((sk) => (
            <button
              key={sk}
              onClick={() => handleSelectSkill(sk)}
              className={`px-3 py-1.5 rounded-xl text-xs font-heading font-semibold transition-all ${
                selectedSkill === sk
                  ? 'bg-forest text-paper shadow-xs border border-forest'
                  : 'bg-paper-dark/60 text-ink hover:bg-paper border border-contour'
              }`}
            >
              + What if I know {sk}?
            </button>
          ))}
        </div>
      </div>

      {/* Custom Skill Autocomplete Input */}
      <div className="relative max-w-md">
        <input
          type="text"
          placeholder="Or type any skill (e.g. Docker, PyTorch, R)..."
          value={hypotheticalSkill}
          onChange={(e) => handleInputChange(e.target.value)}
          className="w-full px-4 py-2.5 rounded-xl bg-paper-dark/40 border border-contour text-ink text-xs font-medium focus:outline-none focus:ring-2 focus:ring-amber"
        />
        {suggestions.length > 0 && (
          <div className="absolute top-full left-0 right-0 z-30 mt-1 bg-paper border border-contour shadow-xl rounded-xl overflow-hidden max-h-40 overflow-y-auto">
            {suggestions.map((s) => (
              <div
                key={s}
                onClick={() => handleSelectSkill(s)}
                className="px-4 py-2 text-xs text-ink hover:bg-forest/10 hover:text-forest cursor-pointer transition-colors"
              >
                + {s}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Loading Spinner */}
      {loading && (
        <div className="flex items-center space-x-3 p-4 bg-paper-dark/30 rounded-xl border border-contour/60">
          <div className="w-4 h-4 border-2 border-forest border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-forest font-semibold">
            Recomputing graph frontier for '{selectedSkill}'...
          </span>
        </div>
      )}

      {/* Simulation Result Delta Display */}
      {!loading && whatIfResult && (
        <div className="p-5 rounded-2xl bg-paper-dark/40 border border-forest/30 space-y-3">
          <div className="flex items-center justify-between border-b border-contour/60 pb-2">
            <span className="font-heading text-sm font-bold text-forest">
              Simulated Scenario: Acquired '{selectedSkill}'
            </span>
            {whatIfResult.payload?.milestones_saved !== undefined && (
              <span className="text-xs font-bold text-paper bg-amber px-2.5 py-0.5 rounded-full shadow-xs">
                Saves {whatIfResult.payload.milestones_saved} Milestone(s)!
              </span>
            )}
          </div>

          <p className="text-xs text-ink/90 leading-relaxed whitespace-pre-wrap">
            {whatIfResult.answerText}
          </p>

          {whatIfResult.payload && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2 text-xs">
              <div className="p-2.5 rounded-xl bg-paper border border-contour">
                <div className="text-[10px] text-muted">Original Path Length:</div>
                <div className="font-heading font-bold text-ink">
                  {whatIfResult.payload.original_path_length || pathData?.path_length || 0} Milestones
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-paper border border-contour">
                <div className="text-[10px] text-muted">New Path Length:</div>
                <div className="font-heading font-bold text-forest">
                  {whatIfResult.payload.new_path_length || 0} Milestones
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-paper border border-contour col-span-2 sm:col-span-1">
                <div className="text-[10px] text-muted">Milestones Removed:</div>
                <div className="font-heading font-bold text-amber-dark">
                  {whatIfResult.payload.removed_milestones?.join(', ') || 'None'}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
};
