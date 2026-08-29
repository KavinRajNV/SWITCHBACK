import React from 'react';
import greenCircleMark from '../assets/green_circle.webp';
import blueSquareMark from '../assets/blue_square.webp';
import blackSquareMark from '../assets/black_sqare.webp';

interface HowItWorksProps {
  onGetStarted: () => void;
}

export const HowItWorks: React.FC<HowItWorksProps> = ({ onGetStarted }) => {
  const steps = [
    {
      num: "01",
      title: "Input Your Frontier",
      desc: "Upload a PDF/DOCX resume or enter your skills manually. Our layout-aware parser extracts evidence and assigns 1–10 confidence scores.",
      mark: greenCircleMark,
      tier: "Beginner Trail"
    },
    {
      num: "02",
      title: "Set Your Target Role",
      desc: "Choose from 1,016 O*NET occupations or describe your goal in plain language. The catalog matcher resolves it to a real occupation — no invented roles.",
      mark: greenCircleMark,
      tier: "Beginner Trail"
    },
    {
      num: "03",
      title: "Traverse Your Path",
      desc: "Our multi-skill Dijkstra algorithm computes a focused 10–12 milestone path, paired with a model-predicted salary elevation profile.",
      mark: blueSquareMark,
      tier: "Intermediate Elevation"
    },
    {
      num: "04",
      title: "Verify & Ascend",
      desc: "Complete milestones, log project evidence, or connect GitHub for verified skill bumps. The path dynamically re-optimizes as you progress.",
      mark: blackSquareMark,
      tier: "Expert Summit"
    }
  ];

  return (
    <section id="how-it-works" className="relative py-24 bg-paper">
      <div className="max-w-7xl mx-auto px-6 sm:px-8">
        
        {/* Section Header (Part E: Added explanatory lead sentence beneath heading) */}
        <div className="max-w-2xl mb-16 space-y-4">
          <h2 className="font-heading text-3xl sm:text-5xl font-bold tracking-tight text-ink">
            A Structured Journey from Your Current Frontier to Your Target Career
          </h2>
          <p className="text-base sm:text-lg text-muted leading-relaxed">
            Move step-by-step from your current skill baseline to full role qualification through deterministic graph milestones and real-time market progress tracking.
          </p>
        </div>

        {/* Asymmetric Split Layout: Connected Sequential Trail on Left, Monte Carlo P10/P50/P90 SVG Chart on Right */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-start">
          
          {/* Left Column: Sequential Numbered List with Connected Vertical Trail Line */}
          <div className="lg:col-span-7 relative">
            
            {/* Connected Vertical Trail Line behind step badges */}
            <div className="absolute left-8 top-8 bottom-24 w-0.5 border-l-2 border-dashed border-amber/60 hidden sm:block z-0" />

            <div className="space-y-8 relative z-10">
              {steps.map((step) => (
                <div
                  key={step.num}
                  className="group relative flex items-start gap-6 p-6 rounded-2xl bg-paper-dark/40 border border-contour/80 hover:border-forest/50 hover:bg-paper transition-all shadow-sm"
                >
                  {/* Step Number Badge */}
                  <div className="flex flex-col items-center shrink-0 bg-paper px-2 py-1 rounded-xl border border-contour/80 z-10 shadow-xs">
                    <span className="font-heading text-3xl font-bold text-forest group-hover:text-amber transition-colors">
                      {step.num}
                    </span>
                    <img
                      src={step.mark}
                      alt={step.tier}
                      className="w-5 h-5 object-contain mt-1.5 opacity-90"
                      title={step.tier}
                    />
                  </div>

                  {/* Step Copy */}
                  <div>
                    <h3 className="font-heading text-xl font-bold text-ink mb-2 flex items-center gap-3">
                      {step.title}
                    </h3>
                    <p className="text-sm sm:text-base text-muted leading-relaxed">
                      {step.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-8">
              <button
                onClick={onGetStarted}
                className="bg-forest hover:bg-forest-dark text-paper font-heading text-base font-semibold px-8 py-4 rounded-xl shadow-md transition-all transform hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-amber"
              >
                Start Your Trail Now
              </button>
            </div>
          </div>

          {/* Right Column: Pure Monte Carlo Timeline Simulation SVG Chart Card (Part D: Duplicate image card deleted) */}
          <div className="lg:col-span-5 lg:sticky lg:top-28">
            
            {/* On-brand Monte Carlo Timeline Distribution SVG Graph */}
            <div className="p-6 rounded-2xl bg-paper-dark/60 border border-contour/80 shadow-md space-y-5">
              <div className="flex items-center justify-between">
                <span className="font-heading text-base font-bold text-ink">
                  2,000-Trial Timeline Simulation
                </span>
                <span className="text-xs font-semibold text-forest bg-forest/10 px-3 py-1 rounded-full">
                  Monte Carlo Engine
                </span>
              </div>

              {/* Lognormal Bell-Curve SVG Visualization */}
              <div className="relative h-32 w-full pt-2">
                <svg className="w-full h-full" viewBox="0 0 300 90" fill="none">
                  {/* Distribution Fill Gradient */}
                  <defs>
                    <linearGradient id="curveGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#1F6B4D" stopOpacity="0.35" />
                      <stop offset="100%" stopColor="#FAF7F0" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>

                  {/* Lognormal Curve Path */}
                  <path
                    d="M 10 80 Q 50 78, 80 40 T 130 15 T 190 55 T 290 80 L 290 85 L 10 85 Z"
                    fill="url(#curveGradient)"
                  />
                  <path
                    d="M 10 80 Q 50 78, 80 40 T 130 15 T 190 55 T 290 80"
                    stroke="#1F6B4D"
                    strokeWidth="3"
                    fill="none"
                  />

                  {/* P10 Line (Optimistic) */}
                  <line x1="90" y1="28" x2="90" y2="80" stroke="#E08A34" strokeWidth="2" strokeDasharray="3 3" />
                  <circle cx="90" cy="28" r="4" fill="#E08A34" />
                  <text x="75" y="20" fill="#E08A34" fontSize="10" fontWeight="bold">P10</text>

                  {/* P50 Line (Realistic / Median) */}
                  <line x1="140" y1="15" x2="140" y2="80" stroke="#1F6B4D" strokeWidth="2" />
                  <circle cx="140" cy="15" r="4" fill="#1F6B4D" />
                  <text x="128" y="10" fill="#1F6B4D" fontSize="10" fontWeight="bold">P50</text>

                  {/* P90 Line (Conservative) */}
                  <line x1="200" y1="58" x2="200" y2="80" stroke="#4A5852" strokeWidth="2" strokeDasharray="3 3" />
                  <circle cx="200" cy="58" r="4" fill="#4A5852" />
                  <text x="190" y="52" fill="#4A5852" fontSize="10" fontWeight="bold">P90</text>
                </svg>
              </div>

              {/* Timeline Percentile Breakdown */}
              <div className="grid grid-cols-3 gap-3 text-center pt-2 border-t border-contour/60">
                <div className="p-3 rounded-xl bg-paper">
                  <div className="text-xs text-muted font-medium mb-1">Optimistic (P10)</div>
                  <div className="font-heading text-base font-bold text-amber">20.8 wks</div>
                </div>
                <div className="p-3 rounded-xl bg-paper border border-forest/30 shadow-xs">
                  <div className="text-xs text-muted font-medium mb-1">Realistic (P50)</div>
                  <div className="font-heading text-base font-bold text-forest">24.8 wks</div>
                </div>
                <div className="p-3 rounded-xl bg-paper">
                  <div className="text-xs text-muted font-medium mb-1">Conservative (P90)</div>
                  <div className="font-heading text-base font-bold text-muted">29.7 wks</div>
                </div>
              </div>

              <div className="text-xs text-muted text-center pt-1 italic">
                Stochastic 2,000-trial simulation sampling lognormal milestone study hours
              </div>

            </div>

          </div>

        </div>
      </div>
    </section>
  );
};
