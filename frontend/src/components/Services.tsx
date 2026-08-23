import React from 'react';
import leftImage from '../assets/landing_page_second_part_on_left_side.webp';
import graphIcon from '../assets/Minimalist_Hiking_Map_Icon.webp';
import salaryIcon from '../assets/Forest_Green_Wax_Seal_Checkmark.webp';
import pathIcon from '../assets/Minimalist_Mountain_Trail_Emblem.webp';

export const Services: React.FC = () => {
  return (
    <section id="what-we-do" className="relative py-24 bg-paper-dark/50 border-t border-b border-contour/80">
      <div className="max-w-7xl mx-auto px-6 sm:px-8">
        
        {/* Asymmetric Split Layout: Image on Left, Un-numbered Trail-Grounded Cards on Right */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center">
          
          {/* Left Column: Image Asset */}
          <div className="lg:col-span-5 relative">
            <div className="relative rounded-2xl overflow-hidden shadow-xl border border-contour/80 bg-paper">
              <img
                src={leftImage}
                alt="Switchback Trail Map Architecture"
                className="w-full h-auto object-cover transform hover:scale-105 transition-transform duration-500"
              />
            </div>
            {/* Decorative Contour Badge */}
            <div className="absolute -bottom-6 -right-6 bg-forest text-paper p-5 rounded-2xl shadow-lg hidden sm:block">
              <div className="font-heading text-2xl font-bold">100%</div>
              <div className="text-xs font-medium text-paper/80">Deterministic ML</div>
            </div>
          </div>

          {/* Right Column: De-Generic Trail-Grounded Feature Copy (Part C1: Eyebrow dot removed; Part C2: Left-accent border cards) */}
          <div className="lg:col-span-7">
            <h2 className="font-heading text-3xl sm:text-5xl font-bold tracking-tight text-ink mb-6">
              A Learning Path Built on Hard Computation, Not Generative Guesses
            </h2>

            <p className="text-base sm:text-lg text-ink/80 leading-relaxed mb-10">
              Generic career recommenders rely on LLM prompts that invent milestones out of thin air. Switchback constructs every path from real graph traversals, trained salary models, and indexed job market data.
            </p>

            {/* Feature Cards List (De-generic: Left-accent forest borders, warm contour backdrop, no plain white box grid) */}
            <div className="space-y-5">
              
              <div className="flex items-start gap-4 p-5 rounded-xl bg-paper border-l-4 border-l-forest border border-contour/80 shadow-sm hover:shadow-md transition-all">
                <img src={graphIcon} alt="Graph Icon" className="w-10 h-10 object-contain shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-heading text-lg font-bold text-ink mb-1">
                    Deterministic Skill Graph
                  </h3>
                  <p className="text-sm text-muted leading-relaxed">
                    Traverses 21,137 verified taxonomy and market transition edges across 1,281 nodes to compute friction-minimized learning paths.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4 p-5 rounded-xl bg-paper border-l-4 border-l-amber border border-contour/80 shadow-sm hover:shadow-md transition-all">
                <img src={salaryIcon} alt="Salary Engine Icon" className="w-10 h-10 object-contain shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-heading text-lg font-bold text-ink mb-1">
                    Market-Grounded Salary Benchmarking
                  </h3>
                  <p className="text-sm text-muted leading-relaxed">
                    Predicts your LPA trajectory at every milestone using a 323-feature GradientBoosting model trained on primary disclosed-salary postings.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4 p-5 rounded-xl bg-paper border-l-4 border-l-forest border border-contour/80 shadow-sm hover:shadow-md transition-all">
                <img src={pathIcon} alt="Adaptive Path Icon" className="w-10 h-10 object-contain shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-heading text-lg font-bold text-ink mb-1">
                    Adaptive Progress Recomputation
                  </h3>
                  <p className="text-sm text-muted leading-relaxed">
                    As you acquire and verify skills via projects or GitHub, our multi-skill Dijkstra engine re-optimizes your remaining steps in real time.
                  </p>
                </div>
              </div>

            </div>
          </div>

        </div>
      </div>
    </section>
  );
};
