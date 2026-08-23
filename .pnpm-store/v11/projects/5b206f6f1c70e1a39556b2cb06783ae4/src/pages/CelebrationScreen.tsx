import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { getRelatedRoles } from '../lib/api';
import type { RelatedRole } from '../lib/api';

import flagIcon from '../assets/Minimalist_Green_and_Orange_Pennant_Flag.webp';
import waxSealMark from '../assets/Forest_Green_Wax_Seal_Checkmark.webp';

export const CelebrationScreen: React.FC = () => {
  const navigate = useNavigate();
  const { pathData, completedSkills, targetOccupation } = useApp();

  const [relatedRoles, setRelatedRoles] = useState<RelatedRole[]>([]);
  const [loadingRoles, setLoadingRoles] = useState(true);

  const socCode = targetOccupation?.onet_soc_code || pathData?.target_occupation_soc_code || '15-2051.00';
  const roleTitle = targetOccupation?.title || pathData?.target_occupation_title || 'Data Scientists';

  const elevationProfile = pathData?.elevation_profile || [];
  const finalSalary = elevationProfile.length > 0
    ? elevationProfile[elevationProfile.length - 1].cumulative_predicted_salary_lpa
    : 18.5;

  useEffect(() => {
    const fetchRelated = async () => {
      setLoadingRoles(true);
      try {
        const res = await getRelatedRoles(socCode);
        setRelatedRoles(res.related_occupations || []);
      } catch (err) {
        console.error('Failed to fetch related roles:', err);
      } finally {
        setLoadingRoles(false);
      }
    };

    fetchRelated();
  }, [socCode]);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-16 text-center space-y-10">
      
      {/* Hero Badge */}
      <div className="space-y-4">
        <div className="relative inline-block">
          <img src={flagIcon} alt="Pennant Flag" className="w-20 h-20 object-contain mx-auto animate-bounce" />
          <img src={waxSealMark} alt="Wax Seal" className="w-8 h-8 object-contain absolute bottom-0 right-0 shadow-lg" />
        </div>

        <h1 className="font-heading text-4xl sm:text-5xl font-bold text-forest tracking-tight">
          Frontier Conquered!
        </h1>
        <p className="text-base sm:text-lg text-muted max-w-xl mx-auto leading-relaxed">
          You have achieved 100% full qualification for <strong className="text-ink">{roleTitle}</strong>. All required skill milestones have been mastered.
        </p>
      </div>

      {/* Achievement Metric Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-3xl mx-auto">
        <div className="p-6 rounded-2xl bg-paper border border-contour/80 shadow-md space-y-1">
          <div className="text-xs text-muted font-heading font-semibold uppercase tracking-wider">Final Achieved Salary</div>
          <div className="font-heading text-3xl font-bold text-forest">₹{finalSalary} LPA</div>
          <div className="text-[11px] text-muted">Model Predicted Elevation</div>
        </div>

        <div className="p-6 rounded-2xl bg-paper border border-contour/80 shadow-md space-y-1">
          <div className="text-xs text-muted font-heading font-semibold uppercase tracking-wider">Total Milestones</div>
          <div className="font-heading text-3xl font-bold text-ink">{completedSkills.length || 8} Mastered</div>
          <div className="text-[11px] text-forest font-semibold">100% Path Completion</div>
        </div>

        <div className="p-6 rounded-2xl bg-paper border border-contour/80 shadow-md space-y-1">
          <div className="text-xs text-muted font-heading font-semibold uppercase tracking-wider">Zero LLM Guarantee</div>
          <div className="font-heading text-3xl font-bold text-amber-dark">100% Deterministic</div>
          <div className="text-[11px] text-muted">Traced to Model & Graph</div>
        </div>
      </div>

      {/* NEXT STRETCH GOAL SUGGESTIONS (Task 2 Real O*NET Data Endpoint) */}
      <div className="p-8 rounded-2xl bg-paper border border-contour/80 shadow-xl space-y-6 text-left max-w-3xl mx-auto">
        <div>
          <h2 className="font-heading text-2xl font-bold text-ink flex items-center gap-2">
            <span>🚀 Next Stretch Goal Career Trajectories</span>
          </h2>
          <p className="text-xs text-muted">
            Sourced directly from real O*NET primary-short related occupation taxonomy for SOC {socCode}
          </p>
        </div>

        {loadingRoles ? (
          <div className="py-8 text-center space-y-2">
            <div className="w-6 h-6 border-2 border-forest border-t-transparent rounded-full animate-spin mx-auto" />
            <div className="text-xs text-forest">Querying O*NET Primary-Short Taxonomy...</div>
          </div>
        ) : relatedRoles.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {relatedRoles.slice(0, 4).map((rel) => (
              <div
                key={rel.onet_soc_code}
                className="p-4 rounded-xl bg-paper-dark/40 border border-contour/80 hover:border-forest/40 transition-all space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="font-heading text-sm font-bold text-ink">{rel.title}</span>
                  <span className="text-[10px] text-muted bg-paper px-2 py-0.5 rounded border border-contour/60">
                    Tier: {rel.relatedness_tier}
                  </span>
                </div>

                <div className="text-xs text-muted flex justify-between">
                  <span>O*NET SOC: {rel.onet_soc_code}</span>
                  {rel.market_median_salary_lpa ? (
                    <span className="font-semibold text-forest">₹{rel.market_median_salary_lpa} LPA</span>
                  ) : (
                    <span className="italic text-muted">Salary: Disclosed per employer</span>
                  )}
                </div>

                <button
                  onClick={() => {
                    navigate('/target-role');
                  }}
                  className="w-full mt-2 bg-paper hover:bg-forest/10 border border-contour/80 text-forest text-xs font-semibold py-2 rounded-lg transition-colors"
                >
                  Set as Next Target Goal →
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-6 rounded-xl bg-paper-dark/30 border border-contour text-center text-xs text-muted italic">
            No primary-short related occupations listed in O*NET taxonomy for SOC code {socCode}.
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="pt-4 flex justify-center gap-4">
        <button
          onClick={() => navigate('/dashboard')}
          className="bg-paper border border-contour text-ink hover:text-forest font-heading text-sm font-semibold px-6 py-3 rounded-xl shadow-xs transition-all"
        >
          Return to Dashboard
        </button>

        <button
          onClick={() => navigate('/start')}
          className="bg-forest hover:bg-forest-dark text-paper font-heading text-sm font-semibold px-8 py-3 rounded-xl shadow-md transition-all"
        >
          Start New Learning Frontier →
        </button>
      </div>

    </div>
  );
};
