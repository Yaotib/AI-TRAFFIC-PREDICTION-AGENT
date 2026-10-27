import { useState, useRef, useEffect } from 'react';
import { BASE, SLOT0, f12, toTimeValue, computeModel } from './routes.js';

export const EXAMPLE_QUESTIONS = [
  'What is the best time to travel between my origin and destination?',
  'If I need to arrive by 8:30 AM, when should I leave?',
  'Which route has the least traffic right now?',
];

export function generateAiResponse(query, place, currentPlan, fromName = 'My location') {
  const q = query.toLowerCase();
  const destName = place?.name || 'Harbour Station';

  // 1. "Arrive by" question (e.g. 8:30 AM)
  if (q.includes('arrive') || q.includes('8:30') || q.includes('when should i leave')) {
    const arrivePlan = { mode: 'arrive', arriveTime: '08:30', date: currentPlan?.date || new Date().toISOString().slice(0, 10) };
    const m = computeModel(place, arrivePlan);
    if (m.ok) {
      const recR = m.routes.find((r) => r.id === m.rec);
      const leaveFormatted = f12(m.dep);
      const tripMin = recR.min;
      const arriveFormatted = f12(m.dep + tripMin);
      const spareMin = m.D - (m.dep + tripMin);
      return {
        text: `To arrive by 8:30 AM, leave at ${leaveFormatted}. The simulated trip takes about ${tripMin} minutes, arriving at ${arriveFormatted} with ${spareMin} minutes to spare.`,
        weather: 'Weather: context, not traffic data. Sample: partly cloudy, 27 °C.',
        updatedPlan: arrivePlan,
      };
    }
  }

  // 2. "Best time" question
  if (q.includes('best time') || q.includes('when to travel') || q.includes('optimal')) {
    const defaultPlan = { mode: 'leave', leaveTime: '07:15', date: currentPlan?.date || new Date().toISOString().slice(0, 10) };
    const m = computeModel(place, defaultPlan);
    if (m.ok) {
      const bestTimeFormatted = f12(SLOT0 + 15 * m.bestI);
      const bestMin = m.mins[m.bestI];
      const recName = BASE[m.rec]?.name || 'Ridge Expressway';
      return {
        text: `The best time to travel between ${fromName} and ${destName} is at ${bestTimeFormatted}. At this time, the simulated trip takes about ${bestMin} minutes on Route ${m.rec} (${recName}) before heavier peak congestion builds.`,
        weather: 'Weather: context, not traffic data. Sample: partly cloudy, 27 °C.',
        updatedPlan: { mode: 'leave', leaveTime: toTimeValue(SLOT0 + 15 * m.bestI), date: defaultPlan.date },
      };
    }
  }

  // 3. "Least traffic" / "fastest" route
  if (q.includes('traffic') || q.includes('fastest') || q.includes('quickest') || q.includes('route')) {
    const m = computeModel(place, currentPlan || { mode: 'leave', leaveTime: '07:15' });
    if (m.ok) {
      const recR = m.routes.find((r) => r.id === m.rec);
      const others = m.routes.filter((r) => r.id !== m.rec);
      const otherStr = others.map((r) => `Route ${r.id} (${r.min} min, ${r.lvl.toLowerCase()} traffic)`).join(' and ');
      return {
        text: `Route ${m.rec} (${recR.name}) currently has the lowest congestion (${recR.lvl.toLowerCase()} traffic) at ${recR.min} minutes (${recR.km} km). Alternatives include ${otherStr}.`,
        weather: 'Weather: context, not traffic data. Sample: partly cloudy, 27 °C.',
        updatedPlan: currentPlan,
      };
    }
  }

  // 4. Default dynamic AI response
  const m = computeModel(place, currentPlan || { mode: 'leave', leaveTime: '07:15' });
  const recR = m.ok ? m.routes.find((r) => r.id === m.rec) : null;
  const min = recR ? recR.min : 27;
  const recId = m.ok ? m.rec : '1';
  const recName = recR ? recR.name : 'Ridge Expressway';

  return {
    text: `For your trip from ${fromName} to ${destName}, Route ${recId} (${recName}) is currently recommended with an estimated travel time of ${min} minutes. Traffic is simulated for Accra morning peak hours.`,
    weather: 'Weather: context, not traffic data. Sample: partly cloudy, 27 °C.',
    updatedPlan: currentPlan,
  };
}

