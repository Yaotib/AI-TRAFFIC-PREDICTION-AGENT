import { useState, useMemo } from 'react';
import HomeScreen from './HomeScreen.jsx';
import MapScreen from './MapScreen.jsx';
import SplitView from './SplitView.jsx';
import Chatbot, { generateAiResponse } from './Chatbot.jsx';
import { computeModel } from './routes.js';
import { PLACES } from './data.js';

// Add ?locfail to the page address to simulate "location unavailable".
// Add ?routefail to simulate "route info unavailable" (the first search fails, Try again works).
const LOCATION_MODE = /[?&]locfail/.test(window.location.search) ? 'fail' : 'demo';

export default function App() {
  const [search, setSearch] = useState(null); // null = not yet selected
  const [viewMode, setViewMode] = useState('chat'); // 'chat' (default) | 'manual' | 'split' | 'map'
  const [plan, setPlan] = useState({
    mode: 'leave',
    leaveTime: '07:15',
    arriveTime: '08:30',
    date: new Date().toISOString().slice(0, 10),
  });
  const [pick, setPick] = useState(null);
  const [messages, setMessages] = useState([]);

  // Compute model based on current search destination and plan
  const destination = search?.destination || PLACES[0];
  const m = useMemo(() => computeModel(destination, plan), [destination, plan]);
  const ready = m && m.ok;
  const selId = ready ? pick || m.rec : null;
  const sel = ready ? m.routes.find((r) => r.id === selId) : null;

  function handleSearch(newSearch) {
    setSearch(newSearch);
    setViewMode('map');
  }

  function handleAskChatbot({ question, from, destination: chosenDest }) {
    const currentSearch = {
      from: from || search?.from || 'Your current location',
      destination: chosenDest || search?.destination || PLACES[0],
    };
    setSearch(currentSearch);

    // Generate AI response
    const reply = generateAiResponse(question, currentSearch.destination, plan, currentSearch.from);
    const userMsg = { sender: 'user', text: question };
    const aiMsg = { sender: 'ai', text: reply.text, weather: reply.weather };

    setMessages((prev) => [...prev, userMsg, aiMsg]);
    if (reply.updatedPlan) {
      setPlan((prev) => ({ ...prev, ...reply.updatedPlan }));
    }
    setViewMode('split');
  }

  function handleSendMessage(text) {
    const activeSearch = search || {
      from: 'Your current location',
      destination: PLACES[0],
    };
    if (!search) setSearch(activeSearch);

    const reply = generateAiResponse(text, activeSearch.destination, plan, activeSearch.from);
    const userMsg = { sender: 'user', text };
    const aiMsg = { sender: 'ai', text: reply.text, weather: reply.weather };

    setMessages((prev) => [...prev, userMsg, aiMsg]);
    if (reply.updatedPlan) {
      setPlan((prev) => ({ ...prev, ...reply.updatedPlan }));
    }
    setViewMode('split');
  }

  function handleBackToHome() {
    setViewMode('chat');
  }

  // 1. Desktop split-screen view (Chatbot on left, Details panel on right)
  if (viewMode === 'split') {
    const activeSearch = search || {
      from: 'Your current location',
      destination: PLACES[0],
    };

    return (
      <SplitView
        search={activeSearch}
        plan={plan}
        setPlan={setPlan}
        m={m}
        ready={ready}
        sel={sel}
        selId={selId}
        onPick={setPick}
        messages={messages}
        onSendMessage={handleSendMessage}
        onBack={handleBackToHome}
        onViewMap={() => setViewMode('map')}
        onStartNavigation={(r) => alert(`Navigating via Route ${r.id} (${r.name})`)}
        onPlanManually={() => setViewMode('manual')}
      />
    );
  }

  // 2. Interactive Map screen (map + bottom sheet)
  if (viewMode === 'map' && search) {
    return (
      <MapScreen
        search={search}
        onBack={() => setViewMode('manual')}
        onOpenChat={() => setViewMode('split')}
        plan={plan}
        setPlan={setPlan}
        pick={pick}
        setPick={setPick}
      />
    );
  }

  // 3. Manual trip planning form (Where to? + From + suggestions)
  if (viewMode === 'manual') {
    return (
      <div className="app">
        <MapBackground />
        <HomeScreen
          locationMode={LOCATION_MODE}
          onSearch={handleSearch}
          onAskChatbot={handleAskChatbot}
          onSwitchToChat={() => setViewMode('chat')}
        />
      </div>
    );
  }

  // 4. Default: Chatbot interface with "Plan trip manually" at top right
  return (
    <div className="app">
      <MapBackground />
      <div className="card chat-card-default">
        <Chatbot
          place={search?.destination || PLACES[0]}
          fromName={search?.from || 'My location'}
          plan={plan}
          onPlanChange={setPlan}
          messages={messages}
          onSendMessage={handleSendMessage}
          onPlanManually={() => setViewMode('manual')}
          isFullPane={false}
        />
      </div>
    </div>
  );
}

// Subtle illustrative map behind the home card (decorative only).
function MapBackground() {
  return (
    <svg className="map-bg" viewBox="0 0 800 520" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <rect width="800" height="520" fill="#E8EFEF" />
      <rect x="40" y="52" width="160" height="112" rx="26" fill="#D4E8DA" />
      <rect x="570" y="360" width="170" height="100" rx="24" fill="#D4E8DA" />
      <path
        d="M0 60H800M0 130H800M0 200H800M0 340H800M0 410H800M0 480H800M60 0V520M150 0V520M240 0V520M330 0V520M420 0V520M510 0V520M600 0V520M690 0V520"
        stroke="#fff"
        strokeWidth="4"
        fill="none"
      />
      <path d="M0 520L260 330L520 190L800 70" stroke="#F7EFD2" strokeWidth="9" fill="none" strokeLinecap="round" />
      <path
        d="M0 250C120 200 240 330 400 300S640 220 800 300"
        stroke="#C9E0EA"
        strokeWidth="46"
        fill="none"
        strokeLinecap="round"
      />
    </svg>
  );
}
