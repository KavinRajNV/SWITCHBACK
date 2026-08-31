import React from 'react';
import footerBg from '../assets/footer_background.webp';
import logoIcon from '../assets/Switchback_logo_only.webp';

export const Footer: React.FC = () => {
  return (
    <footer className="relative bg-forest-deep text-paper overflow-hidden pt-16 pb-12">
      {/* Part A: Visible Topographic & Mountain Landscape Texture Background Image */}
      <div className="absolute inset-0 z-0">
        <img
          src={footerBg}
          alt="Switchback Mountain Trail Footer Background"
          className="w-full h-full object-cover object-center opacity-40 mix-blend-luminosity"
        />
        {/* Subtle Gradient Overlay maintaining high text contrast without drowning image texture */}
        <div className="absolute inset-0 bg-gradient-to-t from-forest-deep/90 via-forest-deep/50 to-transparent pointer-events-none" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 sm:px-8">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-12 pb-12 border-b border-paper/10">
          
          {/* Column 1: Brand Info & Vector Logo Icon + White Wordmark */}
          <div className="md:col-span-6 space-y-4">
            <div className="flex items-center gap-3">
              <img
                src={logoIcon}
                alt="Switchback Logo Icon"
                className="w-9 h-9 object-contain"
              />
              <span className="font-heading text-2xl font-bold tracking-tight text-paper">
                SWITCHBACK
              </span>
            </div>

            <p className="text-sm text-paper/80 max-w-md leading-relaxed">
              A personalized learning-path recommender built on real trained models, graph algorithms, and verified market data.
            </p>

            {/* Quiet trust signal */}
            <div className="inline-flex items-center gap-2 bg-paper/10 border border-paper/20 rounded-full px-3.5 py-1.5 text-xs font-medium text-amber-light">
              <span className="w-2 h-2 rounded-full bg-amber" />
              Recommendations grounded in real data, not LLM guesses
            </div>
          </div>

          {/* Column 2: Navigation Links */}
          <div className="md:col-span-3 space-y-3">
            <div className="font-heading text-sm font-bold uppercase tracking-wider text-paper/90">
              Navigation
            </div>
            <ul className="space-y-2 text-sm text-paper/70">
              <li><a href="#what-we-do" className="hover:text-amber transition-colors">What We Do</a></li>
              <li><a href="#how-it-works" className="hover:text-amber transition-colors">How It Works</a></li>
            </ul>
          </div>

          {/* Column 3: Core Technology */}
          <div className="md:col-span-3 space-y-3">
            <div className="font-heading text-sm font-bold uppercase tracking-wider text-paper/90">
              Technology
            </div>
            <ul className="space-y-2 text-sm text-paper/70">
              <li>GradientBoosting Salary Engine</li>
              <li>21,137 Skill Graph Edges</li>
              <li>Multi-Skill Dijkstra Sequencer</li>
              <li>2,000 Monte Carlo Simulation</li>
            </ul>
          </div>

        </div>

        {/* Bottom Bar */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between text-xs text-paper/60 gap-4">
          <div>
            © {new Date().getFullYear()} Switchback Recommender. All Rights Reserved.
          </div>
          <div className="flex items-center gap-6">
            <span>FastAPI + MongoDB + React</span>
            <span>100% Deterministic Core</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
