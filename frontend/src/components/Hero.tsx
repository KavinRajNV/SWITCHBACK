import React, { useState, useEffect } from 'react';
import heroBg from '../assets/Landing_page_background.webp';
import trailMarker from '../assets/Minimalist_Forest_Trail_Marker.webp';

interface HeroProps {
  onGetStarted: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onGetStarted }) => {
  const fullText = "SWITCHBACK";
  const [displayedText, setDisplayedText] = useState("");
  const [isTypingComplete, setIsTypingComplete] = useState(false);

  useEffect(() => {
    let index = 0;
    const interval = setInterval(() => {
      if (index < fullText.length) {
        setDisplayedText(fullText.slice(0, index + 1));
        index++;
      } else {
        setIsTypingComplete(true);
        clearInterval(interval);
      }
    }, 120);

    return () => clearInterval(interval);
  }, []);

  return (
    <section className="relative min-h-screen flex items-center justify-center pt-24 pb-20 overflow-hidden">
      {/* Background Image */}
      <div className="absolute inset-0 z-0">
        <img
          src={heroBg}
          alt="Switchback Mountain Trail Hiker Background"
          className="w-full h-full object-cover object-center"
        />
        {/* Part C: Narrow left-side text scrim covering strictly behind the text block (sm:w-5/12), leaving hiker figure in lower/center-left clear */}
        <div className="absolute inset-y-0 left-0 w-full sm:w-5/12 bg-gradient-to-r from-paper/95 via-paper/75 to-transparent z-10 pointer-events-none" />
        <div className="absolute inset-0 bg-paper/20 sm:hidden" />
      </div>

      {/* Part C: Concentrated bottom blend gradient strictly at the last ~10-15% edge (h-16), fading hero into paper background without washing out hiker */}
      <div className="absolute bottom-0 inset-x-0 h-16 bg-gradient-to-t from-paper to-transparent z-10 pointer-events-none" />

      {/* Content Container */}
      <div className="relative z-20 max-w-7xl mx-auto px-6 sm:px-8 w-full">
        <div className="max-w-2xl">
          
          {/* Typewriter Wordmark Title */}
          <h1 className="font-heading text-6xl sm:text-8xl font-bold tracking-tight text-ink mb-6 flex items-center gap-2 min-h-[5rem]">
            <span>{displayedText}</span>
            {/* Custom Trail-Post Cursor */}
            <span className="inline-block align-middle ml-1">
              <img
                src={trailMarker}
                alt="Trail Marker Cursor"
                className={`w-7 h-10 object-contain inline-block transition-opacity duration-300 ${
                  isTypingComplete ? 'animate-bounce' : 'opacity-100'
                }`}
              />
            </span>
          </h1>

          {/* Subheading / Tagline (Part B: Weaved 84,000+ job postings inline stat; Part D2: Mention #1 of Zero-LLM) */}
          <p className="text-lg sm:text-xl font-normal text-ink/90 leading-relaxed mb-10">
            A personalized learning-path recommender built on <strong className="font-semibold text-forest">84,000+ real job postings</strong>, trained salary models, and deterministic graph algorithms — zero LLM API calls.
          </p>

          {/* CTA Group */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
            <button
              onClick={onGetStarted}
              className="bg-forest hover:bg-forest-dark text-paper font-heading text-base font-semibold px-8 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all transform hover:-translate-y-0.5 text-center focus:outline-none focus:ring-2 focus:ring-amber"
            >
              Get Started
            </button>
            <a
              href="#how-it-works"
              className="bg-paper/90 hover:bg-paper text-ink border border-contour-dark font-heading text-base font-semibold px-6 py-4 rounded-xl transition-all text-center focus:outline-none focus:ring-2 focus:ring-amber"
            >
              Explore Trail Logic
            </a>
          </div>

          {/* Part B: Hero stats row removed entirely for visual calm & uncluttered focus */}

        </div>
      </div>
    </section>
  );
};
