// Synthesised sound effects (Web Audio), mirroring app/sound_manager.py. No audio files needed.
// Browsers only allow audio after a user gesture, so call unlock() on the first tap.

export class Sound {
  constructor(store) {
    this.store = store;
    this.ctx = null;
  }

  _context() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      this.ctx = new AC();
    }
    if (this.ctx.state === "suspended") this.ctx.resume();
    return this.ctx;
  }

  unlock() {
    this._context();
  }

  _tone(freq, start, dur, { amp = 0.5, type = "sine", endFreq = null } = {}) {
    const c = this.ctx;
    const vol = this.store.getSetting("volume") / 100;
    const t0 = c.currentTime + start;
    const osc = c.createOscillator();
    const gain = c.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    if (endFreq) osc.frequency.linearRampToValueAtTime(endFreq, t0 + dur);
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.linearRampToValueAtTime(amp * vol, t0 + Math.min(0.01, dur / 3));
    gain.gain.linearRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(gain).connect(c.destination);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
  }

  play(name) {
    if (!this.store.getSetting("sound_enabled")) return;
    const c = this._context();
    if (!c) return;
    switch (name) {
      case "click":
        this._tone(1400, 0, 0.04, { amp: 0.4 });
        break;
      case "land":
        this._tone(180, 0, 0.18, { amp: 0.5 });
        this._tone(90, 0, 0.18, { amp: 0.35 });
        break;
      case "spin": {
        let t = 0;
        let gap = 0.03;
        for (let i = 0; i < 28; i++) {
          this._tone(1500, t, 0.02, { amp: 0.3 });
          t += 0.02 + gap;
          gap += 0.006;
        }
        break;
      }
      case "correct":
        [523.25, 659.25, 783.99].forEach((f, i) => this._tone(f, i * 0.16, 0.14));
        break;
      case "wedge":
        this._tone(880, 0, 0.15, { amp: 0.4 });
        this._tone(1320, 0, 0.15, { amp: 0.25 });
        break;
      case "shot":
        this._tone(700, 0, 0.18, { amp: 0.5, endFreq: 250 });
        this._tone(650, 0.21, 0.16, { amp: 0.45, endFreq: 220 });
        this._tone(600, 0.40, 0.14, { amp: 0.4, endFreq: 200 });
        this._tone(320, 0.60, 0.22, { amp: 0.35 });
        break;
      case "victory":
        [523.25, 659.25, 783.99, 1046.5].forEach((f, i) =>
          this._tone(f, i * 0.18, i === 3 ? 0.5 : 0.16)
        );
        break;
    }
  }
}
