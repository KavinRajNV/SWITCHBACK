import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import bgImage from '../assets/Login_signup_page_bg.webp';
import { useApp } from '../context/AppContext';
import { uploadResume, saveManualSkills, parseGoalText, searchSkills } from '../lib/api';

export const StartScreen: React.FC = () => {
  const navigate = useNavigate();
  const { setSessionId, setLearnerProfile, setGoalProfile, setTargetOccupation, resetSession } = useApp();

  // Active tab state: 'resume' | 'manual' | 'goal'
  const [activeTab, setActiveTab] = useState<'resume' | 'manual' | 'goal'>('resume');

  // Resume state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [parseWarnings, setParseWarnings] = useState<string[]>([]);

  // Manual skills state — start empty, no hardcoded defaults
  const [manualSkills, setManualSkills] = useState<Array<{ skill: string; confidence: number }>>([]);
  const [skillInput, setSkillInput] = useState('');
  const [skillSuggestions, setSkillSuggestions] = useState<string[]>([]);
  const [manualLoading, setManualLoading] = useState(false);

  // Confidence rating for the skill being added
  const [pendingConfidence, setPendingConfidence] = useState<number>(5);

  // Goal text state — empty by default, user types their own
  const [goalText, setGoalText] = useState('');
  const [goalLoading, setGoalLoading] = useState(false);

  // Handle skill input autocomplete
  const handleSkillInputChange = async (val: string) => {
    setSkillInput(val);
    if (val.trim().length > 0) {
      const results = await searchSkills(val);
      setSkillSuggestions(results.filter((s) => !manualSkills.some((item) => item.skill === s)));
    } else {
      setSkillSuggestions([]);
    }
  };

  const handleAddSkill = (skillToAdd: string) => {
    if (!manualSkills.some((s) => s.skill === skillToAdd)) {
      setManualSkills([...manualSkills, { skill: skillToAdd, confidence: pendingConfidence }]);
    }
    setSkillInput('');
    setSkillSuggestions([]);
    setPendingConfidence(5); // reset for next skill
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setManualSkills(manualSkills.filter((s) => s.skill !== skillToRemove));
  };

  // Submit 1: Upload Resume
  const handleResumeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setResumeLoading(true);
    setParseWarnings([]);
    try {
      resetSession(); // clear any stale previous session
      const data = await uploadResume(selectedFile);
      setSessionId(data.session_id);
      setLearnerProfile(data.learner_profile);
      if (data.parse_warnings && data.parse_warnings.length > 0) {
        setParseWarnings(data.parse_warnings);
      }
      navigate('/skills');
    } catch (err: any) {
      alert(err.message || 'Failed to parse resume file.');
    } finally {
      setResumeLoading(false);
    }
  };

  // Submit 2: Manual Skills
  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (manualSkills.length === 0) {
      alert('Please add at least one skill.');
      return;
    }

    setManualLoading(true);
    try {
      resetSession(); // clear any stale previous session
      const data = await saveManualSkills(manualSkills);
      setSessionId(data.session_id);
      setLearnerProfile(data.learner_profile);
      navigate('/skills');
    } catch (err: any) {
      alert(err.message || 'Failed to save manual skills.');
    } finally {
      setManualLoading(false);
    }
  };

  // Submit 3: Free-Text Goal
  const handleGoalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goalText.trim()) return;

    setGoalLoading(true);
    try {
      resetSession(); // clear any stale previous session
      const data = await parseGoalText(goalText);
      setSessionId(data.session_id);
      setLearnerProfile(data.learner_profile);
      setGoalProfile(data.goal_profile);
      if (data.target_occupation) {
        setTargetOccupation(data.target_occupation);
      }
      navigate('/skills');
    } catch (err: any) {
      alert(err.message || 'Failed to parse goal prompt.');
    } finally {
      setGoalLoading(false);
    }
  };

  return (
    <div className="relative min-h-[92vh] flex items-center justify-center py-16 px-4 sm:px-6 overflow-hidden">
      {/* Background Graphic */}
      <div className="absolute inset-0 z-0">
        <img
          src={bgImage}
          alt="Login/Signup Path Background"
          className="w-full h-full object-cover object-center opacity-30"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-paper/80 via-paper/60 to-paper" />
      </div>

      <div className="relative z-10 max-w-3xl w-full mx-auto space-y-8">
        
        {/* Header */}
        <div className="text-center space-y-3">
          <h1 className="font-heading text-3xl sm:text-5xl font-bold text-ink tracking-tight">
            Map Your Learning Frontier
          </h1>
          <p className="text-base sm:text-lg text-muted max-w-xl mx-auto leading-relaxed">
            Choose how you would like to initialize your current skill profile. Recomputed deterministically without LLM calls.
          </p>
        </div>

        {/* Tab Selection */}
        <div className="flex rounded-2xl bg-paper-dark/80 p-1.5 border border-contour/80 shadow-xs">
          <button
            onClick={() => setActiveTab('resume')}
            className={`flex-1 py-3 text-xs sm:text-sm font-heading font-bold rounded-xl transition-all ${
              activeTab === 'resume'
                ? 'bg-paper text-forest shadow-sm border border-contour/60'
                : 'text-muted hover:text-ink'
            }`}
          >
            Upload Resume
          </button>
          <button
            onClick={() => setActiveTab('manual')}
            className={`flex-1 py-3 text-xs sm:text-sm font-heading font-bold rounded-xl transition-all ${
              activeTab === 'manual'
                ? 'bg-paper text-forest shadow-sm border border-contour/60'
                : 'text-muted hover:text-ink'
            }`}
          >
            Enter Skills Manually
          </button>
          <button
            onClick={() => setActiveTab('goal')}
            className={`flex-1 py-3 text-xs sm:text-sm font-heading font-bold rounded-xl transition-all ${
              activeTab === 'goal'
                ? 'bg-paper text-forest shadow-sm border border-contour/60'
                : 'text-muted hover:text-ink'
            }`}
          >
            Express Your Goal
          </button>
        </div>

        {/* Card Body */}
        <div className="p-6 sm:p-8 rounded-2xl bg-paper border border-contour/80 shadow-xl space-y-6">
          
          {/* TAB 1: Upload Resume */}
          {activeTab === 'resume' && (
            <form onSubmit={handleResumeSubmit} className="space-y-6">
              <div className="border-2 border-dashed border-contour-dark hover:border-forest/60 rounded-2xl p-8 text-center bg-paper-dark/30 transition-colors">
                <input
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="hidden"
                  id="resume-file-input"
                />
                <label htmlFor="resume-file-input" className="cursor-pointer space-y-3 block">
                  <div className="w-12 h-12 rounded-full bg-forest/10 text-forest font-bold text-xl flex items-center justify-center mx-auto">
                    📄
                  </div>
                  <div className="font-heading text-sm font-bold text-ink">
                    {selectedFile ? selectedFile.name : 'Click to upload PDF, DOCX, or TXT resume'}
                  </div>
                  <div className="text-xs text-muted">
                    Layout-aware section classifier extracts evidence and section origins
                  </div>
                </label>
              </div>

              {parseWarnings.length > 0 && (
                <div className="p-4 rounded-xl bg-amber/10 border border-amber/30 text-xs text-amber-dark space-y-1">
                  <div className="font-bold">Parse Warnings:</div>
                  {parseWarnings.map((w, i) => (
                    <div key={i}>• {w}</div>
                  ))}
                </div>
              )}

              <button
                type="submit"
                disabled={!selectedFile || resumeLoading}
                className="w-full bg-forest hover:bg-forest-dark text-paper font-heading text-base font-semibold py-4 rounded-xl shadow-md transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {resumeLoading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-paper border-t-transparent rounded-full animate-spin" />
                    <span>Parsing Resume Sections...</span>
                  </>
                ) : (
                  'Parse Resume & Review Skills →'
                )}
              </button>
            </form>
          )}

          {/* TAB 2: Enter Skills Manually */}
          {activeTab === 'manual' && (
            <form onSubmit={handleManualSubmit} className="space-y-6">
              <div className="space-y-3">
                <label className="font-heading text-sm font-bold text-ink">
                  Add Your Verified Skills:
                </label>
                
                {/* Autocomplete Input */}
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search skill (e.g. Python, SQL, Power BI, Machine Learning)..."
                    value={skillInput}
                    onChange={(e) => handleSkillInputChange(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl bg-paper-dark/40 border border-contour text-ink text-sm focus:outline-none focus:ring-2 focus:ring-amber"
                  />
                  {skillSuggestions.length > 0 && (
                    <div className="absolute top-full left-0 right-0 z-30 mt-1 bg-paper border border-contour shadow-lg rounded-xl overflow-hidden max-h-48 overflow-y-auto">
                      {skillSuggestions.map((s) => (
                        <div
                          key={s}
                          onClick={() => handleAddSkill(s)}
                          className="px-4 py-2 text-xs font-medium text-ink hover:bg-forest/10 hover:text-forest cursor-pointer transition-colors"
                        >
                          + {s}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* P5: Self-Rating Confidence Selector */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-heading font-semibold text-muted">My level:</span>
                  {([
                    { label: 'Just starting', value: 3 },
                    { label: 'Comfortable', value: 6 },
                    { label: 'Strong', value: 9 },
                  ] as const).map(({ label, value }) => (
                    <button
                      key={label}
                      type="button"
                      onClick={() => setPendingConfidence(value)}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold border transition-all ${
                        pendingConfidence === value
                          ? 'bg-forest text-paper border-forest'
                          : 'bg-paper-dark/40 text-muted border-contour hover:border-forest/50'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                  <span className="text-[11px] text-muted">(applies to next added skill)</span>
                </div>

                {/* Skill Chips List */}
                <div className="flex flex-wrap gap-2 pt-2">
                  {manualSkills.map((sk) => {
                    const tierLabel = sk.confidence >= 8 ? 'Strong' : sk.confidence >= 5 ? 'Comfortable' : 'Starting';
                    return (
                      <span
                        key={sk.skill}
                        className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-forest/10 border border-forest/20 text-forest text-xs font-semibold"
                      >
                        {sk.skill}
                        <span className="text-[10px] text-forest/60 font-normal">({tierLabel})</span>
                        <button
                          type="button"
                          onClick={() => handleRemoveSkill(sk.skill)}
                          className="text-forest/70 hover:text-forest font-bold"
                        >
                          ✕
                        </button>
                      </span>
                    );
                  })}
                </div>
              </div>

              <button
                type="submit"
                disabled={manualSkills.length === 0 || manualLoading}
                className="w-full bg-forest hover:bg-forest-dark text-paper font-heading text-base font-semibold py-4 rounded-xl shadow-md transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {manualLoading ? 'Saving Profile...' : 'Review Skill Profile →'}
              </button>
            </form>
          )}


          {/* TAB 3: Express Your Goal */}
          {activeTab === 'goal' && (
            <form onSubmit={handleGoalSubmit} className="space-y-6">
              <div className="space-y-2">
                <label className="font-heading text-sm font-bold text-ink">
                  Describe Your Career Goal & Current Baseline:
                </label>
                <textarea
                  rows={4}
                  value={goalText}
                  onChange={(e) => setGoalText(e.target.value)}
                  placeholder="e.g. I am a Data Analyst with 3 years of experience proficient in SQL and Python. My goal is to become a Data Scientist in 6 months."
                  className="w-full px-4 py-3 rounded-xl bg-paper-dark/40 border border-contour text-ink text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-amber"
                />
                <p className="text-xs text-muted">
                  Heuristic regex & string-distance matcher extracts target role, timeframe, and baseline skills without LLMs.
                </p>
              </div>

              <button
                type="submit"
                disabled={!goalText.trim() || goalLoading}
                className="w-full bg-forest hover:bg-forest-dark text-paper font-heading text-base font-semibold py-4 rounded-xl shadow-md transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {goalLoading ? 'Parsing Goal Prompt...' : 'Extract Profile & Review Skills →'}
              </button>
            </form>
          )}

        </div>
      </div>
    </div>
  );
};
