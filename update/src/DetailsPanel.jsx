import { BASE, SLOT0, LEVEL_STYLE, f12, reasonText, toTimeValue } from './routes.js';

export default function DetailsPanel({
  m,
  ready,
  plan,
  setPlan,
  sel,
  selId,
  onPick,
  search,
  onBack,
  onViewMap,
  onStartNavigation,
}) {
  const isLeave = plan.mode === 'leave';
  const recR = ready ? m.routes.find((r) => r.id === m.rec) : null;
  const isRec = sel && sel.id === m?.rec;
  const diff = sel && recR ? sel.min - recR.min : 0;
  const L = sel ? LEVEL_STYLE[sel.lvl] : LEVEL_STYLE.Light;
  const max = ready ? Math.max(...m.mins) : 0;
  const min = ready ? Math.min(...m.mins) : 0;
  const timeErr = !ready && m?.kind !== 'nodata' ? m?.msg : '';

  const warns = [];
  if (ready) {
    warns.push('Example numbers for this prototype. Real traffic can differ.');
    if (isLeave && m.dep !== SLOT0 + 15 * m.i) {
      warns.push(`Estimates use the nearest 15-minute slot (${f12(SLOT0 + 15 * m.i)}).`);
    }
    if (!isLeave && sel && sel.eta > m.D) {
      warns.push(`Route ${sel.id} would arrive after your arrive-by time.`);
    }
    if (m.routes.every((r) => r.lvl === 'Heavy')) {
      warns.push('Traffic is heavy on every route at this time.');
    }
  }

  return (
    <div className="details-panel-inner">
      {/* Top summary row / header */}
      <div className="details-header-row">
        <div className="tbcol">
          <div className="from-dest-badge">
            <span className="dot-start" />
            <span className="from-text">{search?.from || 'My location'}</span>
            <span className="arrow-sep">→</span>
            <span className="dot-end" />
            <b>{search?.destination?.name || 'Harbour Station'}</b>
          </div>
        </div>
        <div className="row tight">
          {onViewMap && (
            <button type="button" className="btn small" onClick={onViewMap}>
              View Map
            </button>
          )}
          {onBack && (
            <button type="button" className="btn small" onClick={onBack}>
              Change
            </button>
          )}
        </div>
      </div>

      {ready && sel && (
        <>
          {/* Summary Box with Start Navigation button */}
          <div className="summary-box card-style">
            <div className="sumrow">
              <div className="stack tight">
                <div className="row">
                  <span
                    className="pill"
                    style={
                      isRec
                        ? { background: '#E3F3F0', color: '#075E55' }
                        : { background: '#EEF3F4', color: '#33465C' }
                    }
                  >
                    {isRec ? 'Recommended' : `Selected route${diff > 0 ? ` · +${diff} min` : ''}`}
                  </span>
                  <span className="pill" style={{ background: L.bg, color: L.fg }}>
                    {sel.lvl} traffic
                  </span>
                </div>
                <span className="bigtime">{sel.min} min</span>
                <span className="eta">
                  Leave {f12(m.dep)} · arrive {f12(sel.eta)}
                </span>
                <span className="sub">
                  Route {sel.id} · {sel.name} · {sel.km} km
                </span>
              </div>
            </div>

            {/* Start navigation button spanning full width */}
            <div style={{ marginTop: 14 }}>
              <button
                type="button"
                className="btn primary"
                style={{ width: '100%', minHeight: 48 }}
                onClick={() => {
                  if (onStartNavigation) onStartNavigation(sel);
                  else alert(`Starting navigation on Route ${sel.id} (${sel.name})`);
                }}
              >
                Start Navigation
              </button>
            </div>
          </div>

          {/* Quick route selector cards */}
          <div className="grid3">
            {m.routes.map((r) => (
              <button
                key={r.id}
                type="button"
                className="rcard"
                aria-pressed={r.id === selId}
                onClick={() => onPick(r.id)}
                style={{
                  border: `2px solid ${r.id === selId ? r.color : '#DDE5E8'}`,
                  background: r.id === selId ? '#F4FAF9' : '#fff',
                }}
              >
                <span className="rname">
                  <span className="dot" style={{ background: r.color }} />
                  Route {r.id}
                </span>
                <span className="rmin">{r.min} min</span>
                <span className="rtr">{r.lvl} traffic</span>
                <span className="rrec">{r.id === m.rec ? 'Recommended' : ''}</span>
              </button>
            ))}
          </div>

          {/* When / Departure Planning */}
          <div className="planner">
            <span className="cap">When</span>
            <div className="segwrap" role="group" aria-label="Departure setting">
              <button
                type="button"
                className="seg"
                aria-pressed={isLeave}
                onClick={() => setPlan({ mode: 'leave' })}
              >
                Leave at
              </button>
              <button
                type="button"
                className="seg"
                aria-pressed={!isLeave}
                onClick={() => setPlan({ mode: 'arrive' })}
              >
                Arrive by
              </button>
            </div>
            <div className="row grow">
              <div className="field">
                <input
                  type="date"
                  aria-label="Date"
                  value={plan.date}
                  onChange={(e) => setPlan({ date: e.target.value })}
                />
              </div>
              <div className={`field${timeErr ? ' invalid' : ''}`}>
                <input
                  type="time"
                  aria-label={isLeave ? 'Leave at time' : 'Arrive by time'}
                  aria-describedby="time-err"
                  value={isLeave ? plan.leaveTime : plan.arriveTime}
                  onChange={(e) =>
                    setPlan(
                      isLeave ? { leaveTime: e.target.value } : { arriveTime: e.target.value }
                    )
                  }
                />
              </div>
            </div>
            <p className="err" id="time-err" role="alert">
              {timeErr}
            </p>
            <span className="note">
              Sample times are from 7:00 to 8:30 AM. Updating this updates the route recommendations.
            </span>
          </div>

          {/* Route comparison list */}
          <div className="stack tight">
            <span className="cap">Route comparison</span>
            {m.routes.map((r) => {
              const rL = LEVEL_STYLE[r.lvl];
              return (
                <button
                  key={r.id}
                  type="button"
                  className="rcard wide"
                  aria-pressed={r.id === selId}
                  onClick={() => onPick(r.id)}
                  style={{
                    border: `2px solid ${r.id === selId ? r.color : '#DDE5E8'}`,
                    background: r.id === selId ? '#F4FAF9' : '#fff',
                  }}
                >
                  <span className="rname">
                    <span className="dot" style={{ background: r.color }} />
                    <b>
                      Route {r.id} · {r.name}
                    </b>
                    {r.id === m.rec && (
                      <span className="pill" style={{ background: '#E3F3F0', color: '#075E55' }}>
                        Recommended
                      </span>
                    )}
                  </span>
                  <span>
                    {r.min} min · {r.km} km · arrive {f12(r.eta)}
                  </span>
                  <span
                    className="pill"
                    style={{ background: rL.bg, color: rL.fg, alignSelf: 'flex-start' }}
                  >
                    {r.lvl} traffic
                  </span>
                </button>
              );
            })}
          </div>

          {/* Departure times bar chart */}
          <div className="stack tight">
            <span className="cap">Departure times</span>
            <span className="note big">
              Journey time on Route {m.rec} by departure time (AM). Click a bar to select that time.
            </span>
            <div className="bars" role="group" aria-label="Journey time by departure time">
              {m.mins.map((v, k) => {
                const t = SLOT0 + 15 * k;
                const h = Math.round(36 + ((v - min) / Math.max(1, max - min)) * 64);
                return (
                  <button
                    key={k}
                    type="button"
                    className="col"
                    onClick={() => setPlan({ mode: 'leave', leaveTime: toTimeValue(t) })}
                    aria-label={`Leave at ${f12(t)}: ${v} minutes${k === m.hiI ? ', recommended time' : ''}`}
                    style={{
                      border: `2px solid ${k === m.i && isLeave ? '#0B1F3A' : 'transparent'}`,
                    }}
                  >
                    <span className="bv">{v}</span>
                    <span
                      className="bar"
                      style={{ height: h, background: k === m.hiI ? '#0B7A6F' : '#B9C8D0' }}
                    />
                    <span className="bl">{f12(t).replace(' AM', '')}</span>
                  </button>
                );
              })}
            </div>
            <div className="legend">
              <span>
                <i style={{ background: '#0B7A6F' }} />
                Recommended time
              </span>
              <span>
                <i style={{ background: '#B9C8D0' }} />
                Other times
              </span>
              {isLeave && m.i !== m.hiI && (
                <span>
                  <i style={{ border: '2px solid #0B1F3A', background: '#fff' }} />
                  Your time
                </span>
              )}
            </div>
            {!isLeave && recR && (
              <p className="spare">
                Spare time: {m.D - recR.eta} min before {f12(m.D)}
              </p>
            )}
          </div>

          {/* Why this route */}
          <div className="stack tight">
            <span className="cap">Why this route</span>
            <p className="reason">{reasonText(m, plan.mode)}</p>
          </div>

          {/* Limitations and Data note */}
          <div className="datanote">
            <span className="src">SIMULATED DATA</span>
            {warns.map((w, idx) => (
              <div key={idx} className="warn">
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                  fill="none"
                  stroke="#6B4B00"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                >
                  <circle cx="12" cy="12" r="9" />
                  <path d="M12 11v5M12 8v.2" />
                </svg>
                <span>{w}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
