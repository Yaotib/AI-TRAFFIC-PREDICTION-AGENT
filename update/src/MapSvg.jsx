// Illustrative map. Not real geography: one sample map with three sample routes.
const ROUTES = {
  A: [['M', [120, 400]], ['C', [200, 330], [250, 300], [340, 290]], ['C', [430, 280], [520, 250], [560, 160]], ['C', [600, 70], [640, 130], [680, 120]]],
  B: [['M', [120, 400]], ['C', [220, 430], [380, 440], [470, 380]], ['C', [560, 320], [640, 300], [650, 200]], ['C', [660, 100], [670, 150], [680, 120]]],
  C: [['M', [120, 400]], ['L', [200, 385]], ['L', [280, 395]], ['L', [350, 340]], ['L', [430, 340]], ['L', [500, 300]], ['L', [590, 300]], ['L', [620, 200]], ['L', [680, 120]]],
};
const CHIP_AT = { A: [560, 160], B: [470, 380], C: [590, 300] };
const n1 = (v) => v.toFixed(1);

// Works out how to fit the sample route into the part of the screen that is not covered by panels.
function fit(W, H, onMap) {
  const wide = W >= 900;
  let x0, x1, y0, y1;
  if (wide) { if (onMap) { x0 = 476; x1 = W - 452; y0 = 16; y1 = H - 16; } else { x0 = 496; x1 = W - 32; y0 = 32; y1 = H - 32; } }
  else if (onMap) { x0 = 12; x1 = W - 12; y0 = 150; y1 = Math.max(y0 + 160, H - Math.min(310, H * 0.5) - 8); }
  else { x0 = 0; x1 = W; y0 = 16; y1 = Math.max(140, H - 470); }
  const pad = 30, fw = Math.max(120, x1 - x0), fh = Math.max(100, y1 - y0);
  const sL = Math.min((fw - 2 * pad) / 600, (fh - 2 * pad) / 350);
  const sP = Math.min((fw - 2 * pad) / 350, (fh - 2 * pad) / 600);
  const portrait = sP > sL * 1.05;
  const s = Math.max(0.25, portrait ? sP : sL);
  const T = portrait ? (x, y) => [y, 800 - x] : (x, y) => [x, y];
  const c = T(400, 275);
  return { s, T, vx: c[0] - (x0 + x1) / 2 / s, vy: c[1] - (y0 + y1) / 2 / s, vw: W / s, vh: H / s };
}

