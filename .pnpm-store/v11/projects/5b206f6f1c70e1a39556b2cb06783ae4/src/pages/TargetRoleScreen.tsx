import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { searchRoles, generatePath, getRecommendedRoles } from '../lib/api';
import type { TargetOccupation, RecommendedRole } from '../lib/api';

import runnerSprite from '../assets/Dynamic_Green_Runner_Silhouette.webp';
import flagIcon from '../assets/Minimalist_Green_and_Orange_Pennant_Flag.webp';
import postMarker from '../assets/Numberplate_post.webp';

export const TargetRoleScreen: React.FC = () => {
  const navigate = useNavigate();
  const { sessionId, targetOccupation, setTargetOccupation, pathData, setPathData } = useApp();

  const [roleInput, setRoleInput] = useState(targetOccupation?.title || '');
  const [roleSuggestions, setRoleSuggestions] = useState<TargetOccupation[]>([]);
  const [selectedRole, setSelectedRole] = useState<TargetOccupation | null>(
    targetOccupation || null
  );

  const [pathLoading, setPathLoading] = useState(false);
  const [hoveredMilestone, setHoveredMilestone] = useState<any | null>(null);

  // P6: Recommended roles from skill overlap
  const [recommendations, setRecommendations] = useState<RecommendedRole[]>([]);
  const [recLoading, setRecLoading] = useState(false);

  // Load recommendations on mount if we have a session
  useEffect(() => {
    if (sessionId) {
      setRecLoading(true);
      getRecommendedRoles(sessionId)
        .then((recs) => setRecommendations(recs))
        .catch(() => {})
        .finally(() => setRecLoading(false));
    }
  }, [sessionId]);

  // Search roles
  const handleRoleInputChange = async (val: string) => {
    setRoleInput(val);
    if (val.trim().length > 0) {
      const results = await searchRoles(val);
      setRoleSuggestions(results);
    } else {
      setRoleSuggestions([]);
    }
  };

  const handleSelectRole = (role: TargetOccupation) => {
    setSelectedRole(role);
    setRoleInput(role.title);
    setRoleSuggestions([]);
    setTargetOccupation(role);
  };

  // Generate Path
  const handleGeneratePath = async () => {
    if (!sessionId) {
      alert('Session expired. Redirecting to start.');
      navigate('/start');
      return;
    }

    setPathLoading(true);
    try {
      const res = await generatePath(sessionId, selectedRole?.onet_soc_code, selectedRole?.market_role_id);
      setPathData(res);
    } catch (err: any) {
      alert(err.message || 'Failed to generate path.');
    } finally {
      setPathLoading(false);
    }
  };

  useEffect(() => {
    if (sessionId && selectedRole && (!pathData ||
      pathData.target_occupation_soc_code !== selectedRole?.onet_soc_code ||
      pathData.target_market_role_id !== selectedRole?.market_role_id)) {
      handleGeneratePath();
    }
  }, [selectedRole]);


  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-8 py-12 space-y-10">
      
      {/* Screen Header */}
      <div className="border-b border-contour/80 pb-6 space-y-2">
        <h1 className="font-heading text-3xl sm:text-4xl font-bold text-ink">
          Target Role & Road-to-Job Trail
        </h1>
        <p className="text-sm text-muted">
          Select your target career role. The trail segments below are directly driven by your real computed Dijkstra path length.
        </p>
      </div>

      {/* P6: Skill-Based Role Recommendations */}
      {(recLoading || recommendations.length > 0) && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <h2 className="font-heading text-lg font-bold text-ink">Suggested Roles Based on Your Skills</h2>
            <span className="text-xs text-muted bg-forest/10 border border-forest/20 px-2 py-0.5 rounded-full">Indian market skill fit</span>
          </div>
          {recLoading ? (
            <div className="text-xs text-muted animate-pulse">Computing skill-overlap recommendations...</div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {recommendations.map((rec) => (
                <button
                  key={rec.market_role_id || rec.onet_soc_code}
                  onClick={() => handleSelectRole({ onet_soc_code: rec.onet_soc_code, title: rec.title, market_role_id: rec.market_role_id, market_median_salary_lpa: rec.market_median_salary_lpa })}
                  className={`p-4 rounded-2xl border text-left transition-all hover:shadow-md hover:-translate-y-0.5 ${
                    selectedRole?.onet_soc_code === rec.onet_soc_code
                      ? 'border-forest bg-forest/10 shadow-md'
                      : 'border-contour/80 bg-paper hover:border-forest/40'
                  }`}
                >
                  <div className="font-heading text-sm font-bold text-ink leading-tight">{rec.title}</div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <span className="text-[10px] font-semibold bg-forest/10 text-forest px-2 py-0.5 rounded-full">
                      {rec.overlap_count} skill{rec.overlap_count !== 1 ? 's' : ''} match
                    </span>
                    {rec.market_median_salary_lpa && (
                      <span className="text-[10px] font-semibold bg-amber/10 text-amber-dark px-2 py-0.5 rounded-full">
                        ₹{rec.market_median_salary_lpa} LPA
                      </span>
                    )}
                  </div>
                  <div className="mt-1.5 text-[10px] text-muted">
                    Skill fit: {((rec.match_score ?? rec.idf_weighted_score ?? rec.jaccard_score) * 100).toFixed(1)}%
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Role Selection Box */}
      <div className="p-6 rounded-2xl bg-paper border border-contour/80 shadow-sm space-y-4 max-w-2xl">
        <label className="font-heading text-sm font-bold text-ink block">
          {recommendations.length > 0 ? 'Or Search Manually — O*NET Catalog (1,016 Roles):' : 'Search O*NET Occupation Catalog (1,016 Roles):'}
        </label>

        
        <div className="relative">
          <input
            type="text"
            placeholder="Search role (e.g. Data Scientists, Software Developers, Financial Analysts)..."
            value={roleInput}
            onChange={(e) => handleRoleInputChange(e.target.value)}
            className="w-full px-4 py-3 rounded-xl bg-paper-dark/40 border border-contour text-ink text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-amber"
          />
          {roleSuggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 z-30 mt-1 bg-paper border border-contour shadow-xl rounded-xl overflow-hidden max-h-56 overflow-y-auto">
              {roleSuggestions.map((r) => (
                <div
                  key={r.onet_soc_code}
                  onClick={() => handleSelectRole(r)}
                  className="px-4 py-3 text-xs font-medium text-ink hover:bg-forest/10 hover:text-forest cursor-pointer transition-colors border-b border-contour/40 flex justify-between items-center"
                >
                  <span>{r.title}</span>
                  {r.market_median_salary_lpa && (
                    <span className="text-[11px] font-semibold text-forest">₹{r.market_median_salary_lpa} LPA</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {selectedRole && (
          <div className="p-4 rounded-xl bg-forest/10 border border-forest/20 flex items-center justify-between">
            <div>
              <div className="text-xs text-muted">Target Occupation Selected:</div>
              <div className="font-heading text-base font-bold text-forest">{selectedRole.title}</div>
              <div className="text-xs text-muted">SOC Code: {selectedRole.onet_soc_code}</div>
            </div>
            {selectedRole.market_median_salary_lpa && (
              <div className="text-right">
                <div className="text-xs text-muted">Market Median Salary:</div>
                <div className="font-heading text-lg font-bold text-ink">₹{selectedRole.market_median_salary_lpa} LPA</div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ROAD-TO-JOB TRAIL VISUALIZATION (Task 4 Core Rule: Dash count strictly equals path_length) */}
      <div className="p-8 rounded-2xl bg-paper-dark/50 border border-contour/80 shadow-md space-y-6 relative overflow-hidden">
        
        <div className="flex items-center justify-between border-b border-contour/80 pb-4">
          <div>
            <h2 className="font-heading text-xl font-bold text-ink">
              Computed Road-to-Job Trail Segments
            </h2>
            <p className="text-xs text-muted">
              {pathLoading
                ? 'Computing Dijkstra minimum-friction graph traversal...'
                : pathData?.is_fully_qualified
                ? 'You possess all required skills for this role!'
                : `Real backend path length: ${pathData?.path_length || 0} milestone segments`}
            </p>
          </div>

          <div className="inline-flex items-center gap-2 bg-amber/10 border border-amber/30 text-amber-dark text-xs font-semibold px-3 py-1.5 rounded-full">
            <span className="w-2 h-2 rounded-full bg-amber" />
            Grounded Trail Visualization
          </div>
        </div>

        {pathLoading ? (
          <div className="py-16 text-center space-y-3">
            <div className="w-8 h-8 border-3 border-forest border-t-transparent rounded-full animate-spin mx-auto" />
            <div className="text-sm font-heading font-semibold text-forest">Generating Real Dijkstra Graph Path...</div>
          </div>
        ) : pathData?.is_fully_qualified ? (
          /* Celebratory State if fully qualified */
          <div className="py-12 text-center space-y-4 bg-paper rounded-xl border border-forest/30 p-6">
            <img src={flagIcon} alt="Target Reached" className="w-12 h-12 object-contain mx-auto" />
            <h3 className="font-heading text-2xl font-bold text-forest">Fully Qualified for {selectedRole?.title}!</h3>
            <p className="text-sm text-muted max-w-md mx-auto">
              Your acquired skill baseline covers 100% of top required skills for this target role.
            </p>
          </div>
        ) : (
          /* GROUNDED TRAIL: Segment count strictly equals path_length */
          <div className="relative py-8 px-4">
            
            {/* Trail Bar Track */}
            <div className="relative h-16 w-full flex items-center justify-between">
              
              {/* Connected Dashed SVG Line */}
              <div className="absolute inset-x-8 top-1/2 -translate-y-1/2 h-1 border-t-2 border-dashed border-forest/60 z-0" />

              {/* Start Position: Runner Sprite */}
              <div className="relative z-10 flex flex-col items-center group cursor-pointer">
                <img src={runnerSprite} alt="Runner (You Are Here)" className="w-10 h-10 object-contain drop-shadow-md" />
                <span className="text-[11px] font-heading font-bold text-forest mt-1 bg-paper px-2 py-0.5 rounded border border-contour shadow-xs">
                  Start (You)
                </span>
              </div>

              {/* Milestone Segment Posts (Strictly N = path_length) */}
              {pathData?.milestones.map((ms) => (
                <div
                  key={ms.step_number}
                  onMouseEnter={() => setHoveredMilestone(ms)}
                  onMouseLeave={() => setHoveredMilestone(null)}
                  className="relative z-10 flex flex-col items-center group cursor-pointer"
                >
                  <img
                    src={postMarker}
                    alt={`Milestone ${ms.step_number}`}
                    className="w-6 h-9 object-contain transform group-hover:scale-110 transition-transform"
                  />
                  <span className="text-[10px] font-heading font-bold text-ink mt-1 bg-paper px-1.5 py-0.5 rounded border border-contour/80">
                    #{ms.step_number}
                  </span>

                  {/* Tooltip on Hover/Tap */}
                  {hoveredMilestone?.step_number === ms.step_number && (
                    <div className="absolute bottom-full mb-2 z-30 w-48 p-3 rounded-xl bg-ink text-paper text-xs shadow-xl border border-paper/20 space-y-1">
                      <div className="font-heading font-bold text-amber-light">Step #{ms.step_number}: {ms.skill}</div>
                      <div className="text-[10px] text-paper/80 leading-tight">{ms.explanation || `Reachable via ${ms.reachable_via || 'frontier'}`}</div>
                      <div className="text-[10px] text-forest-light font-semibold">Cost weight: {ms.cost}</div>
                    </div>
                  )}
                </div>
              ))}

              {/* End Position: Target Flag */}
              <div className="relative z-10 flex flex-col items-center group cursor-pointer">
                <img src={flagIcon} alt="Target Role Flag" className="w-10 h-10 object-contain drop-shadow-md" />
                <span className="text-[11px] font-heading font-bold text-amber-dark mt-1 bg-paper px-2 py-0.5 rounded border border-contour shadow-xs">
                  {selectedRole?.title || 'Target'}
                </span>
              </div>

            </div>

            {/* Trail Legend */}
            <div className="flex items-center justify-between text-xs text-muted pt-6 border-t border-contour/60">
              <span>Start: Current Frontier</span>
              <span className="font-semibold text-forest">
                {pathData?.path_length} Milestones Traversed
              </span>
              <span>Finish: {selectedRole?.title}</span>
            </div>

          </div>
        )}

      </div>

      {/* Footer Navigation */}
      <div className="pt-4 flex items-center justify-between border-t border-contour/80">
        <button
          onClick={() => navigate('/skills')}
          className="text-xs font-heading font-semibold text-muted hover:text-ink px-4 py-2"
        >
          ← Back to Skills
        </button>

        <button
          onClick={() => navigate('/path')}
          disabled={pathLoading || !pathData}
          className="bg-forest hover:bg-forest-dark text-paper font-heading text-base font-semibold px-8 py-3.5 rounded-xl shadow-md transition-all transform hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-amber disabled:opacity-50"
        >
          See My Path & Elevation →
        </button>
      </div>

    </div>
  );
};
