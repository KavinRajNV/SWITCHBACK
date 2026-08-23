import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { searchSkills, verifyGithub, saveManualSkills } from '../lib/api';
import type { SkillEvidence } from '../lib/api';

import greenCircleMark from '../assets/green_circle.webp';
import blueSquareMark from '../assets/blue_square.webp';
import blackSquareMark from '../assets/black_sqare.webp';
import waxSealMark from '../assets/Forest_Green_Wax_Seal_Checkmark.webp';

export const SkillsScreen: React.FC = () => {
  const navigate = useNavigate();
  const { sessionId, learnerProfile, setLearnerProfile } = useApp();

  const [skillsList, setSkillsList] = useState<SkillEvidence[]>(
    learnerProfile?.extracted_skills || []
  );


  const [skillInput, setSkillInput] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [githubUsername, setGithubUsername] = useState('');
  const [githubModalOpen, setGithubModalOpen] = useState(false);
  const [githubLoading, setGithubLoading] = useState(false);
  const [githubStatusMsg, setGithubStatusMsg] = useState('');

  // Confidence Tier Icon Helper
  const getConfidenceMark = (conf: number) => {
    if (conf >= 8) return { icon: blackSquareMark, label: 'Expert Summit (8-10)' };
    if (conf >= 5) return { icon: blueSquareMark, label: 'Intermediate Elevation (5-7)' };
    return { icon: greenCircleMark, label: 'Beginner Trail (1-4)' };
  };

  // Add Skill
  const handleInputChange = async (val: string) => {
    setSkillInput(val);
    if (val.trim().length > 0) {
      const results = await searchSkills(val);
      const existing = skillsList.map((s) => s.skill.toLowerCase());
      setSuggestions(results.filter((r) => !existing.includes(r.toLowerCase())));
    } else {
      setSuggestions([]);
    }
  };

  const handleAddSkill = (skillName: string) => {
    const newEvidence: SkillEvidence = {
      skill: skillName,
      confidence: 5,
      found_in_sections: ['MANUAL'],
      mention_count: 1,
    };
    setSkillsList([...skillsList, newEvidence]);
    setSkillInput('');
    setSuggestions([]);
  };

  const handleRemoveSkill = (skillName: string) => {
    setSkillsList(skillsList.filter((s) => s.skill !== skillName));
  };

  // GitHub Verification
  const handleVerifyGithub = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!githubUsername.trim() || !sessionId) return;

    setGithubLoading(true);
    setGithubStatusMsg('');
    try {
      const res = await verifyGithub(sessionId, githubUsername);
      setGithubStatusMsg(`Verified ${res.verified_skills.length} skills from GitHub repository languages!`);
      
      // Upgrade matching skills in list to confidence 9 (github_verified tier)
      const updated = skillsList.map((se) => {
        if (res.verified_skills.includes(se.skill)) {
          return { ...se, confidence: 9, found_in_sections: [...se.found_in_sections, 'GITHUB_VERIFIED'] };
        }
        return se;
      });

      // Add any new verified skills
      res.verified_skills.forEach((verifiedSk) => {
        if (!updated.some((s) => s.skill === verifiedSk)) {
          updated.push({
            skill: verifiedSk,
            confidence: 9,
            found_in_sections: ['GITHUB_VERIFIED'],
            mention_count: 1,
          });
        }
      });

      setSkillsList(updated);
      setTimeout(() => setGithubModalOpen(false), 1500);
    } catch (err: any) {
      setGithubStatusMsg(err.message || 'GitHub verification failed.');
    } finally {
      setGithubLoading(false);
    }
  };

  // Continue to Target Role
  const handleContinue = async () => {
    if (sessionId) {
      try {
        const skillsWithConf = skillsList.map((s) => ({ skill: s.skill, confidence: s.confidence }));
        const res = await saveManualSkills(skillsWithConf, sessionId);
        setLearnerProfile(res.learner_profile);
      } catch (e) {
        // Fallback silently if session already has skills saved
      }
    }
    navigate('/target-role');
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-8 py-12 space-y-8">
      
      {/* Screen Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-contour/80 pb-6">
        <div>
          <h1 className="font-heading text-3xl sm:text-4xl font-bold text-ink">
            Your Acquired Skill Baseline
          </h1>
          <p className="text-sm text-muted mt-1">
            Skills detected from your input. The score reflects strength of resume evidence, not your claimed proficiency; you can adjust it below.
          </p>
        </div>

        <button
          onClick={() => setGithubModalOpen(true)}
          className="bg-paper-dark hover:bg-paper text-forest border border-forest/30 font-heading text-xs font-semibold px-4 py-2.5 rounded-xl shadow-xs flex items-center gap-2 transition-all focus:outline-none focus:ring-2 focus:ring-amber"
        >
          <img src={waxSealMark} alt="Wax Seal" className="w-5 h-5 object-contain" />
          <span>Verify via GitHub</span>
        </button>
      </div>

      {/* Add Skill Search Box */}
      <div className="relative max-w-xl">
        <input
          type="text"
          placeholder="Add more skills (e.g. Power BI, Docker, PyTorch)..."
          value={skillInput}
          onChange={(e) => handleInputChange(e.target.value)}
          className="w-full px-4 py-3 rounded-xl bg-paper border border-contour text-ink text-sm focus:outline-none focus:ring-2 focus:ring-amber shadow-xs"
        />
        {suggestions.length > 0 && (
          <div className="absolute top-full left-0 right-0 z-30 mt-1 bg-paper border border-contour shadow-xl rounded-xl overflow-hidden max-h-48 overflow-y-auto">
            {suggestions.map((s) => (
              <div
                key={s}
                onClick={() => handleAddSkill(s)}
                className="px-4 py-2.5 text-xs font-medium text-ink hover:bg-forest/10 hover:text-forest cursor-pointer transition-colors"
              >
                + {s}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Skills Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {skillsList.map((se) => {
          const mark = getConfidenceMark(se.confidence);
          const isGithubVerified = se.found_in_sections?.includes('GITHUB_VERIFIED') || se.confidence >= 9;

          return (
            <div
              key={se.skill}
              className="p-5 rounded-2xl bg-paper border border-contour/80 shadow-xs hover:shadow-md transition-all flex items-start justify-between relative group"
            >
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <img
                    src={mark.icon}
                    alt={mark.label}
                    className="w-5 h-5 object-contain shrink-0"
                    title={mark.label}
                  />
                  <span className="font-heading text-base font-bold text-ink">
                    {se.skill}
                  </span>
                  {isGithubVerified && (
                    <img
                      src={waxSealMark}
                      alt="GitHub Verified"
                      className="w-4 h-4 object-contain"
                      title="GitHub Repository Verified"
                    />
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted">
                  <span className="font-semibold text-forest">Evidence: {se.confidence}/10</span>
                  {se.found_in_sections && se.found_in_sections.length > 0 && (
                    <span className="bg-paper-dark px-2 py-0.5 rounded text-[11px] border border-contour/60">
                      {se.found_in_sections.join(', ')}
                    </span>
                  )}
                </div>
              </div>

              <button
                onClick={() => handleRemoveSkill(se.skill)}
                className="text-muted/60 hover:text-rose-600 font-bold text-sm p-1 rounded transition-colors"
                title="Remove Skill"
              >
                ✕
              </button>
            </div>
          );
        })}
      </div>

      {/* Footer Actions */}
      <div className="pt-6 border-t border-contour/80 flex items-center justify-between">
        <div className="text-xs text-muted">
          Total verified skills: <strong className="text-ink">{skillsList.length}</strong>
        </div>

        <button
          onClick={handleContinue}
          className="bg-forest hover:bg-forest-dark text-paper font-heading text-base font-semibold px-8 py-3.5 rounded-xl shadow-md transition-all transform hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-amber"
        >
          Select Target Role →
        </button>
      </div>

      {/* GitHub Verification Modal */}
      {githubModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div onClick={() => setGithubModalOpen(false)} className="fixed inset-0 bg-ink/50 backdrop-blur-xs" />
          <div className="relative bg-paper rounded-2xl p-6 max-w-md w-full shadow-2xl border border-contour space-y-4 z-10">
            <div className="flex items-center gap-3 border-b border-contour pb-3">
              <img src={waxSealMark} alt="Wax Seal" className="w-7 h-7 object-contain" />
              <h3 className="font-heading text-lg font-bold text-ink">GitHub Skill Verification</h3>
            </div>

            <p className="text-xs text-muted leading-relaxed">
              Enter a public GitHub username. We query public repositories to verify programming language frequencies and boost confidence scores to Tier 9.
            </p>

            <form onSubmit={handleVerifyGithub} className="space-y-4">
              <input
                type="text"
                placeholder="e.g. torvalds"
                value={githubUsername}
                onChange={(e) => setGithubUsername(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-paper-dark border border-contour text-ink text-sm focus:outline-none focus:ring-2 focus:ring-amber"
              />

              {githubStatusMsg && (
                <div className="text-xs font-semibold text-forest bg-forest/10 p-2.5 rounded-lg border border-forest/20">
                  {githubStatusMsg}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setGithubModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-muted hover:text-ink"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={githubLoading || !githubUsername.trim()}
                  className="bg-forest hover:bg-forest-dark text-paper text-xs font-semibold px-5 py-2.5 rounded-xl shadow-xs disabled:opacity-50"
                >
                  {githubLoading ? 'Verifying...' : 'Verify Repositories'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
