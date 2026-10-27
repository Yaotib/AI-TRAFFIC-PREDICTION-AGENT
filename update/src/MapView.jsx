import { BASE, IDS } from './routing.js';

// Illustrative map. The route shapes are drawn in a fixed 800x520 space, then fitted
// to whatever part of the screen is free (not covered by the top bar or bottom sheet).
const SEGS = {
  A: [['M', [120, 400]], ['C', [200, 330], [250, 300], [340, 290]], ['S', [520, 250], [560, 160]], ['S', [640, 130], [680, 120]]],
  B: [['M', [120, 400]], ['C', [220, 430], [380, 440], [470, 380]], ['S', [640, 300], [650, 200]], ['S', [670, 150], [680, 120]]],
  C: [['M', [120, 400]], ['L', [200, 385]], ['L', [280, 395]], ['L', [350, 340]], ['L', [430, 340]], ['L', [500, 300]], ['L', [590, 300]], ['L', [620, 200]], ['L', [680, 120]]],
};
const CHIP_AT = { A: [560, 160], B: [470, 380], C: [590, 300] };

function geometry({ W, H }) {
  const wide = W >= 900;
  let x0, x1, y0, y1;
  if (wide) { x0 = 476; x1 = W - 452; y0 = 16; y1 = H - 16; }
  else { x0 = 12; x1 = W - 12; y0 = 150; y1 = Math.max(y0 + 160, H - Math.min(310, H * 0.5) - 8); }
  const pad = 30, fw = Math.max(120, x1 - x0), fh = Math.max(100, y1 - y0);
  const sL = Math.min((fw - 2 * pad) / 600, (fh - 2 * pad) / 350);
  const sP = Math.min((fw - 2 * pad) / 350, (fh - 2 * pad) / 600);
  const portrait = sP > sL * 1.05; // turn the map on its side when that fits better
  const s = Math.max(0.25, portrait ? sP : sL);
  const T = portrait ? (x, y) => [y, 800 - x] : (x, y) => [x, y];
  const c = T(400, 275);
  const vx = c[0] - (x0 + x1) / 2 / s, vy = c[1] - (y0 + y1) / 2 / s;
  return { s, T, vx, vy, vw: W / s, vh: H / s, wide };
}

export default function MapView({ size, model, selectedId, onPick }) {
  const g = geometry(size), { s, T } = g, u = 1 / s;
  const f = (n) => n.toFixed(1);
  const path = (segs) => segs.map((sg) => sg[0] + sg.slice(1).map((pt) => { const q = T(pt[0], pt[1]); return `${f(q[0])} ${f(q[1])}`; }).join(' ')).join('');
  const river = path([['M', [-800, 250]], ['L', [0, 250]], ['C', [120, 200], [240, 330], [400, 300]], ['S', [640, 220], [800, 300]], ['L', [1600, 300]]]);
  const avenue = path([['M', [-400, 820]], ['L', [0, 520]], ['L', [260, 330]], ['L', [520, 190]], ['L', [800, 70]], ['L', [1200, -110]]]);
  const parks = [[48, 60, 144, 96], [578, 368, 154, 84], [258, 448, 74, 44]].map((r) => {
    const a = T(r[0], r[1]), b = T(r[0] + r[2], r[1] + r[3]);
    const xa = Math.min(a[0], b[0]), xb = Math.max(a[0], b[0]), ya = Math.min(a[1], b[1]), yb = Math.max(a[1], b[1]);
    return `M${f(xa)} ${f(ya)}H${f(xb)}V${f(yb)}H${f(xa)}Z`;
  }).join('');
  let grid = '';
  for (let x = Math.floor((g.vx - 90) / 90) * 90; x < g.vx + g.vw + 90; x += 90) grid += `M${x} ${f(g.vy - 90)}V${f(g.vy + g.vh + 90)}`;
  for (let y = Math.floor((g.vy - 90) / 90) * 90 + 40; y < g.vy + g.vh + 90; y += 90) grid += `M${f(g.vx - 90)} ${y}H${f(g.vx + g.vw + 90)}`;

  const ready = !!(model && model.ok);
  const st = T(120, 400), en = T(680, 120);
  const sel = ready ? selectedId : 'A';
  const round = { strokeLinecap: 'round', strokeLinejoin: 'round', fill: 'none' };

  return (
    <svg className="mapsvg" viewBox={`${f(g.vx)} ${f(g.vy)} ${f(g.vw)} ${f(g.vh)}`} preserveAspectRatio="xMidYMid slice"
      role="img" aria-label="Illustrative map, not to scale">
      <rect x="-400" y="-400" width="2400" height="2400" fill="#E8EFEF" />
      <path d={parks} fill="#D4E8DA" stroke="#D4E8DA" strokeWidth="16" strokeLinejoin="round" />
      <path d={grid} fill="none" stroke="#FFFFFF" strokeWidth="4" />
      <path d={avenue} fill="none" stroke="#F7EFD2" strokeWidth="9" strokeLinecap="round" />
      <path d={river} fill="none" stroke="#C9E0EA" strokeWidth="46" strokeLinecap="round" />

      {ready && (
        <g>
          {IDS.map((id) => <path key={'c' + id} d={path(SEGS[id])} stroke="#FFFFFF" strokeWidth={9 * u} {...round} />)}
          {IDS.map((id) => <path key={'l' + id} d={path(SEGS[id])} stroke={BASE[id].color} strokeWidth={5 * u} opacity={id === sel ? 0 : 0.85} {...round} />)}
          <path d={path(SEGS[sel])} stroke={BASE[sel].color} strokeWidth={8 * u} {...round} />
        </g>
      )}

      <circle cx={st[0]} cy={st[1]} r={10 * u} fill="#FFFFFF" stroke="#0B1F3A" strokeWidth={3.5 * u} />
      <rect x={en[0] - 12 * u} y={en[1] - 12 * u} width={24 * u} height={24 * u} rx={6 * u} fill="#0B1F3A" stroke="#FFFFFF" strokeWidth={3.5 * u} />

      {ready && model.routes.map((r) => {
        const p = T(CHIP_AT[r.id][0], CHIP_AT[r.id][1]), w = 78 * u, h = 30 * u, isSel = r.id === sel, isRec = r.id === model.rec;
        const bx = w / 2, by = -h / 2, br = 9 * u;
        return (
          <g key={r.id} transform={`translate(${f(p[0])} ${f(p[1])})`} role="button" tabIndex={0} style={{ cursor: 'pointer' }}
            aria-label={`Route ${r.id}, ${r.name}, ${r.min} minutes${isRec ? ', recommended' : ''}`}
            onClick={() => onPick(r.id)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onPick(r.id); } }}>
            <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={h / 2} fill="#FFFFFF" stroke={r.color} strokeWidth={(isSel ? 3.5 : 2) * u} />
            <text x="0" y={4.5 * u} textAnchor="middle" fontFamily="Figtree, sans-serif" fontWeight="700" fontSize={13 * u} fill="#0B1F3A">{r.id} · {r.min} min</text>
            {isRec && (
              <g>
                <circle cx={bx} cy={by} r={br} fill="#0B7A6F" stroke="#FFFFFF" strokeWidth={2 * u} />
                <path d={`M${f(bx - 4 * u)} ${f(by)}L${f(bx - 1 * u)} ${f(by + 3 * u)}L${f(bx + 4 * u)} ${f(by - 3 * u)}`} fill="none" stroke="#FFFFFF" strokeWidth={2 * u} strokeLinecap="round" strokeLinejoin="round" />
              </g>
            )}
          </g>
        );
      })}
    </svg>
  );
}