/**
 * Chatbot component supporting both embedded and full panel modes.
 */
export default function Chatbot({
  place,
  fromName = 'My location',
  plan,
  onPlanChange,
  messages = [],
  onSendMessage,
  isFullPane = false,
  onClose,
  onPlanManually,
}) {
  const [inputVal, setInputVal] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (messagesEndRef.current && isFullPane) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isFullPane]);

  function handleSend(text) {
    const trimmed = (text || inputVal).trim();
    if (!trimmed) return;
    setInputVal('');
    if (onSendMessage) {
      onSendMessage(trimmed);
    }
  }

  return (
    <div className={`chatbot-container${isFullPane ? ' full-pane' : ''}`}>
      {/* Top Header with Brand and 'Plan trip manually' button at top right */}
      <div className="chat-header">
        <div className="brand">
          <svg width="30" height="30" viewBox="0 0 36 36" role="img" aria-label="Wayline logo">
            <rect width="36" height="36" rx="11" fill="#0B1F3A" />
            <path d="M9 26 C17 26 13 10 27 10" fill="none" stroke="#2FD0BC" strokeWidth="3" strokeLinecap="round" />
            <circle cx="9" cy="26" r="2.8" fill="#fff" />
            <circle cx="27" cy="10" r="2.8" fill="#fff" />
          </svg>
          <div className="chat-titles">
            <b>Wayline</b>
            <span className="badge">Prototype · simulated data</span>
          </div>
        </div>
        <div className="row tight" style={{ marginLeft: 'auto' }}>
          {onPlanManually && (
            <button
              type="button"
              className="btn small manual-plan-btn"
              onClick={onPlanManually}
              aria-label="Plan trip manually with form"
            >
              Plan trip manually
            </button>
          )}
          {onClose && (
            <button type="button" className="iconbtn" aria-label="Close assistant" onClick={onClose}>
              <svg width="20" height="20" viewBox="0 0 24 24" stroke="#0B1F3A" strokeWidth="2.2" fill="none" strokeLinecap="round">
                <path d="M6 6l12 12M18 6L6 18" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Recommendations / Example questions */}
      <div className="chat-recommendations">
        <span className="cap">Try an example question</span>
        <div className="example-questions-list">
          {EXAMPLE_QUESTIONS.map((q, idx) => (
            <button
              key={idx}
              type="button"
              className="example-question-btn"
              onClick={() => handleSend(q)}
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Messages area */}
      {messages.length > 0 && (
        <div className="chat-messages-area">
          {messages.map((msg, i) => (
            <div key={i} className={`chat-message-row ${msg.sender}`}>
              {msg.sender === 'user' ? (
                <div className="user-bubble">{msg.text}</div>
              ) : (
                <div className="ai-response-card">
                  <div className="ai-badge">AI explanation</div>
                  <p className="ai-subtext">Simulated in this prototype: no real AI is connected.</p>
                  <p className="ai-body">{msg.text}</p>
                  {msg.weather && (
                    <div className="weather-card">
                      <b>Weather: context, not traffic data.</b> Sample: partly cloudy, 27 °C.
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input bar */}
      <form
        className="chat-input-row"
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
      >
        <input
          type="text"
          className="chat-input-field"
          placeholder="Ask about your trip..."
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          aria-label="Ask about your trip"
        />
        <button type="submit" className="chat-send-btn">
          Send
        </button>
      </form>
    </div>
  );
}
