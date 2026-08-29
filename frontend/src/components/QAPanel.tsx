import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useApp } from '../context/AppContext';
import { sendAssistantMessage } from '../lib/api';
import type { ChatTurn } from '../lib/api';
import mapIcon from '../assets/Minimalist_Hiking_Map_Icon.webp';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  rationale?: string;
  payload?: any;
  intent?: string;
  timestamp: string;
}

const STARTER_PROMPTS = [
  'How long will this path take?',
  'Am I qualified for this role yet?',
  'Why is my next skill on the path?',
  'Any free courses for my next skill?',
];

/**
 * Other screens open the assistant with a pre-filled question via:
 *   window.dispatchEvent(new CustomEvent('switchback:ask', { detail: 'why this role?' }))
 */
export const QAPanel: React.FC = () => {
  const { sessionId } = useApp();
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>(STARTER_PROMPTS);
  const scrollRef = useRef<HTMLDivElement>(null);
  const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const ask = useCallback(
    async (question: string) => {
      const q = question.trim();
      if (!q || loading) return;
      if (!sessionId) {
        setMessages((prev) => [
          ...prev,
          { id: Math.random().toString(), role: 'assistant', text: 'Start a session on the entry screen first, then I can help.', timestamp: now() },
        ]);
        return;
      }

      const history: ChatTurn[] = messages.map((m) => ({ role: m.role, content: m.text }));
      setMessages((prev) => [...prev, { id: Math.random().toString(), role: 'user', text: q, timestamp: now() }]);
      setInput('');
      setLoading(true);
      try {
        const res = await sendAssistantMessage(sessionId, q, history);
        setMessages((prev) => [
          ...prev,
          {
            id: Math.random().toString(),
            role: 'assistant',
            text: res.reply,
            rationale: res.rationale,
            payload: res.structured_payload,
            intent: res.intent,
            timestamp: now(),
          },
        ]);
        if (res.suggestions?.length) setSuggestions(res.suggestions);
      } catch (err: any) {
        setMessages((prev) => [
          ...prev,
          { id: Math.random().toString(), role: 'assistant', text: err.message || 'The assistant is unavailable right now.', timestamp: now() },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [sessionId, messages, loading]
  );

  // Let other screens pop the assistant open with a question.
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      setIsOpen(true);
      if (typeof detail === 'string' && detail.trim()) {
        // defer so the panel is mounted before we send
        setTimeout(() => ask(detail), 50);
      }
    };
    window.addEventListener('switchback:ask', handler);
    return () => window.removeEventListener('switchback:ask', handler);
  }, [ask]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loading]);

  const renderPayload = (m: Message) => {
    const p = m.payload;
    if (!p) return null;
    if (Array.isArray(p.courses) && p.courses.length > 0) {
      return (
        <ul className="mt-2 space-y-1">
          {p.courses.slice(0, 4).map((c: any, i: number) => (
            <li key={i} className="text-[11px]">
              <a href={c.url || '#'} target="_blank" rel="noreferrer" className="text-forest hover:underline">
                {c.title}
              </a>{' '}
              <span className="text-muted">· {c.source}</span>
            </li>
          ))}
        </ul>
      );
    }
    if (p.milestones_saved !== undefined && p.new_path_length !== undefined) {
      return (
        <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
          <span className="px-2 py-0.5 rounded-full bg-paper-dark border border-contour">was {p.original_path_length}</span>
          <span className="px-2 py-0.5 rounded-full bg-forest/10 text-forest border border-forest/20">now {p.new_path_length}</span>
          <span className="px-2 py-0.5 rounded-full bg-amber/10 text-amber-dark border border-amber/30">saves {p.milestones_saved}</span>
        </div>
      );
    }
    return null;
  };

  return (
    <>
      {/* Floating trigger */}
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="fixed bottom-6 right-6 z-50 bg-forest hover:bg-forest-dark text-paper font-heading text-sm font-semibold px-4 py-3 rounded-full shadow-xl flex items-center gap-2.5 transition-all transform hover:scale-105 border border-paper/20 focus:outline-none focus:ring-2 focus:ring-amber"
      >
        <img src={mapIcon} alt="" className="w-6 h-6 object-contain" />
        <span>Ask Assistant</span>
        {messages.filter((m) => m.role === 'assistant').length > 0 && (
          <span className="w-5 h-5 rounded-full bg-amber text-paper text-xs flex items-center justify-center font-bold">
            {messages.filter((m) => m.role === 'assistant').length}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div onClick={() => setIsOpen(false)} className="fixed inset-0 bg-ink/40 backdrop-blur-xs transition-opacity" />

          <div className="relative w-full max-w-md bg-paper h-full shadow-2xl flex flex-col border-l border-contour z-10 overflow-hidden">
            {/* Header */}
            <div className="bg-forest text-paper p-5 flex items-center justify-between shadow-xs">
              <div className="flex items-center gap-3">
                <img src={mapIcon} alt="" className="w-7 h-7 object-contain" />
                <div>
                  <h3 className="font-heading text-lg font-bold">Trail Assistant</h3>
                  <p className="text-xs text-paper/80">Grounded, explainable answers</p>
                </div>
              </div>
              <button onClick={() => setIsOpen(false)} className="text-paper/80 hover:text-paper text-xl font-bold p-1 focus:outline-none">
                ✕
              </button>
            </div>

            {/* Transcript */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 && (
                <p className="text-center py-6 text-xs text-muted/70 italic">
                  Ask anything about your plan — timeline, gaps, why a skill is recommended, free courses…
                </p>
              )}

              {messages.map((m) =>
                m.role === 'user' ? (
                  <div key={m.id} className="flex justify-end">
                    <div className="max-w-[80%] bg-forest text-paper text-xs rounded-2xl rounded-br-sm px-3.5 py-2.5 leading-relaxed">
                      {m.text}
                    </div>
                  </div>
                ) : (
                  <div key={m.id} className="flex justify-start">
                    <div className="max-w-[85%] space-y-1">
                      {m.rationale && <div className="text-[10px] text-muted italic px-1">{m.rationale}</div>}
                      <div className="bg-paper-dark/70 border border-contour/80 text-ink text-xs rounded-2xl rounded-bl-sm px-3.5 py-2.5 leading-relaxed whitespace-pre-wrap">
                        {m.text}
                        {renderPayload(m)}
                      </div>
                    </div>
                  </div>
                )
              )}

              {loading && (
                <div className="flex justify-start">
                  <div className="bg-paper-dark/70 border border-contour/80 rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-2">
                    <div className="w-3.5 h-3.5 border-2 border-forest border-t-transparent rounded-full animate-spin" />
                    <span className="text-[11px] text-forest">Checking your data…</span>
                  </div>
                </div>
              )}
            </div>

            {/* Suggestions */}
            {suggestions.length > 0 && !loading && (
              <div className="px-4 pb-2 flex flex-wrap gap-1.5">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => ask(s)}
                    className="text-[11px] px-2.5 py-1 rounded-full bg-paper-dark/60 border border-contour/80 text-ink hover:border-forest/40 hover:text-forest transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}

            {/* Composer */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                ask(input);
              }}
              className="p-3 border-t border-contour flex items-center gap-2"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question…"
                className="flex-1 px-3.5 py-2.5 rounded-xl bg-paper-dark/40 border border-contour text-ink text-xs focus:outline-none focus:ring-2 focus:ring-amber"
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="bg-forest hover:bg-forest-dark text-paper text-xs font-semibold px-4 py-2.5 rounded-xl disabled:opacity-50"
              >
                Send
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
};
