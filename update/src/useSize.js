import { useEffect, useRef, useState } from 'react';

// Measures an element so the map can fit itself to the screen.
export function useSize() {
  const ref = useRef(null);
  const [size, setSize] = useState({ W: 390, H: 800 });
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const measure = () => {
      const r = el.getBoundingClientRect();
      if (r.width > 50 && r.height > 50) setSize((s) => (s.W === Math.round(r.width) && s.H === Math.round(r.height) ? s : { W: Math.round(r.width), H: Math.round(r.height) }));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, size];
}
