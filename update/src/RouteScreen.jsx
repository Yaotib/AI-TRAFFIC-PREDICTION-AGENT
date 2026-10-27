import { useEffect, useMemo, useRef, useState } from 'react';
import MapView from './MapView.jsx';
import { FIRST_SLOT, LEVEL_STYLE, buildReason, buildWarnings, computeModel, f12, toTimeValue } from './routing.js';

// Watches an element's size so the map can fit itself to the screen.
function useSize(ref) {
  const [size, setSize] = useState({ W: 390, H: 800 });
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const ro = new ResizeObserver(() => {
      const r = el.getBoundingClientRect();
      setSize({ W: Math.round(r.width), H: Math.round(r.height) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref]);
  return size;
}

const today = () => new Date().toISOString().slice(0, 10);

/**
 * Route screen: map + recommended route + bottom sheet + Details.
 * Props:
 *   search     { from, destination }  from the home screen
 *   onBack     go back to the home screen (to change start or destination)
 *   failFirst  true = the first route lookup fails once, to demo the retry message
 */
export default function RouteScreen({ search, onBack, failFirst = false }) {
  const { destination } = search;
  const rootRef = useRef(null);
  const size = useSize(rootRef);
  const failRef = useRef(failFirst); // used up after the first failure

  const [status, setStatus] = useState('loading'); // loading | ready | error
  const [pick, setPick] = useState(null);
  const [open, setOpen] = useState(false); // Details open?
  const [toast, setToast] = useState('');
  const [plan, setPlan] = useState({ mode: 'leave', leaveTime: '07:15', arriveTime: '08:30', date: today() });

  // Pretend to fetch routes. INTEGRATION POINT: call the prediction service here.
  function load() {
    setStatus('loading');
    return setTimeout(() => {
      if (failRef.current) { failRef.current = false; setStatus('error'); } else setStatus('ready');
    }, 1100);
  }
  useEffect(() => { const t = load(); return () => clearTimeout(t); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const model = useMemo(() => computeModel(destination, plan), [destination, plan]);
  const ready = status === 'ready' && model.ok;
  const problem = status === 'ready' && !model.ok && model.kind !== 'nodata'; // e.g. time outside the sample data
  const noData = status === 'ready' && model.kind === 'nodata';
  const detailsOpen = open && (ready || problem);

  const selectedId = ready ? (pick || model.rec) : 'A';
  const selected = ready ? model.routes.find((r) => r.id === selectedId) : null;
  const recommended = ready ? model.routes.find((r) => r.id === model.rec) : null;

  function showToast(t) { setToast(t); setTimeout(() => setToast(''), 3000); }
  const set = (patch) => setPlan((p) => ({ ...p, ...patch }));

  return (
    <div className="screen" ref={rootRef}>
      <MapView size={size} model={status === 'ready' ? model : null} selectedId={selectedId} onPick={setPick} />
      <div className="mapcap">Illustrative map, not to scale · simulated data</div>

      {/* compact top bar: tap start or destination to edit */}
      <div className="topbar">
        <button type="button" className="iconbtn" aria-label="Back to search" onClick={onBack}><BackIcon /></button>
        <div className="tbcol">
          <button type="button" className="tbrow" aria-label={`Edit starting point: ${search.from}`} onClick={onBack}>
            <span className="dot-start" aria-hidden="true" /><span className="tbtext">{search.from}</span><EditIcon />
          </button>
          <button type="button" className="tbrow strong" aria-label={`Edit destination: ${destination.name}`} onClick={onBack}>
            <span className="dot-end" aria-hidden="true" /><span className="tbtext">{destination.name}</span><EditIcon />
          </button>
        </div>
      </div>
      <button type="button" className="recenter" aria-label="Recenter on my location" onClick={() => showToast('Demo map: your location is an example point, not real GPS.')}><TargetIcon /></button>
      {toast && <div className="toast" role="status">{toast}</div>}

      <section className={`sheet${detailsOpen ? ' open' : ''}`} aria-label="Route summary">
        <button type="button" className="grab" aria-label={detailsOpen ? 'Collapse details' : 'Expand details'} aria-expanded={detailsOpen}
          onClick={() => { if (ready || problem) setOpen(!open); }}><span /></button>
        <div className="sheetbody">

          {status === 'loading' && (
            <div role="status" aria-live="polite" className="stack">
              <div className="loading"><span className="dots" aria-hidden="true"><span /><span /><span /></span><b>Finding routes to {destination.name}</b></div>
              <div className="skel" style={{ height: 34, width: '55%' }} />
              <div className="grid3"><div className="skel" style={{ height: 72 }} /><div className="skel" style={{ height: 72 }} /><div className="skel" style={{ height: 72 }} /></div>
            </div>
          )}

          {status === 'error' && (
            <div role="alert" className="stack">
              <div className="notice"><span className="ico warn" aria-hidden="true"><WarnIcon /></span>
                <div><b>We couldn&apos;t load route options right now.</b><p>Please try again in a moment.</p></div></div>
              <div className="row"><button type="button" className="btn primary" onClick={load}>Try again</button><button type="button" className="btn" onClick={onBack}>Back to search</button></div>
            </div>
          )}

          {noData && (
            <div role="status" className="stack">
              <div><b className="h">Not enough data for this trip</b><p>We don&apos;t have enough sample data for {destination.name}, so we can&apos;t recommend a route.</p></div>
              <div className="row"><button type="button" className="btn primary" onClick={onBack}>Choose another destination</button></div>
            </div>
          )}

          {problem && !detailsOpen && (
            <div role="status" className="stack">
              <div><b className="h">Not enough data for that time</b><p>{model.msg}</p></div>
              <div className="row"><button type="button" className="btn primary" onClick={() => setOpen(true)}>Change time</button><button type="button" className="btn" onClick={onBack}>New destination</button></div>
            </div>
          )}

          {ready && !detailsOpen && (
            <>
              <div className="summary">
                <div className="stack tight">
                  <div className="row tight">
                    <Pill text={selected.id === model.rec ? 'Recommended' : `Selected route${selected.min > recommended.min ? ` · +${selected.min - recommended.min} min` : ''}`}
                      bg={selected.id === model.rec ? '#E3F3F0' : '#EEF3F4'} fg={selected.id === model.rec ? '#075E55' : '#33465C'} />
                    <Pill text={`${selected.level} traffic`} bg={LEVEL_STYLE[selected.level].bg} fg={LEVEL_STYLE[selected.level].fg} />
                  </div>
                  <span className="bigtime">{selected.min} min</span>
                  <span className="eta">Leave {f12(model.dep)} · arrive {f12(selected.eta)}</span>
                  <span className="sub">Route {selected.id} · {selected.name} · {selected.km} km</span>
                </div>
                <button type="button" className="btn small" onClick={() => setOpen(true)}>Details</button>
              </div>
              <div className="grid3">
                {model.routes.map((r) => (
                  <button type="button" key={r.id} className="rcard" aria-pressed={r.id === selectedId} onClick={() => setPick(r.id)}
                    style={{ border: `2px solid ${r.id === selectedId ? r.color : '#DDE5E8'}`, background: r.id === selectedId ? '#F4FAF9' : '#fff' }}>
                    <span className="rname"><i style={{ background: r.color }} />Route {r.id}</span>
                    <span className="rmin">{r.min} min</span>
                    <span className="rsub">{r.level} traffic</span>
                    <span className="rrec">{r.id === model.rec ? 'Recommended' : ' '}</span>
                  </button>
                ))}
              </div>
            </>
          )}

          {detailsOpen && (
            <Details model={model} plan={plan} set={set} selectedId={selectedId} setPick={setPick} onClose={() => setOpen(false)} ready={ready} />
          )}
        </div>
      </section>
    </div>
  );
}

function Details({ model, plan, set, selectedId, setPick, onClose, ready }) {
  const selected = ready ? model.routes.find((r) => r.id === selectedId) : null;
  const timeValue = plan.mode === 'leave' ? plan.leaveTime : plan.arriveTime;
  const timeErr = ready ? '' : model.msg;
  const max = ready ? Math.max(...model.mins) : 0, min = ready ? Math.min(...model.mins) : 0;
  return (
    <>
      <div className="dhead"><h2>Details</h2><button type="button" className="iconbtn" aria-label="Close details" onClick={onClose}><CloseIcon /></button></div>

      {/* E. Departure planning */}
      <div className="planner">
        <span className="cap">When</span>
        <div className="segwrap" role="group" aria-label="Departure setting">
          <button type="button" className="seg" aria-pressed={plan.mode === 'leave'} onClick={() => set({ mode: 'leave' })}>Leave at</button>
          <button type="button" className="seg" aria-pressed={plan.mode === 'arrive'} onClick={() => set({ mode: 'arrive' })}>Arrive by</button>
        </div>
        <div className="row">
          <div className="field grow"><input type="date" aria-label="Date" value={plan.date} onChange={(e) => set({ date: e.target.value })} /></div>
          <div className={`field grow${timeErr ? ' invalid' : ''}`}>
            <input type="time" aria-label={plan.mode === 'leave' ? 'Leave at time' : 'Arrive by time'} aria-describedby="time-err" value={timeValue}
              onChange={(e) => set(plan.mode === 'leave' ? { leaveTime: e.target.value } : { arriveTime: e.target.value })} />
          </div>
        </div>
        <p className="err" id="time-err" role="alert">{timeErr}</p>
        <p className="note">Times are Accra local time (Africa/Accra). Sample times are the same on every date. The comparison updates when you change this.</p>
      </div>

      {ready && (
        <>
          {/* A. Route comparison */}
          <div className="stack tight">
            <span className="cap">Route comparison</span>
            {model.routes.map((r) => (
              <button type="button" key={r.id} className="rcard wide" aria-pressed={r.id === selectedId} onClick={() => setPick(r.id)}
                style={{ border: `2px solid ${r.id === selectedId ? r.color : '#DDE5E8'}`, background: r.id === selectedId ? '#F4FAF9' : '#fff' }}>
                <span className="rname big"><i style={{ background: r.color }} />Route {r.id} · {r.name}
                  {r.id === model.rec && <em>Recommended</em>}</span>
                <span>{r.min} min · {r.km} km · arrive {f12(r.eta)}</span>
                <Pill text={`${r.level} traffic`} bg={LEVEL_STYLE[r.level].bg} fg={LEVEL_STYLE[r.level].fg} />
              </button>
            ))}
          </div>

          {/* B. Departure-time comparison */}
          <div className="stack tight">
            <span className="cap">Departure times</span>
            <p className="note">Journey time on Route {model.rec} by departure time (AM). Tap a bar to try that time.</p>
            <div className="bars" role="group" aria-label="Journey time by departure time">
              {model.mins.map((m, k) => {
                const t = FIRST_SLOT + 15 * k, h = Math.round(36 + ((m - min) / Math.max(1, max - min)) * 64);
                return (
                  <button type="button" key={k} className="col" onClick={() => set({ mode: 'leave', leaveTime: toTimeValue(t) })}
                    aria-label={`Leave at ${f12(t)}: ${m} minutes${k === model.highlightI ? ', recommended time' : ''}`}
                    style={{ border: `2px solid ${plan.mode === 'leave' && k === model.i ? '#0B1F3A' : 'transparent'}` }}>
                    <b>{m}</b><span className="bar" style={{ height: h, background: k === model.highlightI ? '#0B7A6F' : '#B9C8D0' }} /><small>{f12(t).replace(' AM', '')}</small>
                  </button>
                );
              })}
            </div>
            <div className="legend"><span><i style={{ background: '#0B7A6F' }} />Recommended time</span><span><i style={{ background: '#B9C8D0' }} />Other times</span>
              {plan.mode === 'leave' && model.i !== model.highlightI && <span><i className="hollow" />Your time</span>}</div>
            {plan.mode === 'arrive' && <p className="spare">Spare time: {model.deadline - model.routes.find((r) => r.id === model.rec).eta} min before {f12(model.deadline)}</p>}
          </div>

          {/* C. Why this route */}
          <div className="stack tight"><span className="cap">Why this route</span><p className="reason">{buildReason(model, plan.mode)}</p></div>

          {/* D. Data source and limits */}
          <div className="limits">
            <span className="src">SIMULATED DATA</span>
            {buildWarnings(model, plan.mode, selected).map((w) => <p key={w}>{w}</p>)}
          </div>
        </>
      )}
    </>
  );
}

const Pill = ({ text, bg, fg }) => <span className="pill" style={{ background: bg, color: fg }}>{text}</span>;
const ic = { fill: 'none', strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true };
const BackIcon = () => <svg width="22" height="22" viewBox="0 0 24 24" stroke="#0B1F3A" strokeWidth="2.2" {...ic}><path d="M15 5l-7 7 7 7" /></svg>;
const CloseIcon = () => <svg width="22" height="22" viewBox="0 0 24 24" stroke="#0B1F3A" strokeWidth="2.2" {...ic}><path d="M6 6l12 12M18 6L6 18" /></svg>;
const EditIcon = () => <svg width="16" height="16" viewBox="0 0 24 24" stroke="#4A5B70" strokeWidth="2" {...ic}><path d="M4 20h4L19 9l-4-4L4 16zM14 6l4 4" /></svg>;
const TargetIcon = () => <svg width="22" height="22" viewBox="0 0 24 24" stroke="#0B7A6F" strokeWidth="2.2" {...ic}><circle cx="12" cy="12" r="4" /><path d="M12 2v4M12 18v4M2 12h4M18 12h4" /></svg>;
const WarnIcon = () => <svg width="20" height="20" viewBox="0 0 24 24" stroke="#6B4B00" strokeWidth="2" {...ic}><path d="M12 3l10 18H2zM12 10v5M12 18v.2" /></svg>;
