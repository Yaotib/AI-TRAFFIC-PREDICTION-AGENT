// =====================================================================
// SAMPLE ROUTE DATA (prototype only). Every number here is made up.
// INTEGRATION POINT: a real build would get these from the team's
// prediction service. The real data format is not defined here.
// =====================================================================
export const BASE = {
  A: { name: 'Ridge Expressway', km: 14.2, free: 24, m: [30, 27, 29, 33, 32, 34, 35], color: '#0B7A6F' },
  B: { name: 'Riverside Road', km: 12.6, free: 21, m: [35, 33, 34, 38, 40, 41, 42], color: '#C8630F' },
  C: { name: 'Old Market Link', km: 11.8, free: 27, m: [38, 36, 37, 41, 43, 44, 45], color: '#4458C4' },
};
export const IDS = ['A', 'B', 'C'];
export const FIRST_SLOT = 420; // 7:00 AM, in minutes after midnight
export const SLOTS = 7; // 7:00, 7:15 ... 8:30

export function f12(m) {
  const h = Math.floor(m / 60) % 24, mm = m % 60;
  return `${h % 12 === 0 ? 12 : h % 12}:${mm < 10 ? '0' : ''}${mm} ${h >= 12 ? 'PM' : 'AM'}`;
}
export function toTimeValue(m) {
  return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
}
export function parseTime(s) {
  const m = /^(\d{1,2}):(\d{2})$/.exec(String(s || ''));
  if (!m || +m[1] > 23 || +m[2] > 59) return NaN;
  return +m[1] * 60 + +m[2];
}
export const level = (ratio) => (ratio < 1.15 ? 'Light' : ratio < 1.5 ? 'Moderate' : 'Heavy');
export const LEVEL_STYLE = {
  Light: { bg: '#E3F3F0', fg: '#075E55' },
  Moderate: { bg: '#FFF6DD', fg: '#6B4B00' },
  Heavy: { bg: '#FBE4DF', fg: '#8E2615' },
};

// Places typed by the user get a made-up (but stable) distance factor.
export function placeFactor(place) {
  if (place.f) return place.f;
  let h = 0;
  for (const ch of place.name) h = (h * 31 + ch.charCodeAt(0)) % 997;
  return 0.7 + (h % 80) / 100;
}

/**
 * The "decision": choose a departure slot and the best route from the sample table.
 * Returns { ok: true, ... } or { ok: false, kind, msg } when there is not enough data.
 */
export function computeModel(place, { mode, leaveTime, arriveTime }) {
  if (!place || place.nodata) return { ok: false, kind: 'nodata', msg: '' };
  const f = placeFactor(place);
  const trip = (id, i) => Math.max(5, Math.round(BASE[id].m[i] * f));
  const bestAt = (i) => IDS.reduce((b, id) => (trip(id, i) < trip(b, i) ? id : b), 'A');

  let i, dep, deadline = null;
  if (mode === 'leave') {
    const t = parseTime(leaveTime);
    if (Number.isNaN(t)) return { ok: false, kind: 'time', msg: 'Enter a valid time.' };
    if (t < FIRST_SLOT - 7 || t > FIRST_SLOT + 15 * (SLOTS - 1) + 7)
      return { ok: false, kind: 'range', msg: 'We only have sample times from 7:00 to 8:30 AM. Pick a time in that window.' };
    i = Math.max(0, Math.min(SLOTS - 1, Math.round((t - FIRST_SLOT) / 15)));
    dep = t;
  } else {
    deadline = parseTime(arriveTime);
    if (Number.isNaN(deadline)) return { ok: false, kind: 'time', msg: 'Enter a valid time.' };
    let bi = -1, bm = Infinity;
    for (let k = 0; k < SLOTS; k++) {
      const m = trip(bestAt(k), k);
      if (FIRST_SLOT + 15 * k + m <= deadline && m <= bm) { bm = m; bi = k; }
    }
    if (bi < 0) return { ok: false, kind: 'nofeasible', msg: `None of the sample departures arrive by ${f12(deadline)}. Try a later arrival time.` };
    i = bi;
    dep = FIRST_SLOT + 15 * bi;
  }

  const rec = bestAt(i);
  const routes = IDS.map((id) => {
    const min = trip(id, i);
    return { id, name: BASE[id].name, color: BASE[id].color, min, km: (BASE[id].km * f).toFixed(1), eta: dep + min, level: level(min / (BASE[id].free * f)) };
  });
  const mins = Array.from({ length: SLOTS }, (_, k) => trip(rec, k));
  const bestI = mins.indexOf(Math.min(...mins));
  return { ok: true, i, dep, deadline, rec, routes, mins, bestI, highlightI: mode === 'arrive' ? i : bestI };
}

// One short, plain-English reason that only states what the data shows.
export function buildReason(model, mode) {
  const r = model.routes.find((x) => x.id === model.rec);
  if (mode === 'arrive') {
    return `Leaving at ${f12(model.dep)} on Route ${r.id} (${r.name}) gets you there by ${f12(r.eta)}, ${model.deadline - r.eta} min before ${f12(model.deadline)}. Of the sample departures that arrive in time, it has the shortest journey.`;
  }
  const others = model.routes.filter((x) => x.id !== model.rec).map((x) => x.min).sort((a, b) => a - b);
  let t = `Route ${r.id} (${r.name}) is the quickest of the three for a ${f12(model.dep)} departure: ${r.min} min, against ${others[0]} and ${others[1]} min on the other routes.`;
  if (model.bestI !== model.i) t += ` Leaving at ${f12(FIRST_SLOT + 15 * model.bestI)} would be quicker: ${model.mins[model.bestI]} min.`;
  return t;
}

export function buildWarnings(model, mode, selected) {
  const w = ['Example numbers for this prototype. Real traffic can differ.'];
  if (mode === 'leave' && model.dep !== FIRST_SLOT + 15 * model.i) w.push(`Estimates use the nearest 15-minute slot (${f12(FIRST_SLOT + 15 * model.i)}).`);
  if (mode === 'arrive' && selected.eta > model.deadline) w.push(`Route ${selected.id} would arrive after your arrive-by time.`);
  if (model.routes.every((r) => r.level === 'Heavy')) w.push('Traffic is heavy on every route at this time.');
  return w;
}