export default function MapSvg({ W, H, routes, rec, selId, onPick }) {
  const { s, T, vx, vy, vw, vh } = fit(W, H, true);
  const u = 1 / s;
  const P = (segs) => segs.map((sg) => sg[0] + sg.slice(1).map((pt) => { const q = T(pt[0], pt[1]); return `${n1(q[0])} ${n1(q[1])}`; }).join(' ')).join('');

  const river = P([['M', [-800, 250]], ['L', [0, 250]], ['C', [120, 200], [240, 330], [400, 300]], ['S', [640, 220], [800, 300]], ['L', [1600, 300]]]);
  const avenue = P([['M', [-400, 820]], ['L', [0, 520]], ['L', [260, 330]], ['L', [520, 190]], ['L', [800, 70]], ['L', [1200, -110]]]);
  const parks = [[48, 60, 144, 96], [578, 368, 154, 84], [258, 448, 74, 44]].map((r) => {
    const a = T(r[0], r[1]), b = T(r[0] + r[2], r[1] + r[3]);
    const x0 = Math.min(a[0], b[0]), x1 = Math.max(a[0], b[0]), y0 = Math.min(a[1], b[1]), y1 = Math.max(a[1], b[1]);
    return `M${n1(x0)} ${n1(y0)}H${n1(x1)}V${n1(y1)}H${n1(x0)}Z`;
  }).join('');
  let grid = '';
  for (let x = Math.floor((vx - 90) / 90) * 90; x < vx + vw + 90; x += 90) grid += `M${x} ${n1(vy - 90)}V${n1(vy + vh + 90)}`;
  for (let y = Math.floor((vy - 90) / 90) * 90 + 40; y < vy + vh + 90; y += 90) grid += `M${n1(vx - 90)} ${y}H${n1(vx + vw + 90)}`;

  const start = T(120, 400), dest = T(680, 120);
  const sel = selId || 'A';

  return (
    <svg className="mapsvg" viewBox={`${n1(vx)} ${n1(vy)} ${n1(vw)} ${n1(vh)}`} role="img" aria-label="Illustrative map, not to scale">
      <rect x="-2000" y="-2000" width="5000" height="5000" fill="#E8EFEF" />
      <path d={parks} fill="#D4E8DA" stroke="#D4E8DA" strokeWidth="16" strokeLinejoin="round" />
      <path d={grid} fill="none" stroke="#fff" strokeWidth="4" />
      <path d={avenue} fill="none" stroke="#F7EFD2" strokeWidth="9" strokeLinecap="round" />
      <path d={river} fill="none" stroke="#C9E0EA" strokeWidth="46" strokeLinecap="round" />

      {routes && ['A', 'B', 'C'].map((id) => {
        const color = routes.find((r) => r.id === id).color;
        return (
          <g key={id}>
            <path d={P(ROUTES[id])} fill="none" stroke="#fff" strokeWidth={n1(9 * u)} strokeLinecap="round" strokeLinejoin="round" />
            <path d={P(ROUTES[id])} fill="none" stroke={color} strokeWidth={n1(5 * u)} strokeLinecap="round" strokeLinejoin="round" opacity={id === sel ? 0 : 0.85} />
          </g>
        );
      })}
      {routes && (
        <path d={P(ROUTES[sel])} fill="none" stroke={routes.find((r) => r.id === sel).color} strokeWidth={n1(8 * u)} strokeLinecap="round" strokeLinejoin="round" />
      )}

      <circle cx={n1(start[0])} cy={n1(start[1])} r={n1(10 * u)} fill="#fff" stroke="#0B1F3A" strokeWidth={n1(3.5 * u)} />
      <rect x={n1(dest[0] - 12 * u)} y={n1(dest[1] - 12 * u)} width={n1(24 * u)} height={n1(24 * u)} rx={n1(6 * u)} fill="#0B1F3A" stroke="#fff" strokeWidth={n1(3.5 * u)} />

      {routes && routes.map((r) => {
        const p = T(CHIP_AT[r.id][0], CHIP_AT[r.id][1]);
        const w = 78 * u, h = 30 * u, isSel = r.id === sel, isRec = r.id === rec;
        const bx = w / 2, by = -h / 2;
        return (
          <g key={r.id} transform={`translate(${n1(p[0])} ${n1(p[1])})`} role="button" tabIndex={0} style={{ cursor: 'pointer' }}
            aria-label={`Route ${r.id}, ${r.name}, ${r.min} minutes${isRec ? ', recommended' : ''}`}
            onClick={() => onPick(r.id)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onPick(r.id); } }}>
            <rect x={n1(-w / 2)} y={n1(-h / 2)} width={n1(w)} height={n1(h)} rx={n1(h / 2)} fill="#fff" stroke={r.color} strokeWidth={n1((isSel ? 3.5 : 2) * u)} />
            <text x="0" y={n1(4.5 * u)} textAnchor="middle" fontFamily="Figtree, sans-serif" fontWeight="700" fontSize={n1(13 * u)} fill="#0B1F3A">{`${r.id} · ${r.min} min`}</text>
            {isRec && (
              <g>
                <circle cx={n1(bx)} cy={n1(by)} r={n1(9 * u)} fill="#0B7A6F" stroke="#fff" strokeWidth={n1(2 * u)} />
                <path d={`M${n1(bx - 4 * u)} ${n1(by)}L${n1(bx - 1 * u)} ${n1(by + 3 * u)}L${n1(bx + 4 * u)} ${n1(by - 3 * u)}`} fill="none" stroke="#fff" strokeWidth={n1(2 * u)} strokeLinecap="round" strokeLinejoin="round" />
              </g>
            )}
          </g>
        );
      })}
    </svg>
  );
}
