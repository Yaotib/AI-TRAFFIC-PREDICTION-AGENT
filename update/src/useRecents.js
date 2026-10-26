import { useState } from 'react';
import { DEFAULT_RECENTS } from './data.js';

const KEY = 'wayline.recents';

function read() {
  try {
    const r = JSON.parse(localStorage.getItem(KEY) || 'null');
    if (Array.isArray(r) && r.length) return r;
  } catch (e) { /* storage blocked: fall back to defaults */ }
  return DEFAULT_RECENTS;
}

// Remembers the last 3 chosen places in this browser only.
export function useRecents() {
  const [recents, setRecents] = useState(read);
  const addRecent = (id) => {
    const next = [id, ...recents.filter((x) => x !== id)].slice(0, 3);
    setRecents(next);
    try { localStorage.setItem(KEY, JSON.stringify(next)); } catch (e) { /* ignore */ }
  };
  return [recents, addRecent];
}
