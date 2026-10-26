import { useEffect, useState } from 'react';
import HomeScreen from './HomeScreen.jsx';

// Add ?locfail to the page address to simulate "location unavailable".
const LOCATION_MODE = /[?&]locfail/.test(window.location.search) ? 'fail' : 'demo';

// INTEGRATION POINT: replace this with the real map screen.
function MapPlaceholder({ search, onBack }) {
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 1100);
    return () => clearTimeout(t);
  }, []);
  return (
    <section className="card" aria-label="Finding routes">
      <div role="status">
        {loading ? (
          <div className="loading">
            <span className="dots" aria-hidden="true"><span /><span /><span /></span>
            <b>Finding routes to {search.destination.name}</b>
          </div>
        ) : (
          <p>The map screen goes here. From: {search.from} · To: {search.destination.name}</p>
        )}
      </div>
      <div className="row"><button type="button" className="btn" onClick={onBack}>Back to search</button></div>
    </section>
  );
}

export default function App() {
  const [search, setSearch] = useState(null); // null = home screen

  return (
    <div className="app">
      <MapBackground />
      {search ? (
        <MapPlaceholder search={search} onBack={() => setSearch(null)} />
      ) : (
        <HomeScreen locationMode={LOCATION_MODE} onSearch={setSearch} />
      )}
    </div>
  );
}

// Subtle illustrative map behind the card (decorative only).
function MapBackground() {
  return (
    <svg className="map-bg" viewBox="0 0 800 520" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <rect width="800" height="520" fill="#E8EFEF" />
      <rect x="40" y="52" width="160" height="112" rx="26" fill="#D4E8DA" />
      <rect x="570" y="360" width="170" height="100" rx="24" fill="#D4E8DA" />
      <path d="M0 60H800M0 130H800M0 200H800M0 340H800M0 410H800M0 480H800M60 0V520M150 0V520M240 0V520M330 0V520M420 0V520M510 0V520M600 0V520M690 0V520" stroke="#fff" strokeWidth="4" fill="none" />
      <path d="M0 520L260 330L520 190L800 70" stroke="#F7EFD2" strokeWidth="9" fill="none" strokeLinecap="round" />
      <path d="M0 250C120 200 240 330 400 300S640 220 800 300" stroke="#C9E0EA" strokeWidth="46" fill="none" strokeLinecap="round" />
    </svg>
  );
}
