import { useEffect, useMemo, useRef, useState } from 'react';
import MapSvg from './MapSvg.jsx';
import { useSize } from './useSize.js';
import { SLOT0, LEVEL_STYLE, computeModel, f12, reasonText, toTimeValue } from './routes.js';

// Add ?routefail to the page address: the first route search fails, and "Try again" works.
const FAIL_FIRST = /[?&]routefail/.test(window.location.search);

/**
 * Route screen: map + bottom sheet + details.
 * Props: search = { from, destination }, onBack = go back to the home screen.
 */
export default function MapScreen({ search, onBack }) {
  const [ref, { W, H }] = useSize();
  const place = search.destination;

  const [status, setStatus] = useState('loading'); // loading | ready | error
  const failNext = useRef(FAIL_FIRST);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [pick, setPick] = useState(null);
  const [toast, setToast] = useState('');
  const [plan, setPlan] = useState({ mode: 'leave', leaveTime: '07:15', arriveTime: '08:30', date: new Date().toISOString().slice(0, 10) });

  // brief loading state, then the (simulated) result
  function load() {
    setStatus('loading');
    return setTimeout(() => {
      if (failNext.current) { failNext.current = false; setStatus('error'); } else setStatus('ready');
    }, 1100);
  }
  useEffect(() => { const t = load(); return () => clearTimeout(t); }, [place]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(() => setToast(''), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  const m = useMemo(() => computeModel(place, plan), [place, plan]);
  const noData = status === 'ready' && m.kind === 'nodata';
  const ready = status === 'ready' && m.ok;
  const problem = status === 'ready' && !m.ok && !noData; // e.g. time outside our sample data
  const detailsOpen = sheetOpen && (ready || problem);
  const selId = ready ? pick || m.rec : null;
  const sel = ready ? m.routes.find((r) => r.id === selId) : null;
  const recR = ready ? m.routes.find((r) => r.id === m.rec) : null;
  const set = (patch) => setPlan((p) => ({ ...p, ...patch }));

  return (
    <div className="app" ref={ref}>
      <MapSvg W={W} H={H} routes={ready ? m.routes : null} rec={ready ? m.rec : null} selId={selId} onPick={setPick} />
      <div className="mapcap">Illustrative map, not to scale · simulated data</div>

      <div className="topbar">
        <button type="button" className="iconbtn" aria-label="Back to search" onClick={onBack}><Icon d="M15 5l-7 7 7 7" /></button>
        <div className="tbcol">
          <button type="button" className="tbrow" aria-label={`Edit starting point: ${search.from}`} onClick={onBack}>
            <svg width="14" height="14" viewBox="0 0 18 18" aria-hidden="true"><circle cx="9" cy="9" r="6" fill="#fff" stroke="#0B1F3A" strokeWidth="3" /></svg>
            <span className="ell">{search.from}</span><Icon d="M4 20h4L19 9l-4-4L4 16zM14 6l4 4" size={16} color="#4A5B70" sw={2} />
          </button>
          <button type="button" className="tbrow bold" aria-label={`Edit destination: ${place.name}`} onClick={onBack}>
            <svg width="14" height="14" viewBox="0 0 18 18" aria-hidden="true"><rect x="2" y="2" width="14" height="14" rx="3" fill="#0B1F3A" /></svg>
            <span className="ell">{place.name}</span><Icon d="M4 20h4L19 9l-4-4L4 16zM14 6l4 4" size={16} color="#4A5B70" sw={2} />
          </button>
        </div>
      </div>
      <button type="button" className="recenter" aria-label="Recenter on my location" onClick={() => setToast('Demo map: your location is an example point, not real GPS.')}>
        <Icon d="M12 2v4M12 18v4M2 12h4M18 12h4" color="#0B7A6F" extra={<circle cx="12" cy="12" r="4" />} />
      </button>
      {toast && <div className="toast" role="status">{toast}</div>}

      <section className={`sheet${detailsOpen ? ' open' : ''}`} aria-label="Route summary">
        <button type="button" className="grab" aria-label={detailsOpen ? 'Collapse details' : 'Expand details'} aria-expanded={detailsOpen}
          onClick={() => { if (ready || problem) setSheetOpen(!sheetOpen); }}><span /></button>
        <div className="sheetbody">
          {status === 'loading' && (
            <div role="status" aria-live="polite" className="stack">
              <div className="loading"><span className="dots" aria-hidden="true"><span /><span /><span /></span><b>Finding routes to {place.name}</b></div>
              <div className="skel" style={{ height: 34, width: '55%' }} />
              <div className="grid3"><div className="skel" style={{ height: 72 }} /><div className="skel" style={{ height: 72 }} /><div className="skel" style={{ height: 72 }} /></div>
            </div>
          )}

          {status === 'error' && (
            <div role="alert" className="stack">
              <div className="msg"><span className="ico warn" aria-hidden="true"><Icon d="M12 3l10 18H2zM12 10v5M12 18v.2" size={20} color="#6B4B00" sw={2} /></span>
                <div><b className="big">We couldn't load route options right now.</b><p>Please try again in a moment.</p></div></div>
              <div className="row"><button type="button" className="btn primary" onClick={load}>Try again</button><button type="button" className="btn" onClick={onBack}>Back to search</button></div>
            </div>
          )}

          {noData && (
            <div role="status" className="stack">
              <div><b className="big">Not enough data for this trip</b><p>We don't have enough sample data for {place.name}, so we can't recommend a route.</p></div>
              <div className="row"><button type="button" className="btn primary" onClick={onBack}>Choose another destination</button></div>
            </div>
          )}

          {problem && !detailsOpen && (
            <div role="status" className="stack">
              <div><b className="big">Not enough data for that time</b><p>{m.msg}</p></div>
              <div className="row"><button type="button" className="btn primary" onClick={() => setSheetOpen(true)}>Change time</button><button type="button" className="btn" onClick={onBack}>New destination</button></div>
            </div>
          )}

          {ready && !detailsOpen && <Summary m={m} sel={sel} recR={recR} selId={selId} onPick={setPick} onDetails={() => setSheetOpen(true)} />}

          {detailsOpen && (
            <Details m={m} ready={ready} plan={plan} set={set} sel={sel} selId={selId} onPick={setPick} onClose={() => setSheetOpen(false)} />
          )}
        </div>
      </section>
    </div>
  );
}

/* ---------- collapsed sheet: the simple summary ---------- */
function Summary({ m, sel, recR, selId, onPick, onDetails }) {
  const isRec = sel.id === m.rec;
  const diff = sel.min - recR.min;
  const L = LEVEL_STYLE[sel.lvl];
  return (
    <>
      <div className="sumrow">
        <div className="stack tight">
          <div className="row">
            <span className="pill" style={isRec ? { background: '#E3F3F0', color: '#075E55' } : { background: '#EEF3F4', color: '#33465C' }}>{isRec ? 'Recommended' : `Selected route${diff > 0 ? ` · +${diff} min` : ''}`}</span>
            <span className="pill" style={{ background: L.bg, color: L.fg }}>{sel.lvl} traffic</span>
          </div>
          <span className="bigtime">{sel.min} min</span>
          <span className="eta">Leave {f12(m.dep)} · arrive {f12(sel.eta)}</span>
          <span className="sub">Route {sel.id} · {sel.name} · {sel.km} km</span>
        </div>
        <button type="button" className="btn small" onClick={onDetails}>Details</button>
      </div>
      <div className="grid3">
        {m.routes.map((r) => (
          <button key={r.id} type="button" className="rcard" aria-pressed={r.id === selId} onClick={() => onPick(r.id)}
            style={{ border: `2px solid ${r.id === selId ? r.color : '#DDE5E8'}`, background: r.id === selId ? '#F4FAF9' : '#fff' }}>
            <span className="rname"><span className="dot" style={{ background: r.color }} />Route {r.id}</span>
            <span className="rmin">{r.min} min</span>
            <span className="rtr">{r.lvl} traffic</span>
            <span className="rrec">{r.id === m.rec ? 'Recommended' : ''}</span>
          </button>
        ))}
      </div>
    </>
  );
}

/* ---------- Details panel ---------- */
function Details({ m, ready, plan, set, selId, onPick, onClose }) {
  const timeErr = !ready && m.kind !== 'nodata' ? m.msg : '';
  const isLeave = plan.mode === 'leave';
  const warns = [];
  if (ready) {
    warns.push('Example numbers for this prototype. Real traffic can differ.');
    if (isLeave && m.dep !== SLOT0 + 15 * m.i) warns.push(`Estimates use the nearest 15-minute slot (${f12(SLOT0 + 15 * m.i)}).`);
    const sel = m.routes.find((r) => r.id === selId);
    if (!isLeave && sel.eta > m.D) warns.push(`Route ${sel.id} would arrive after your arrive-by time.`);
    if (m.routes.every((r) => r.lvl === 'Heavy')) warns.push('Traffic is heavy on every route at this time.');
  }
  const recR = ready ? m.routes.find((r) => r.id === m.rec) : null;
  const max = ready ? Math.max(...m.mins) : 0, min = ready ? Math.min(...m.mins) : 0;

  return (
    <>
      <div className="dhead"><h2>Details</h2><button type="button" className="iconbtn" aria-label="Close details" onClick={onClose}><Icon d="M6 6l12 12M18 6L6 18" /></button></div>

      {/* E. Departure planning */}
      <div className="planner">
        <span className="cap">When</span>
        <div className="segwrap" role="group" aria-label="Departure setting">
          <button type="button" className="seg" aria-pressed={isLeave} onClick={() => set({ mode: 'leave' })}>Leave at</button>
          <button type="button" className="seg" aria-pressed={!isLeave} onClick={() => set({ mode: 'arrive' })}>Arrive by</button>
        </div>
        <div className="row grow">
          <div className="field"><input type="date" aria-label="Date" value={plan.date} onChange={(e) => set({ date: e.target.value })} /></div>
          <div className={`field${timeErr ? ' invalid' : ''}`}>
            <input type="time" aria-label={isLeave ? 'Leave at time' : 'Arrive by time'} aria-describedby="time-err" value={isLeave ? plan.leaveTime : plan.arriveTime}
              onChange={(e) => set(isLeave ? { leaveTime: e.target.value } : { arriveTime: e.target.value })} />
          </div>
        </div>
        <p className="err" id="time-err" role="alert">{timeErr}</p>
        <span className="note">Times are Accra local time (Africa/Accra). Sample times are the same on every date. The comparison updates when you change this.</span>
      </div>

      {ready && (
        <>
          {/* A. Route comparison */}
          <div className="stack tight">
            <span className="cap">Route comparison</span>
            {m.routes.map((r) => {
              const L = LEVEL_STYLE[r.lvl];
              return (
                <button key={r.id} type="button" className="rcard wide" aria-pressed={r.id === selId} onClick={() => onPick(r.id)}
                  style={{ border: `2px solid ${r.id === selId ? r.color : '#DDE5E8'}`, background: r.id === selId ? '#F4FAF9' : '#fff' }}>
                  <span className="rname"><span className="dot" style={{ background: r.color }} /><b>Route {r.id} · {r.name}</b>
                    {r.id === m.rec && <span className="pill" style={{ background: '#E3F3F0', color: '#075E55' }}>Recommended</span>}</span>
                  <span>{r.min} min · {r.km} km · arrive {f12(r.eta)}</span>
                  <span className="pill" style={{ background: L.bg, color: L.fg, alignSelf: 'flex-start' }}>{r.lvl} traffic</span>
                </button>
              );
            })}
          </div>

          {/* B. Departure-time comparison */}
          <div className="stack tight">
            <span className="cap">Departure times</span>
            <span className="note big">Journey time on Route {m.rec} by departure time (AM). Tap a bar to try that time.</span>
            <div className="bars" role="group" aria-label="Journey time by departure time">
              {m.mins.map((v, k) => {
                const t = SLOT0 + 15 * k;
                const h = Math.round(36 + ((v - min) / Math.max(1, max - min)) * 64);
                return (
                  <button key={k} type="button" className="col" onClick={() => set({ mode: 'leave', leaveTime: toTimeValue(t) })}
                    aria-label={`Leave at ${f12(t)}: ${v} minutes${k === m.hiI ? ', recommended time' : ''}`}
                    style={{ border: `2px solid ${k === m.i && isLeave ? '#0B1F3A' : 'transparent'}` }}>
                    <span className="bv">{v}</span>
                    <span className="bar" style={{ height: h, background: k === m.hiI ? '#0B7A6F' : '#B9C8D0' }} />
                    <span className="bl">{f12(t).replace(' AM', '')}</span>
                  </button>
                );
              })}
            </div>
            <div className="legend">
              <span><i style={{ background: '#0B7A6F' }} />Recommended time</span>
              <span><i style={{ background: '#B9C8D0' }} />Other times</span>
              {isLeave && m.i !== m.hiI && <span><i style={{ border: '2px solid #0B1F3A', background: '#fff' }} />Your time</span>}
            </div>
            {!isLeave && <p className="spare">Spare time: {m.D - recR.eta} min before {f12(m.D)}</p>}
          </div>

          {/* C. Why this route */}
          <div className="stack tight"><span className="cap">Why this route</span><p className="reason">{reasonText(m, plan.mode)}</p></div>

          {/* D. Data source and limitations */}
          <div className="datanote">
            <span className="src">SIMULATED DATA</span>
            {warns.map((w) => <div key={w} className="warn"><svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="#6B4B00" strokeWidth="2.2" strokeLinecap="round"><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8v.2" /></svg><span>{w}</span></div>)}
          </div>
        </>
      )}
    </>
  );
}

function Icon({ d, size = 22, color = '#0B1F3A', sw = 2.2, extra }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round"><path d={d} />{extra}</svg>;
}
