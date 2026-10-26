import { useId, useMemo, useRef, useState } from 'react';
import { buildOptions } from './data.js';
import { useRecents } from './useRecents.js';

const LOC_FAIL_MSG = "We couldn't find your location. Enter a starting point instead.";

/**
 * Home screen: "Where to?" + start point + suggestions.
 * Props:
 *   onSearch({ from, destination })  called when the user picks a destination
 *   locationMode                     'demo' (works) or 'fail' (simulates location unavailable)
 */
export default function HomeScreen({ onSearch, locationMode = 'demo' }) {
  const listId = useId();
  const destRef = useRef(null);
  const fromRef = useRef(null);

  const [recents, addRecent] = useRecents();
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(-1);
  const [destError, setDestError] = useState('');

  // Start point: 'loc' = demo current location, 'text' = typed by the user, 'none' = location unavailable
  const failed = locationMode === 'fail';
  const [from, setFrom] = useState({ mode: failed ? 'none' : 'loc', text: '' });
  const [editing, setEditing] = useState(failed);
  const [fromDraft, setFromDraft] = useState('');
  const [fromError, setFromError] = useState(failed ? LOC_FAIL_MSG : '');

  const options = useMemo(() => buildOptions(query, recents), [query, recents]);

  const fromLabel = from.mode === 'loc' ? 'Your current location' : from.mode === 'text' ? from.text : 'Starting point needed';
  const fromHint = from.mode === 'loc' ? 'Demo location. Wayline does not read real GPS.' : from.mode === 'text' ? 'Entered by you' : 'Location unavailable';

  function openEditor(message = '') {
    setEditing(true);
    setFromError(message);
    setTimeout(() => fromRef.current && fromRef.current.focus(), 0);
  }

  function useMyLocation() {
    if (locationMode === 'fail') {
      setFrom({ mode: 'none', text: '' });
      openEditor(LOC_FAIL_MSG);
      return;
    }
    // INTEGRATION POINT: a real build would call navigator.geolocation here, with the user's permission.
    setFrom({ mode: 'loc', text: '' });
    setEditing(false);
    setFromError('');
  }

  function saveFrom() {
    const t = fromDraft.trim();
    if (!t) { setFromError('Enter a starting point.'); return; }
    setFrom({ mode: 'text', text: t.slice(0, 40) });
    setEditing(false);
    setFromError('');
  }

  function choose(place) {
    if (from.mode === 'none') {
      openEditor("We couldn't find your location. Enter a starting point to continue.");
      return;
    }
    if (place.id !== 'custom') addRecent(place.id);
    onSearch({ from: from.mode === 'loc' ? 'Your current location' : from.text, destination: place });
  }

  function onKeyDown(e) {
    const n = options.length;
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive((active + 1) % n); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((active - 1 + n) % n); }
    else if (e.key === 'Escape') { setQuery(''); setActive(-1); }
    else if (e.key === 'Enter') {
      e.preventDefault();
      if (!query.trim() && active < 0) { setDestError('Enter a destination to see routes.'); return; }
      const o = options[active >= 0 ? active : 0];
      if (o) choose(o.place);
    }
  }

  return (
    <section className="card" aria-label="Where to?">
      <div className="brand">
        <Logo />
        <b>Wayline</b>
        <span className="badge">Prototype · simulated data</span>
      </div>

      <div>
        <label className="cap" htmlFor="dest">Where to?</label>
        <div className={`field big${destError ? ' invalid' : ''}`}>
          <SearchIcon />
          <input
            id="dest" ref={destRef} type="text" placeholder="Where to?" autoComplete="off"
            role="combobox" aria-expanded={options.length > 0} aria-controls={listId} aria-autocomplete="list"
            aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
            aria-describedby="dest-err"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setActive(-1); setDestError(''); }}
            onKeyDown={onKeyDown}
          />
          {query && (
            <button type="button" className="clear" aria-label="Clear destination"
              onClick={() => { setQuery(''); setActive(-1); destRef.current.focus(); }}>
              <CloseIcon />
            </button>
          )}
        </div>
        <p className="err" id="dest-err" role="alert">{destError}</p>
      </div>

      <div>
        <div className="from">
          <span className="ico" aria-hidden="true"><TargetIcon /></span>
          <div className="t">
            <span className="cap small">From</span>
            <b>{fromLabel}</b>
            <small>{fromHint}</small>
          </div>
          <button type="button" className="link" aria-expanded={editing} aria-controls="from-editor"
            onClick={() => (editing ? setEditing(false) : openEditor())}>
            {from.mode === 'none' ? 'Enter' : 'Change'}
          </button>
        </div>

        {editing && (
          <div className="editor" id="from-editor">
            <label className="cap small" htmlFor="from-input">Starting point</label>
            <div className={`field${fromError ? ' invalid' : ''}`}>
              <input id="from-input" ref={fromRef} type="text" placeholder="Enter a starting point" autoComplete="off"
                aria-describedby="from-err" value={fromDraft}
                onChange={(e) => { setFromDraft(e.target.value); setFromError(''); }}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); saveFrom(); } }} />
            </div>
            <p className="err" id="from-err" role="alert">{fromError}</p>
            <div className="row">
              <button type="button" className="btn small" onClick={saveFrom}>Use this start</button>
              <button type="button" className="link" onClick={useMyLocation}>Use my location</button>
            </div>
            <p className="note">Demo only: Wayline does not read your real location. An example location is used.</p>
          </div>
        )}
      </div>

      <div>
        <div className="cap" id={`${listId}-title`} style={{ padding: '0 4px 4px' }}>{query.trim() ? 'Suggestions' : 'Recent places'}</div>
        <ul className="list" id={listId} role="listbox" aria-labelledby={`${listId}-title`}>
          {options.map((o, i) => (
            <li key={o.place.id + i} id={`${listId}-${i}`} className="opt" role="option" aria-selected={i === active}
              onMouseDown={(e) => e.preventDefault()} onClick={() => choose(o.place)}>
              <span className="ico" aria-hidden="true">{o.recent ? <ClockIcon /> : <PinIcon />}</span>
              <span className="t"><b>{o.place.name}</b><span>{o.sub}</span></span>
            </li>
          ))}
        </ul>
      </div>

      <p className="note">Sample data only. No GPS, live traffic or map service is connected.</p>
    </section>
  );
}

