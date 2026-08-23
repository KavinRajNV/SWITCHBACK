import React, { useState, useEffect } from 'react';
import logoIcon from '../assets/Switchback_logo_only.webp';

interface NavbarProps {
  onGetStarted: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onGetStarted }) => {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 60);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled
          ? 'bg-paper/95 backdrop-blur-md border-b border-contour/80 shadow-sm py-3'
          : 'bg-transparent py-5'
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 sm:px-8 flex items-center justify-between">
        {/* Logo Icon + Wordmark */}
        <a href="#" className="flex items-center gap-3 group">
          <img
            src={logoIcon}
            alt="Switchback Logo"
            className="w-9 h-9 object-contain transition-transform group-hover:scale-105"
          />
          <span className="font-heading text-xl font-bold tracking-tight text-ink">
            SWITCHBACK
          </span>
        </a>

        {/* Minimalist Navigation Anchors (Part D1: Simplified navbar, zero-LLM link removed) */}
        <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-ink/80">
          <a
            href="#what-we-do"
            className="hover:text-forest transition-colors focus:outline-none focus:ring-2 focus:ring-amber rounded px-2 py-1"
          >
            What We Do
          </a>
          <a
            href="#how-it-works"
            className="hover:text-forest transition-colors focus:outline-none focus:ring-2 focus:ring-amber rounded px-2 py-1"
          >
            How It Works
          </a>
        </nav>

        {/* Primary CTA Button (No Login/Signup per product design) */}
        <button
          onClick={onGetStarted}
          className="bg-forest hover:bg-forest-dark text-paper font-heading text-sm font-semibold px-5 py-2.5 rounded-lg shadow-sm transition-all transform hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-amber"
        >
          Get Started
        </button>
      </div>
    </header>
  );
};
