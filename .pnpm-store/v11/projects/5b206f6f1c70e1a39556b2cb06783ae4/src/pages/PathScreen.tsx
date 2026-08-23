import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { completeMilestone } from '../lib/api';
import type { Milestone } from '../lib/api';

import freeGateIcon from '../assets/The_open_gate_between_two_low_post.webp';
import paidBookletIcon from '../assets/Minimalist_Green_Book_with_Orange_Bookmark.webp';
import checkmarkSeal from '../assets/Forest_Green_Wax_Seal_Checkmark.webp';

export const PathScreen: React.FC = () => {
  const { sessionId, pathData, setPathData, addCompletedSkill } = useApp();

  // Filter state for courses: 'all' | 'free' | 'paid'
  const [courseFilter, setCourseFilter] = useState<'all' | 'free' | 'paid'>('all');

  // Complete milestone modal state
  const [activeMilestone, setActiveMilestone] = useState<Milestone | null>(null);
  const [evidenceType, setEvidenceType] = useState<'self_report' | 'project_log' | 'github_verified'>('project_log');
  const [completing, setCompleting] = useState(false);
  const [toastMsg, setToastMsg] = useState('');

  // Path data
  const milestones = pathData?.milestones || [];
  const elevationProfile = pathData?.elevation_profile || [];

  // Custom SVG Area Chart path calculations
  const renderElevationChart = () => {
    if (elevationProfile.length === 0) return null;

    const width = 800;
    const height = 180;
    const padding = 30;

    const minSal = Math.min(...elevationProfile.map((p) => p.cumulative_predicted_salary_lpa)) * 0.9;
    const maxSal = Math.max(...elevationProfile.map((p) => p.cumulative_predicted_salary_lpa)) * 1.1;

    const getX = (idx: number) => padding + (idx / Math.max(elevationProfile.length - 1, 1)) * (width - 2 * padding);
    const getY = (sal: number) => height - padding - ((sal - minSal) / Math.max(maxSal - minSal, 1)) * (height - 2 * padding);

    const points = elevationProfile.map((p, idx) => `${getX(idx)},${getY(p.cumulative_predicted_salary_lpa)}`).join(' L ');
    const firstX = getX(0);
    const lastX = getX(elevationProfile.length - 1);
    const bottomY = height - padding;

    const areaD = `M ${firstX},${bottomY} L ${points} L ${lastX},${bottomY} Z`;
    const lineD = `M ${points}`;

    return (
      <div className="relative w-full overflow-x-auto">
        <svg className="w-full h-48 min-w-[600px]" viewBox={`0 0 ${width} ${height}`} fill="none">
          <defs>
            <linearGradient id="elevationGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#1F6B4D" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#FAF7F0" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line x1={padding} y1={bottomY} x2={width - padding} y2={bottomY} stroke="#E4DFD3" strokeWidth="1" />

          {/* Area fill under curve */}
          <path d={areaD} fill="url(#elevationGrad)" />

          {/* Main elevation line */}
          <path d={lineD} stroke="#1F6B4D" strokeWidth="3.5" fill="none" strokeLinecap="round" />

          {/* Dots at milestones */}
          {elevationProfile.map((p, idx) => {
            const cx = getX(idx);
            const cy = getY(p.cumulative_predicted_salary_lpa);
            return (
              <g key={idx} className="group cursor-pointer">
                <circle cx={cx} cy={cy} r="5" fill="#E08A34" stroke="#FAF7F0" strokeWidth="2" />
                <text x={cx} y={cy - 12} textAnchor="middle" fill="#1C2421" fontSize="10" fontWeight="bold">
                  ₹{p.cumulative_predicted_salary_lpa}L
                </text>
                <text x={cx} y={bottomY + 14} textAnchor="middle" fill="#4A5852" fontSize="9">
                  Step #{p.step}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    );
  };

  // Handle Complete Milestone Submit
  const handleCompleteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeMilestone || !sessionId) return;

    setCompleting(true);
    try {
      const res = await completeMilestone(sessionId, activeMilestone.skill, evidenceType);
      
      addCompletedSkill(activeMilestone.skill);

      // Update path in state
      if (pathData) {
        setPathData({
          ...pathData,
          path_length: res.new_path_length,
          milestones: res.remaining_milestones,
        });
      }

      setToastMsg(`Milestone '${activeMilestone.skill}' completed! You saved ${res.milestones_saved} milestone(s).`);
      setActiveMilestone(null);
      setTimeout(() => setToastMsg(''), 4000);
    } catch (err: any) {
      alert(err.message || 'Failed to mark milestone complete.');
    } finally {
      setCompleting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-8 py-12 space-y-10">
      
      {/* Toast Notification */}
      {toastMsg && (
        <div className="fixed top-20 right-6 z-50 p-4 rounded-xl bg-forest text-paper shadow-2xl border border-paper/20 text-xs font-semibold animate-bounce flex items-center gap-3">
          <img src={checkmarkSeal} alt="Checkmark" className="w-5 h-5 object-contain" />
          <span>{toastMsg}</span>
        </div>
      )}

      {/* Screen Header */}
      <div className="border-b border-contour/80 pb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-3xl sm:text-4xl font-bold text-ink">
            Your Learning Path & Elevation Profile
          </h1>
          <p className="text-sm text-muted mt-1">
            Target Role: <strong className="text-forest">{pathData?.target_occupation_title || 'Data Scientists'}</strong>
          </p>
        </div>

        {/* Free / Paid Course Toggle */}
        <div className="flex rounded-xl bg-paper-dark p-1 border border-contour/80 shadow-xs">
          <button
            onClick={() => setCourseFilter('all')}
            className={`px-3 py-1.5 text-xs font-heading font-semibold rounded-lg transition-all ${
              courseFilter === 'all' ? 'bg-paper text-forest shadow-xs' : 'text-muted'
            }`}
          >
            All Courses
          </button>
          <button
            onClick={() => setCourseFilter('free')}
            className={`px-3 py-1.5 text-xs font-heading font-semibold rounded-lg transition-all flex items-center gap-1.5 ${
              courseFilter === 'free' ? 'bg-paper text-forest shadow-xs' : 'text-muted'
            }`}
          >
            <img src={freeGateIcon} alt="Free" className="w-3.5 h-3.5 object-contain" />
            <span>Free Only</span>
          </button>
          <button
            onClick={() => setCourseFilter('paid')}
            className={`px-3 py-1.5 text-xs font-heading font-semibold rounded-lg transition-all flex items-center gap-1.5 ${
              courseFilter === 'paid' ? 'bg-paper text-forest shadow-xs' : 'text-muted'
            }`}
          >
            <img src={paidBookletIcon} alt="Paid" className="w-3.5 h-3.5 object-contain" />
            <span>Paid Only</span>
          </button>
        </div>
      </div>

      {/* SALARY ELEVATION CHART CARD (Custom SVG) */}
      <div className="p-6 rounded-2xl bg-paper border border-contour/80 shadow-md space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-heading text-xl font-bold text-ink">
              Model-Predicted Salary Elevation Curve (LPA)
            </h2>
            <p className="text-xs text-muted">
              Cumulative predicted LPA trajectory rising as you acquire milestone skills (GradientBoosting model)
            </p>
          </div>
          <span className="text-xs font-semibold text-forest bg-forest/10 px-3 py-1 rounded-full border border-forest/20">
            323-Feature ML Output
          </span>
        </div>

        {renderElevationChart()}
      </div>

      {/* MILESTONE TIMELINE CARDS */}
      <div className="space-y-6">
        <h2 className="font-heading text-2xl font-bold text-ink">
          Sequenced Path Milestones ({milestones.length})
        </h2>

        {milestones.length === 0 && (
          <div className="p-8 text-center bg-paper rounded-2xl border border-contour text-muted text-sm">
            No remaining milestones. You have completed your path!
          </div>
        )}

        {milestones.map((ms) => {
          const freeCourses = ms.free_courses || [];
          const paidCourses = ms.paid_courses || [];

          const showFree = courseFilter === 'all' || courseFilter === 'free';
          const showPaid = courseFilter === 'all' || courseFilter === 'paid';

          return (
            <div
              key={ms.step_number}
              className="p-6 rounded-2xl bg-paper border-l-4 border-l-forest border border-contour/80 shadow-sm hover:shadow-md transition-all space-y-4"
            >
              {/* Header Bar */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-contour/60 pb-3">
                <div className="flex items-center gap-3">
                  <span className="w-8 h-8 rounded-full bg-forest text-paper font-heading text-sm font-bold flex items-center justify-center">
                    #{ms.step_number}
                  </span>
                  <h3 className="font-heading text-xl font-bold text-ink">
                    {ms.skill}
                  </h3>
                  {ms.reachable_via && (
                    <span className="text-xs text-muted bg-paper-dark px-2.5 py-1 rounded-md border border-contour/60">
                      Reachable via {ms.reachable_via}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-xs text-forest font-semibold">Cost weight: {ms.cost}</span>
                  <button
                    onClick={() => setActiveMilestone(ms)}
                    className="bg-forest hover:bg-forest-dark text-paper text-xs font-heading font-semibold px-4 py-2 rounded-xl shadow-xs transition-all"
                  >
                    Mark Complete
                  </button>
                </div>
              </div>

              {/* Explanation Text */}
              {ms.explanation && (
                <p className="text-sm text-ink/80 leading-relaxed bg-paper-dark/30 p-3 rounded-xl border border-contour/60">
                  {ms.explanation}
                </p>
              )}

              {/* Course Offerings Section */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                
                {/* Free Courses */}
                {showFree && freeCourses.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-heading font-bold text-forest uppercase tracking-wider">
                      <img src={freeGateIcon} alt="Free Gate" className="w-4 h-4 object-contain" />
                      <span>Free Learning Options ({freeCourses.length})</span>
                    </div>
                    <div className="space-y-1.5">
                      {freeCourses.map((c, i) => (
                        <a
                          key={i}
                          href={c.url}
                          target="_blank"
                          rel="noreferrer"
                          className="p-2.5 rounded-xl bg-paper-dark/50 border border-contour/80 hover:border-forest/40 block transition-colors group"
                        >
                          <div className="text-xs font-semibold text-ink group-hover:text-forest flex items-center justify-between">
                            <span className="truncate">{c.title}</span>
                            <span className="text-[10px] text-muted ml-2">{c.source}</span>
                          </div>
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {/* Paid Courses */}
                {showPaid && paidCourses.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-heading font-bold text-amber-dark uppercase tracking-wider">
                      <img src={paidBookletIcon} alt="Paid Booklet" className="w-4 h-4 object-contain" />
                      <span>Paid Certified Courses ({paidCourses.length})</span>
                    </div>
                    <div className="space-y-1.5">
                      {paidCourses.map((c, i) => (
                        <a
                          key={i}
                          href={c.url}
                          target="_blank"
                          rel="noreferrer"
                          className="p-2.5 rounded-xl bg-paper-dark/50 border border-contour/80 hover:border-amber/40 block transition-colors group"
                        >
                          <div className="text-xs font-semibold text-ink group-hover:text-amber-dark flex items-center justify-between">
                            <span className="truncate">{c.title}</span>
                            <span className="text-[10px] text-amber-dark font-bold ml-2">
                              {c.price ? `₹${c.price}` : 'Paid'}
                            </span>
                          </div>
                        </a>
                      ))}
                    </div>
                  </div>
                )}

              </div>

            </div>
          );
        })}
      </div>

      {/* Complete Milestone Modal */}
      {activeMilestone && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div onClick={() => setActiveMilestone(null)} className="fixed inset-0 bg-ink/50 backdrop-blur-xs" />
          <div className="relative bg-paper rounded-2xl p-6 max-w-md w-full shadow-2xl border border-contour space-y-4 z-10">
            <div className="flex items-center gap-3 border-b border-contour pb-3">
              <img src={checkmarkSeal} alt="Checkmark" className="w-7 h-7 object-contain" />
              <h3 className="font-heading text-lg font-bold text-ink">
                Mark '{activeMilestone.skill}' Complete
              </h3>
            </div>

            <form onSubmit={handleCompleteSubmit} className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-heading font-bold text-ink block">
                  Select Evidence Verification Tier:
                </label>

                <div className="space-y-2">
                  <label className="flex items-center gap-3 p-3 rounded-xl border border-contour cursor-pointer hover:bg-paper-dark">
                    <input
                      type="radio"
                      name="evidence"
                      value="self_report"
                      checked={evidenceType === 'self_report'}
                      onChange={() => setEvidenceType('self_report')}
                    />
                    <div className="text-xs">
                      <div className="font-bold text-ink">Self Reported (Confidence 6)</div>
                      <div className="text-muted">Learner self-reported completion</div>
                    </div>
                  </label>

                  <label className="flex items-center gap-3 p-3 rounded-xl border border-contour cursor-pointer hover:bg-paper-dark">
                    <input
                      type="radio"
                      name="evidence"
                      value="project_log"
                      checked={evidenceType === 'project_log'}
                      onChange={() => setEvidenceType('project_log')}
                    />
                    <div className="text-xs">
                      <div className="font-bold text-ink">Project Evidence Logged (Confidence 7)</div>
                      <div className="text-muted">Submitted project repository/documentation</div>
                    </div>
                  </label>

                  <label className="flex items-center gap-3 p-3 rounded-xl border border-contour cursor-pointer hover:bg-paper-dark">
                    <input
                      type="radio"
                      name="evidence"
                      value="github_verified"
                      checked={evidenceType === 'github_verified'}
                      onChange={() => setEvidenceType('github_verified')}
                    />
                    <div className="text-xs">
                      <div className="font-bold text-ink">GitHub Repository Verified (Confidence 9)</div>
                      <div className="text-muted">Automated code analysis verification</div>
                    </div>
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setActiveMilestone(null)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-muted hover:text-ink"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={completing}
                  className="bg-forest hover:bg-forest-dark text-paper text-xs font-semibold px-5 py-2.5 rounded-xl shadow-xs disabled:opacity-50"
                >
                  {completing ? 'Recomputing Path...' : 'Confirm & Recompute Trail'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
