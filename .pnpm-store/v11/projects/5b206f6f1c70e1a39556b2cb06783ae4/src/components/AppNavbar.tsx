import React from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import logoIcon from '../assets/Switchback_logo_only.webp';
import { useApp } from '../context/AppContext';

export const AppNavbar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { sessionId, resetSession } = useApp();

  const steps = [
    { number: '1', label: 'Skills', path: '/skills' },
    { number: '2', label: 'Target Role', path: '/target-role' },
    { number: '3', label: 'Learning Path', path: '/path' },
    { number: '4', label: 'Dashboard', path: '/dashboard' },
  ];

  const handleNewSession = () => {
    resetSession();
    navigate('/start');
  };

  return (
    <header className="sticky top-0 z-40 bg-paper/95 backdrop-blur-md border-b border-contour/80 py-3 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-8 flex items-center justify-between">
        
        {/* Brand Logo */}
        <Link to="/" className="flex items-center gap-3 group">
          <img
            src={logoIcon}
            alt="Switchback Logo"
            className="w-8 h-8 object-contain transition-transform group-hover:scale-105"
          />
          <span className="font-heading text-lg font-bold tracking-tight text-ink">
            SWITCHBACK
          </span>
        </Link>

        {/* Step Indicator */}
        <nav className="flex items-center gap-1.5 sm:gap-4">
          {steps.map((st, idx) => {
            const isActive = location.pathname === st.path;

            return (
              <React.Fragment key={st.path}>
                <Link
                  to={st.path}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all ${
                    isActive
                      ? 'bg-forest/10 border border-forest/30 text-forest font-semibold'
                      : 'text-muted/70 hover:text-ink font-normal'
                  }`}
                >
                  <span
                    className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-heading font-bold ${
                      isActive ? 'bg-forest text-paper' : 'bg-contour text-muted'
                    }`}
                  >
                    {st.number}
                  </span>
                  <span className="text-xs font-heading hidden sm:inline">
                    {st.label}
                  </span>
                </Link>
                {idx < steps.length - 1 && (
                  <span className="text-contour-dark text-xs hidden sm:inline">→</span>
                )}
              </React.Fragment>
            );
          })}
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-3">
          {sessionId && (
            <button
              onClick={handleNewSession}
              className="text-xs font-heading font-medium text-muted hover:text-forest transition-colors px-2.5 py-1.5 rounded-lg border border-contour/80 hover:border-forest/40"
            >
              Reset Session
            </button>
          )}
        </div>

      </div>
    </header>
  );
};
