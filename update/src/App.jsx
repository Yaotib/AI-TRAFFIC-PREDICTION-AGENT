import { useState } from 'react';
import HomeScreen from './HomeScreen.jsx';
import MapScreen from './MapScreen.jsx';

// Add ?locfail to the page address to simulate "location unavailable".
// Add ?routefail to simulate "route info unavailable" (the first search fails, Try again works).
const LOCATION_MODE = /[?&]locfail/.test(window.location.search) ? 'fail' : 'demo';

export default function App() {
  const [search, setSearch] = useState(null); // null = home screen

  if (search) return <MapScreen search={search} onBack={() => setSearch(null)} />;
  return (
    <div className="app">
      <MapBackground />
      <HomeScreen locationMode={LOCATION_MODE} onSearch={setSearch} />
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
      <path d="M0 60H800M0 130H800M0 200H800M0 340H800M0 410H800M0 480H800M60 0V520M150 0V520M240 0V520M330 0V520M420 0V520M510 0V520M600 0V520M690 0V520" stroke="#fff" strokeWidth="4" fill="none" />
      <path d="M0 520L260 330L520 190L800 70" stroke="#F7EFD2" strokeWidth="9" fill="none" strokeLinecap="round" />
      <path d="M0 250C120 200 240 330 400 300S640 220 800 300" stroke="#C9E0EA" strokeWidth="46" fill="none" strokeLinecap="round" />
    </svg>
  );
}
