import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { askQA } from '../lib/api';
import mapIcon from '../assets/Minimalist_Hiking_Map_Icon.webp';

interface QAMessage {
  id: string;
  questionText: string;
  answerText: string;
  payload?: any;
  timestamp: string;
}

export const QAPanel: React.FC = () => {
  const { sessionId } = useApp();
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<QAMessage[]>([]);
  const [selectedExtraSkill, setSelectedExtraSkill] = useState('');

  const questions = [
    { id: 'why_this_skill', label: 'Why is this milestone skill recommended?' },
    { id: 'how_long_will_this_take', label: 'How long will this path take?' },
    { id: 'what_if_i_already_know_x', label: 'What if I already know Python/SQL?' },
    { id: 'show_free_alternatives', label: 'Show free course options' },
    { id: 'why_this_role', label: 'Why target this career role?' },
    { id: 'am_i_qualified_already', label: 'Am I already qualified for this role?' },
    { id: 'what_skills_do_i_already_have', label: 'What skills do I already possess?' },
    { id: 'explain_confidence_score', label: 'Explain my skill confidence score' },
  ];

  const handleAsk = async (qId: string, label: string) => {
    if (!sessionId) {
      alert('Please start a session first on the Entry screen.');
      return;
    }

    setLoading(true);
    try {
      const extraSkill = qId === 'what_if_i_already_know_x' ? (selectedExtraSkill || 'Python') : undefined;
      const res = await askQA(sessionId, qId, extraSkill);

      const newMsg: QAMessage = {
        id: Math.random().toString(),
        questionText: label,
        answerText: res.answer_text,
        payload: res.structured_payload,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [newMsg, ...prev]);
    } catch (err: any) {
      alert(err.message || 'Failed to fetch Q&A answer.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating Trigger Button (Visible on all in-app screens) */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-50 bg-forest hover:bg-forest-dark text-paper font-heading text-sm font-semibold px-4 py-3 rounded-full shadow-xl flex items-center gap-2.5 transition-all transform hover:scale-105 border border-paper/20 focus:outline-none focus:ring-2 focus:ring-amber"
      >
        <img src={mapIcon} alt="Assistant Map Icon" className="w-6 h-6 object-contain" />
        <span>Ask Assistant</span>
        {messages.length > 0 && (
          <span className="w-5 h-5 rounded-full bg-amber text-paper text-xs flex items-center justify-center font-bold">
            {messages.length}
          </span>
        )}
      </button>

      {/* Slide-in Q&A Panel Drawer */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          {/* Backdrop */}
          <div
            onClick={() => setIsOpen(false)}
            className="fixed inset-0 bg-ink/40 backdrop-blur-xs transition-opacity"
          />

          {/* Drawer Body */}
          <div className="relative w-full max-w-md bg-paper h-full shadow-2xl flex flex-col border-l border-contour z-10 overflow-hidden">
            {/* Drawer Header */}
            <div className="bg-forest text-paper p-5 flex items-center justify-between shadow-xs">
              <div className="flex items-center gap-3">
                <img src={mapIcon} alt="Map Icon" className="w-7 h-7 object-contain" />
                <div>
                  <h3 className="font-heading text-lg font-bold">Trail Assistant</h3>
                  <p className="text-xs text-paper/80">Constrained Deterministic Q&A Engine</p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="text-paper/80 hover:text-paper text-xl font-bold p-1 focus:outline-none"
              >
                ✕
              </button>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6">
              
              {/* Question Selection Grid */}
              <div className="space-y-2">
                <div className="text-xs font-heading font-bold uppercase tracking-wider text-muted">
                  Select a Inquiry Topic
                </div>
                <div className="grid grid-cols-1 gap-2">
                  {questions.map((q) => (
                    <button
                      key={q.id}
                      onClick={() => handleAsk(q.id, q.label)}
                      disabled={loading}
                      className="text-left p-3 rounded-xl bg-paper-dark/60 border border-contour/80 hover:border-forest/40 hover:bg-paper text-xs font-medium text-ink transition-all disabled:opacity-50"
                    >
                      {q.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Extra skill parameter for What-if */}
              <div className="p-3 rounded-xl bg-amber/10 border border-amber/30 text-xs space-y-2">
                <div className="font-semibold text-amber-dark">Optional Parameter for "What-if" Inquiry:</div>
                <input
                  type="text"
                  placeholder="Enter skill (e.g. Python, SQL)"
                  value={selectedExtraSkill}
                  onChange={(e) => setSelectedExtraSkill(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-paper border border-contour text-ink text-xs focus:outline-none focus:ring-1 focus:ring-amber"
                />
              </div>

              {/* Network Loading State (Real network spinner, zero fake typing delay!) */}
              {loading && (
                <div className="flex items-center justify-center p-6 space-x-3 bg-paper-dark/30 rounded-xl border border-contour/60">
                  <div className="w-5 h-5 border-2 border-forest border-t-transparent rounded-full animate-spin" />
                  <span className="text-xs text-forest font-medium">Executing deterministic query...</span>
                </div>
              )}

              {/* Transcript View */}
              <div className="space-y-4 pt-2">
                <div className="text-xs font-heading font-bold uppercase tracking-wider text-muted">
                  Q&A Transcript ({messages.length})
                </div>

                {messages.length === 0 && !loading && (
                  <div className="text-center py-8 text-xs text-muted/70 italic">
                    Tap any topic above to query the recommender model.
                  </div>
                )}

                {messages.map((m) => (
                  <div key={m.id} className="space-y-2 p-4 rounded-xl bg-paper border border-contour/80 shadow-xs">
                    <div className="flex items-center justify-between text-xs text-forest font-semibold border-b border-contour/60 pb-1.5">
                      <span>Q: {m.questionText}</span>
                      <span className="text-muted text-[10px]">{m.timestamp}</span>
                    </div>
                    <p className="text-xs text-ink/90 whitespace-pre-wrap leading-relaxed">
                      {m.answerText}
                    </p>
                  </div>
                ))}
              </div>

            </div>
          </div>
        </div>
      )}
    </>
  );
};
