// The wheel of themes, drawn on a canvas. Tap it to spin (see onTap).
import { textOn } from "./util.js";

export class Wheel {
  constructor(canvas, themes) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.themes = themes;
    this.angle = 0; // degrees, clockwise
    this.spinning = false;
    this.onTap = null;
    this._raf = 0;

    canvas.addEventListener("click", () => this.onTap && this.onTap());
    this._ro = new ResizeObserver(() => this.resize());
    this._ro.observe(canvas);
    this.resize();
  }

  destroy() {
    this._ro.disconnect();
    cancelAnimationFrame(this._raf);
  }

  resize() {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = Math.max(1, Math.round(rect.width * dpr));
    this.canvas.height = Math.max(1, Math.round(rect.height * dpr));
    this.draw();
  }

  /** Spin and land with the pointer (top) on theme `index`. Resolves when it stops. */
  spinTo(index, durationMs = 3000) {
    return new Promise((resolve) => {
      const seg = 360 / this.themes.length;
      const finalMod = (((360 - (index + 0.5) * seg) % 360) + 360) % 360;
      const currentMod = ((this.angle % 360) + 360) % 360;
      const delta = (finalMod - currentMod + 360) % 360;
      const start = this.angle;
      const target = start + 5 * 360 + delta;
      const t0 = performance.now();
      this.spinning = true;
      const step = (now) => {
        const p = Math.min(1, (now - t0) / durationMs);
        const eased = 1 - Math.pow(1 - p, 3);
        this.angle = start + (target - start) * eased;
        this.draw();
        if (p < 1) {
          this._raf = requestAnimationFrame(step);
        } else {
          this.spinning = false;
          resolve();
        }
      };
      this._raf = requestAnimationFrame(step);
    });
  }

  draw() {
    const { ctx, canvas } = this;
    const w = canvas.width;
    const h = canvas.height;
    const dpr = window.devicePixelRatio || 1;
    ctx.clearRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h / 2;
    const margin = 14 * dpr;
    const R = Math.min(w, h) / 2 - margin;
    if (R <= 8) return; // canvas not laid out yet
    const n = this.themes.length;
    const seg = (Math.PI * 2) / n;

    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate((this.angle * Math.PI) / 180);
    const baseSize = Math.max(12, R / 8);
    const setFont = (px) => (ctx.font = `bold ${px}px system-ui, sans-serif`);
    ctx.textBaseline = "middle";

    this.themes.forEach((theme, i) => {
      const a0 = -Math.PI / 2 + i * seg;
      const a1 = a0 + seg;
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.arc(0, 0, R, a0, a1);
      ctx.closePath();
      ctx.fillStyle = theme.color;
      ctx.fill();
      ctx.lineWidth = 2 * dpr;
      ctx.strokeStyle = "#1a1a1a";
      ctx.stroke();

      ctx.save();
      ctx.rotate(a0 + seg / 2);
      ctx.fillStyle = textOn(theme.color);
      ctx.textAlign = "right";
      // shrink the font first, and only ellipsize if it still does not fit
      const maxWidth = R * 0.66;
      let size = baseSize;
      setFont(size);
      while (size > baseSize * 0.6 && ctx.measureText(theme.name).width > maxWidth) setFont((size -= 1));
      ctx.fillText(this._fit(theme.name, maxWidth), R * 0.93, 0);
      ctx.restore();
    });
    ctx.restore();

    // hub
    ctx.beginPath();
    ctx.arc(cx, cy, R * 0.07, 0, Math.PI * 2);
    ctx.fillStyle = "#222";
    ctx.fill();
    ctx.lineWidth = 2 * dpr;
    ctx.strokeStyle = "#000";
    ctx.stroke();

    // pointer (fixed, at the top)
    const top = cy - R;
    ctx.beginPath();
    ctx.moveTo(cx - R * 0.07, top - 8 * dpr);
    ctx.lineTo(cx + R * 0.07, top - 8 * dpr);
    ctx.lineTo(cx, top + R * 0.09);
    ctx.closePath();
    ctx.fillStyle = "#f1c40f";
    ctx.fill();
    ctx.lineWidth = 1.5 * dpr;
    ctx.strokeStyle = "#000";
    ctx.stroke();
  }

  _fit(text, maxWidth) {
    const ctx = this.ctx;
    if (ctx.measureText(text).width <= maxWidth) return text;
    let t = text;
    while (t.length > 1 && ctx.measureText(t + "…").width > maxWidth) t = t.slice(0, -1);
    return t + "…";
  }
}
