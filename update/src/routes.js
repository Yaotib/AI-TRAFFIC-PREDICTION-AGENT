// SAMPLE ROUTE DATA (prototype only). Every number here is made up.
// INTEGRATION POINT: in a real build this table would come from your traffic-prediction service.
// Journey minutes for 7 departure times (7:00, 7:15 ... 8:30 AM) on each route.
export const BASE = {
  A: { name: 'Ridge Expressway', km: 14.2, free: 24, color: '#0B7A6F', m: [30, 27, 29, 33, 32, 34, 35] },
  B: { name: 'Riverside Road', km: 12.6, free: 21, color: '#C8630F', m: [35, 33, 34, 38, 40, 41, 42] },
  C: { name: 'Old Market Link', km: 11.8, free: 27, color: '#4458C4', m: [38, 36, 37, 41, 43, 44, 45] },
};
export const IDS = ['A', 'B', 'C'];
export const SLOT0 = 420; // 7:00 AM in minutes after midnight
export const SLOTS = 7;   // every 15 minutes until 8:30 AM

// minutes after midnight -> "7:15 AM"
export function f12(m) {
  const h = Math.floor(m / 60) % 24, mm = m % 60;
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${mm < 10 ? '0' : ''}${mm} ${h >= 12 ? 'PM' : 'AM'}`;
}
// "07:15" -> minutes (NaN if invalid)
export function parseTime(s) {
  const m = /^(\d{1,2}):(\d{2})$/.exec(String(s || ''));
  if (!m) return NaN;
  const h = +m[1], mi = +m[2];
  return h > 23 || mi > 59 ? NaN : h * 60 + mi;
}
export function toTimeValue(min) {
  return `${String(Math.floor(min / 60)).padStart(2, '0')}:${String(min % 60).padStart(2, '0')}`;
}
export const levelFor = (ratio) => (ratio < 1.15 ? 'Light' : ratio < 1.5 ? 'Moderate' : 'Heavy');
export const LEVEL_STYLE = {
  Light: { bg: '#E3F3F0', fg: '#075E55' },
  Moderate: { bg: '#FFF6DD', fg: '#6B4B00' },
  Heavy: { bg: '#FBE4DF', fg: '#8E2615' },
};

// A destination's "size" scales the sample numbers so different places give different times.
export function placeFactor(place) {
  if (place.id === 'custom') {
    let h = 0;
    for (const ch of place.name) h = (h * 31 + ch.charCodeAt(0)) % 997;
    return 0.7 + (h % 80) / 100;
  }
  return { harbour: 1, campus: 0.7, market: 1.15, northgate: 0.85, clinic: 0.9, airport: 1.5 }[place.id] ?? 1;
}

/**
 * The "decision". Picks a departure slot and the quickest route from the sample table.
 * Returns { ok:true, ... } or { ok:false, kind, msg } when we can't recommend anything.
 */
export function computeModel(place, { mode, leaveTime, arriveTime }) {
  if (!place || place.id === 'lakeview') return { ok: false, kind: 'nodata', msg: '' };
  const f = placeFactor(place);
  const trip = (id, i) => Math.max(5, Math.round(BASE[id].m[i] * f));
  const bestAt = (i) => IDS.reduce((b, id) => (trip(id, i) < trip(b, i) ? id : b), 'A');

  let i, dep, D = null;
  if (mode === 'leave') {
    const T = parseTime(leaveTime);
    if (Number.isNaN(T)) return { ok: false, kind: 'time', msg: 'Enter a valid time.' };
    if (T < 413 || T > 517) return { ok: false, kind: 'range', msg: 'We only have sample times from 7:00 to 8:30 AM. Pick a time in that window.' };
    i = Math.max(0, Math.min(SLOTS - 1, Math.round((T - SLOT0) / 15)));
    dep = T;
  } else {
    D = parseTime(arriveTime);
    if (Number.isNaN(D)) return { ok: false, kind: 'time', msg: 'Enter a valid time.' };
    let bi = -1, bm = Infinity;
    for (let k = 0; k < SLOTS; k++) {
      const m = trip(bestAt(k), k);
      if (SLOT0 + 15 * k + m <= D && m <= bm) { bm = m; bi = k; }
    }
    if (bi < 0) return { ok: false, kind: 'nofeasible', msg: `None of the sample departures arrive by ${f12(D)}. Try a later arrival time.` };
    i = bi;
    dep = SLOT0 + 15 * bi;
  }

  const rec = bestAt(i);
  const routes = IDS.map((id) => {
    const min = trip(id, i);
    return { id, name: BASE[id].name, color: BASE[id].color, min, km: (BASE[id].km * f).toFixed(1), eta: dep + min, lvl: levelFor(min / (BASE[id].free * f)) };
  });
  const mins = Array.from({ length: SLOTS }, (_, k) => trip(rec, k));
  const bestI = mins.indexOf(Math.min(...mins));
  return { ok: true, i, dep, D, rec, routes, mins, bestI, hiI: mode === 'arrive' ? i : bestI };
}

// One short plain-English reason that only uses numbers we actually show.
export function reasonText(m, mode) {
  const r = m.routes.find((x) => x.id === m.rec);
  const others = m.routes.filter((x) => x.id !== m.rec).map((x) => x.min).sort((a, b) => a - b);
  if (mode === 'leave') {
    let t = `Route ${r.id} (${r.name}) is the quickest of the three for a ${f12(m.dep)} departure: ${r.min} min, against ${others[0]} and ${others[1]} min on the other routes.`;
    if (m.bestI !== m.i) t += ` Leaving at ${f12(SLOT0 + 15 * m.bestI)} would be quicker: ${m.mins[m.bestI]} min.`;
    return t;
  }
  return `Leaving at ${f12(m.dep)} on Route ${r.id} (${r.name}) gets you there by ${f12(r.eta)}, ${m.D - r.eta} min before ${f12(m.D)}. Of the sample departures that arrive in time, it has the shortest journey.`;
}
