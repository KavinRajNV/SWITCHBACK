import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { getDashboardData, getLiveJobs, completeMilestone } from '../lib/api';
import type { JobPosting, Milestone, DashboardResponse } from '../lib/api';
import { ElevationChart } from '../components/ElevationChart';
import { WhatIfSlider } from '../components/WhatIfSlider';

import checkmarkSeal from '../assets/Forest_Green_Wax_Seal_Checkmark.webp';

export const DashboardScreen: React.FC = () => {
  const navigate = useNavigate();
  const { sessionId, pathData, setPathData, completedLogs, addCompletedSkill } = useApp();

  const [loading, setLoading] = useState(true);
  const [dash, setDash] = useState<DashboardResponse | null>(null);
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [jobsStatus, setJobsStatus] = useState<string>('loading');

  // Complete Next Milestone modal state
  const [activeNextMilestone, setActiveNextMilestone] = useState<Milestone | null>(null);
  const [evidenceType, setEvidenceType] = useState<'self_report' | 'project_log' | 'github_verified'>('project_log');
  const [completing, setCompleting] = useState(false);
  const [toastMsg, setToastMsg] = useState('');

  const loadDashboard = async () => {
    if (!sessionId) return null;
    const dashRes = await getDashboardData(sessionId);
    setDash(dashRes);
    return dashRes;
  };

  // Fetch Dashboard Data & Adzuna Live Jobs
  useEffect(() => {
    if (!sessionId) {
      navigate('/start');
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      try {
        const dashRes = await loadDashboard();
        const targetRole = dashRes?.target_role?.title || pathData?.target_occupation_title;
        if (targetRole) {
          const jobsRes = await getLiveJobs(targetRole);
          setJobs(jobsRes.jobs || []);
          setJobsStatus(jobsRes.status || 'unavailable');
        } else {
          setJobsStatus('unavailable');
        }
      } catch (err: any) {
        // Session gone / backend unreachable — send the learner back to the start.
        console.error('Failed to load dashboard:', err);
        navigate('/start');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // Prefer authoritative backend values; fall back to locally-known path data only for the milestone cards.
  const elevationProfile = dash?.elevation_profile ?? pathData?.elevation_profile ?? [];
  const completedCount = dash?.progress.completed_milestones_count ?? 0;
  const remainingCount = dash?.progress.remaining_milestones_count ?? (pathData?.milestones.length ?? 0);
  const progressPct = dash ? Math.round(dash.progress.progress_percentage) : 0;
  const totalAcquiredSkills = dash?.profile_summary.total_acquired_skills ?? 0;
  const currentSalaryLpa =
    elevationProfile[Math.min(completedCount, Math.max(elevationProfile.length - 1, 0))]?.cumulative_predicted_salary_lpa ??
    dash?.profile_summary.current_predicted_salary_lpa ??
    null;
  const targetTitle = dash?.target_role.title ?? pathData?.target_occupation_title ?? null;
  const targetSoc = dash?.target_role.onet_soc_code ?? pathData?.target_occupation_soc_code ?? null;
  const marketMedian = dash?.target_role.market_median_salary_lpa ?? null;

  const nextMilestone: Milestone | null =
    dash?.next_action_milestone ?? (pathData?.milestones && pathData.milestones.length > 0 ? pathData.milestones[0] : null);

  // Handle Mark Complete Submit
  const handleCompleteNext = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeNextMilestone || !sessionId) return;

    setCompleting(true);
    try {
      const res = await completeMilestone(sessionId, activeNextMilestone.skill, evidenceType);
      addCompletedSkill(activeNextMilestone.skill, evidenceType);

      if (pathData) {
        setPathData({
          ...pathData,
          path_length: res.new_path_length,
          milestones: res.remaining_milestones,
        });
      }

      // Re-pull real aggregates rather than hand-patching them.
      await loadDashboard();

      setToastMsg(`Completed '${activeNextMilestone.skill}'! Saved ${res.milestones_saved} milestone(s).`);
      setActiveNextMilestone(null);

      if (res.new_path_length === 0) {
        setTimeout(() => navigate('/celebration'), 1500);
      } else {
        setTimeout(() => setToastMsg(''), 3000);
      }
    } catch (err: any) {
      alert(err.message || 'Failed to complete milestone.');
    } finally {
      setCompleting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-24 text-center space-y-4">
        <div className="w-10 h-10 border-3 border-forest border-t-transparent rounded-full animate-spin mx-auto" />
        <div className="font-heading font-semibold text-forest text-base">Loading dashboard aggregates…</div>
      </div>
    );
  }

  const hasRole = Boolean(targetTitle);

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
            Learner Frontier Dashboard
          </h1>
          <p className="text-sm text-muted mt-1">
            {hasRole ? (
              <>Target Role: <strong className="text-forest">{targetTitle}</strong></>
            ) : (
              <>No target role selected yet.{' '}
                <button onClick={() => navigate('/target-role')} className="text-forest underline font-semibold">Pick one →</button>
              </>
            )}
            {' '}| Session <code className="text-xs">{sessionId?.slice(0, 8)}…</code>
          </p>
        </div>

        <div className="flex items-center gap-3">
          {progressPct >= 100 ? (
            <button
              onClick={() => navigate('/celebration')}
              className="bg-amber hover:bg-amber-dark text-paper font-heading text-xs font-bold px-4 py-2.5 rounded-xl shadow-md transition-all"
            >
              🎉 View Celebration Screen
            </button>
          ) : (
            <div className="bg-forest/10 border border-forest/20 text-forest font-heading text-xs font-bold px-4 py-2 rounded-xl">
              Progress: {progressPct}% Complete
            </div>
          )}
        </div>
      </div>

      {/* Profile Overview Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-paper border border-contour/80 shadow-xs space-y-1">
          <div className="text-xs text-muted font-heading font-semibold uppercase tracking-wider">Acquired Baseline Skills</div>
          <div className="font-heading text-2xl font-bold text-ink">{totalAcquiredSkills} Skills</div>
          <div className="text-[11px] text-forest">Extracted &amp; Verified</div>
        </div>

        <div className="p-5 rounded-2xl bg-paper border border-contour/80 shadow-xs space-y-1">
          <div className="text-xs text-muted font-heading font-semibold uppercase tracking-wider">Milestones Completed</div>
          <div className="font-heading text-2xl font-bold text-forest">{completedCount} Completed</div>
          <div className="text-[11px] text-muted">{remainingCount} Remaining</div>
        </div>

        <div className="p-5 rounded-2xl bg-paper border border-contour/80 shadow-xs space-y-1">
          <div className="text-xs text-muted font-heading font-semibold uppercase tracking-wider">
            {completedCount > 0 ? 'Achieved LPA Elevation' : 'Predicted LPA (Current Skills)'}
          </div>
          <div className="font-heading text-2xl font-bold text-ink">
            {currentSalaryLpa != null ? `₹${currentSalaryLpa} LPA` : '—'}
          </div>
          <div className="text-[11px] text-amber-dark font-semibold">Model-Predicted Trajectory</div>
        </div>

        <div className="p-5 rounded-2xl bg-paper border border-contour/80 shadow-xs space-y-1">
          <div className="text-xs text-muted font-heading font-semibold uppercase tracking-wider">Target Job Frontier</div>
          <div className="font-heading text-lg font-bold text-ink truncate">{targetTitle ?? 'Not selected'}</div>
          <div className="text-[11px] text-muted">{targetSoc ? `SOC: ${targetSoc}` : 'Choose a role to begin'}</div>
        </div>
      </div>

      {/* SHARED ELEVATION CHART (Solid Completed vs Dashed Projected Split) */}
      <div className="p-6 rounded-2xl bg-paper border border-contour/80 shadow-md space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-heading text-xl font-bold text-ink">
              Salary Trajectory Split: Completed vs Projected (LPA)
            </h2>
            <p className="text-xs text-muted">
              Solid line indicates achieved salary elevation; dashed line projects trajectory across remaining path milestones.
            </p>
          </div>
          <span className="text-xs font-semibold text-forest bg-forest/10 px-3 py-1 rounded-full border border-forest/20">
            Live Session State
          </span>
        </div>

        <ElevationChart
          elevationProfile={elevationProfile}
          completedCount={completedCount}
        />
      </div>

      {/* NEXT ACTION CARD & WHAT-IF SIMULATOR GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

        {/* Next Action Trigger Card (1 col) */}
        <div className="p-6 rounded-2xl bg-paper border-2 border-forest/40 shadow-md space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 bg-forest text-paper text-xs font-heading font-bold px-3 py-1 rounded-full">
              🎯 Next Priority Action
            </div>

            {nextMilestone ? (
              <div className="space-y-2">
                <h3 className="font-heading text-2xl font-bold text-ink">
                  {nextMilestone.skill}
                </h3>
                <p className="text-xs text-muted leading-relaxed">
                  {nextMilestone.explanation || (targetTitle ? `Key milestone skill to reach ${targetTitle}` : 'Key milestone skill on your path')}
                </p>
                <div className="text-xs text-forest font-semibold">
                  Cost weight: {nextMilestone.cost} | Step #{nextMilestone.step_number}
                </div>
              </div>
            ) : hasRole ? (
              <div className="space-y-2 py-4">
                <h3 className="font-heading text-2xl font-bold text-forest">Full Qualification Reached!</h3>
                <p className="text-xs text-muted">You have completed all milestones for this role.</p>
              </div>
            ) : (
              <div className="space-y-2 py-4">
                <h3 className="font-heading text-xl font-bold text-ink">No path yet</h3>
                <p className="text-xs text-muted">Select a target role to generate your milestone path.</p>
              </div>
            )}
          </div>

          {nextMilestone ? (
            <button
              onClick={() => setActiveNextMilestone(nextMilestone)}
              className="w-full bg-forest hover:bg-forest-dark text-paper font-heading text-sm font-semibold py-3.5 rounded-xl shadow-sm transition-all text-center"
            >
              Mark '{nextMilestone.skill}' Complete →
            </button>
          ) : hasRole ? (
            <button
              onClick={() => navigate('/celebration')}
              className="w-full bg-amber hover:bg-amber-dark text-paper font-heading text-sm font-semibold py-3.5 rounded-xl shadow-sm transition-all text-center"
            >
              Go to Celebration Screen →
            </button>
          ) : (
            <button
              onClick={() => navigate('/target-role')}
              className="w-full bg-forest hover:bg-forest-dark text-paper font-heading text-sm font-semibold py-3.5 rounded-xl shadow-sm transition-all text-center"
            >
              Select Target Role →
            </button>
          )}
        </div>

        {/* What-If Scenario Simulator (2 cols) */}
        <div className="lg:col-span-2">
          <WhatIfSlider />
        </div>

      </div>

      {/* LIVE ADZUNA JOBS STRIP (Visually handles status: "unavailable" graceful fallback) */}
      <div className="p-6 rounded-2xl bg-paper border border-contour/80 shadow-md space-y-4">
        <div className="flex items-center justify-between border-b border-contour/60 pb-3">
          <div>
            <h2 className="font-heading text-xl font-bold text-ink">
              Live Job Market Postings{targetTitle ? ` (${targetTitle})` : ''}
            </h2>
            <p className="text-xs text-muted">
              Fetched via live Adzuna REST integration with MongoDB TTL cache
            </p>
          </div>

          <span
            className={`text-xs font-semibold px-3 py-1 rounded-full border ${
              jobsStatus === 'success' || jobs.length > 0
                ? 'bg-forest/10 text-forest border-forest/20'
                : 'bg-amber/10 text-amber-dark border-amber/30'
            }`}
          >
            {jobsStatus === 'success' || jobs.length > 0 ? 'Adzuna API Live' : 'Adzuna Offline Fallback'}
          </span>
        </div>

        {jobs.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {jobs.slice(0, 3).map((j, idx) => (
              <a
                key={idx}
                href={j.url}
                target="_blank"
                rel="noreferrer"
                className="p-4 rounded-xl bg-paper-dark/40 border border-contour hover:border-forest/40 block transition-colors space-y-2 group"
              >
                <div className="font-heading text-xs font-bold text-ink group-hover:text-forest truncate">
                  {j.title}
                </div>
                <div className="text-[11px] text-muted flex justify-between">
                  <span>{j.company}</span>
                  <span>{j.location}</span>
                </div>
                {j.salary_max && (
                  <div className="text-[11px] font-semibold text-forest">
                    ₹{(j.salary_max / 100000).toFixed(1)} LPA
                  </div>
                )}
              </a>
            ))}
          </div>
        ) : (
          /* Graceful Failure Empty State Banner */
          <div className="p-6 rounded-xl bg-amber/10 border border-amber/30 text-center space-y-2">
            <div className="font-heading text-sm font-bold text-amber-dark">
              Live job strip currently unavailable
            </div>
            <p className="text-xs text-muted max-w-lg mx-auto">
              {marketMedian != null
                ? `Showing the local dataset benchmark instead: ₹${marketMedian} LPA median for this role.`
                : 'The live Adzuna request timed out or is rate-limited. Page layout is unaffected.'}
            </p>
          </div>
        )}
      </div>

      {/* MILESTONE ACTIVITY TIMELINE LOG (ISO Timestamps) */}
      <div className="p-6 rounded-2xl bg-paper border border-contour/80 shadow-md space-y-4">
        <h2 className="font-heading text-xl font-bold text-ink">
          Milestone Completion Log &amp; Activity Streak ({completedLogs.length})
        </h2>

        {completedLogs.length === 0 ? (
          <div className="text-xs text-muted py-4 text-center italic">
            No completed milestones logged in this session yet. Complete a milestone above to start your streak!
          </div>
        ) : (
          <div className="space-y-2">
            {completedLogs.map((log, i) => (
              <div
                key={i}
                className="p-3 rounded-xl bg-paper-dark/40 border border-contour flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-3">
                  <img src={checkmarkSeal} alt="Completed" className="w-5 h-5 object-contain" />
                  <span className="font-heading font-bold text-ink">{log.skill}</span>
                  <span className="text-[10px] text-forest font-semibold bg-forest/10 px-2 py-0.5 rounded border border-forest/20">
                    Tier: {log.evidence_type}
                  </span>
                </div>
                <span className="text-[11px] text-muted">
                  {new Date(log.completed_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Complete Milestone Modal */}
      {activeNextMilestone && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div onClick={() => setActiveNextMilestone(null)} className="fixed inset-0 bg-ink/50 backdrop-blur-xs" />
          <div className="relative bg-paper rounded-2xl p-6 max-w-md w-full shadow-2xl border border-contour space-y-4 z-10">
            <div className="flex items-center gap-3 border-b border-contour pb-3">
              <img src={checkmarkSeal} alt="Checkmark" className="w-7 h-7 object-contain" />
              <h3 className="font-heading text-lg font-bold text-ink">
                Mark '{activeNextMilestone.skill}' Complete
              </h3>
            </div>

            <form onSubmit={handleCompleteNext} className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-heading font-bold text-ink block">
                  Select Evidence Verification Tier:
                </label>

                <div className="space-y-2">
                  <label className="flex items-center gap-3 p-3 rounded-xl border border-contour cursor-pointer hover:bg-paper-dark">
                    <input
                      type="radio"
                      name="evidence_dash"
                      value="self_report"
                      checked={evidenceType === 'self_report'}
                      onChange={() => setEvidenceType('self_report')}
                    />
                    <div className="text-xs">
                      <div className="font-bold text-ink">Self Reported (Confidence 6)</div>
                    </div>
                  </label>

                  <label className="flex items-center gap-3 p-3 rounded-xl border border-contour cursor-pointer hover:bg-paper-dark">
                    <input
                      type="radio"
                      name="evidence_dash"
                      value="project_log"
                      checked={evidenceType === 'project_log'}
                      onChange={() => setEvidenceType('project_log')}
                    />
                    <div className="text-xs">
                      <div className="font-bold text-ink">Project Evidence Logged (Confidence 7)</div>
                    </div>
                  </label>

                  <label className="flex items-center gap-3 p-3 rounded-xl border border-contour cursor-pointer hover:bg-paper-dark">
                    <input
                      type="radio"
                      name="evidence_dash"
                      value="github_verified"
                      checked={evidenceType === 'github_verified'}
                      onChange={() => setEvidenceType('github_verified')}
                    />
                    <div className="text-xs">
                      <div className="font-bold text-ink">GitHub Repository Verified (Confidence 9)</div>
                    </div>
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setActiveNextMilestone(null)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-muted hover:text-ink"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={completing}
                  className="bg-forest hover:bg-forest-dark text-paper text-xs font-semibold px-5 py-2.5 rounded-xl shadow-xs disabled:opacity-50"
                >
                  {completing ? 'Recomputing Path...' : 'Confirm Milestone'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