/* ---- small inline icons (decorative) ---- */
const base = { fill: 'none', strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true };
const Logo = () => (
  <svg width="32" height="32" viewBox="0 0 36 36" role="img" aria-label="Wayline logo">
    <rect width="36" height="36" rx="11" fill="#0B1F3A" />
    <path d="M9 26 C17 26 13 10 27 10" fill="none" stroke="#2FD0BC" strokeWidth="3" strokeLinecap="round" />
    <circle cx="9" cy="26" r="2.8" fill="#fff" /><circle cx="27" cy="10" r="2.8" fill="#fff" />
  </svg>
);
const SearchIcon = () => <svg width="22" height="22" viewBox="0 0 24 24" stroke="#0B1F3A" strokeWidth="2.2" {...base}><circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" /></svg>;
const CloseIcon = () => <svg width="18" height="18" viewBox="0 0 24 24" stroke="#4A5B70" strokeWidth="2.2" {...base}><path d="M6 6l12 12M18 6L6 18" /></svg>;
const TargetIcon = () => <svg width="20" height="20" viewBox="0 0 24 24" stroke="#0B7A6F" strokeWidth="2.2" {...base}><circle cx="12" cy="12" r="4" /><path d="M12 2v4M12 18v4M2 12h4M18 12h4" /></svg>;
const PinIcon = () => <svg width="18" height="18" viewBox="0 0 24 24" stroke="#33465C" strokeWidth="2" {...base}><path d="M12 21s-6-5.2-6-10a6 6 0 1112 0c0 4.8-6 10-6 10z" /><circle cx="12" cy="11" r="1.7" /></svg>;
const ClockIcon = () => <svg width="18" height="18" viewBox="0 0 24 24" stroke="#33465C" strokeWidth="2" {...base}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>;
