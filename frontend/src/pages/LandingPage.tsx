import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { Hero } from '../components/Hero';
import { ScrollTrail } from '../components/ScrollTrail';
import { Services } from '../components/Services';
import { HowItWorks } from '../components/HowItWorks';
import { Footer } from '../components/Footer';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  const handleGetStarted = () => {
    navigate('/start');
  };

  return (
    <div className="relative min-h-screen bg-paper text-ink overflow-x-hidden">
      {/* Signature Scroll Trail Line & Runner Animation */}
      <ScrollTrail />

      {/* Marketing Header Navbar */}
      <Navbar onGetStarted={handleGetStarted} />

      {/* Main Page Content */}
      <main className="relative z-10">
        <Hero onGetStarted={handleGetStarted} />
        <Services />
        <HowItWorks onGetStarted={handleGetStarted} />
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
};
