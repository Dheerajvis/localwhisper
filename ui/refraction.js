/**
 * iOS 27 Liquid Glass Refraction & Chromatic Dispersion Engine
 * Renders real-time liquid caustic waves, chromatic light separation,
 * and audio-reactive specular highlights.
 */

class LiquidGlassRefraction {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    
    this.audioLevel = 0.0;
    this.targetLevel = 0.0;
    this.time = 0;
    this.isActive = false;

    // Specular caustic particles
    this.caustics = [];
    for (let i = 0; i < 16; i++) {
      this.caustics.push({
        x: Math.random(),
        y: Math.random(),
        radius: Math.random() * 2 + 1,
        speedX: (Math.random() - 0.5) * 0.005,
        speedY: (Math.random() - 0.5) * 0.005,
        opacity: Math.random() * 0.6 + 0.2
      });
    }

    this.resize();
    window.addEventListener('resize', () => this.resize());
    this.animate();
  }

  resize() {
    if (!this.canvas) return;
    const rect = this.canvas.getBoundingClientRect();
    this.width = rect.width || 280;
    this.height = rect.height || 28;
    this.dpr = window.devicePixelRatio || 1;
    this.canvas.width = this.width * this.dpr;
    this.canvas.height = this.height * this.dpr;
    this.ctx.scale(this.dpr, this.dpr);
  }

  setAudioLevel(level) {
    // Smooth target level interpolation
    this.targetLevel = Math.max(0.02, Math.min(1.0, level));
  }

  setActive(active) {
    this.isActive = active;
  }

  animate() {
    requestAnimationFrame(() => this.animate());

    // Linear interpolation of audio level
    this.audioLevel += (this.targetLevel - this.audioLevel) * 0.25;
    this.time += 0.04 + this.audioLevel * 0.06;

    if (!this.isActive && this.audioLevel < 0.03) {
      this.ctx.clearRect(0, 0, this.width, this.height);
      return;
    }

    this.render();
  }

  render() {
    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;
    const centerY = h / 2;

    ctx.clearRect(0, 0, w, h);

    // Save state for chromatic aberration passes
    ctx.save();

    // 1. Chromatic Dispersion Waves (Teal, Mint, Emerald refraction offset)
    const layers = [
      { color: 'rgba(81, 178, 153, 0.50)', offset: -2.5, freq: 0.035, ampScale: 1.1 }, // Teal refraction
      { color: 'rgba(45, 212, 191, 0.55)', offset: 0, freq: 0.045, ampScale: 1.0 },    // Cyan-mint core
      { color: 'rgba(107, 231, 167, 0.65)', offset: 2.5, freq: 0.055, ampScale: 0.9 },   // Luminous Mint
      { color: 'rgba(52, 211, 153, 0.40)', offset: 1.2, freq: 0.025, ampScale: 0.8 }    // Emerald edge
    ];

    layers.forEach(layer => {
      ctx.beginPath();
      const amplitude = Math.max(3, this.audioLevel * (h * 0.42)) * layer.ampScale;

      for (let x = 0; x <= w; x += 3) {
        // Compound sine wave simulating fluid refraction
        const wave1 = Math.sin(x * layer.freq + this.time * 2.0);
        const wave2 = Math.cos(x * 0.02 - this.time * 1.4);
        const y = centerY + layer.offset + (wave1 * 0.65 + wave2 * 0.35) * amplitude;

        if (x === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }

      ctx.strokeStyle = layer.color;
      ctx.lineWidth = 1.5 + this.audioLevel * 1.5;
      ctx.stroke();
    });

    // 2. Specular Liquid Glass Caustic Highlights
    ctx.globalCompositeOperation = 'screen';
    this.caustics.forEach(c => {
      c.x += c.speedX;
      c.y += c.speedY;
      if (c.x < 0) c.x = 1;
      if (c.x > 1) c.x = 0;
      if (c.y < 0) c.y = 1;
      if (c.y > 1) c.y = 0;

      const px = c.x * w;
      const py = centerY + (c.y - 0.5) * (h * 0.6);
      const intensity = c.opacity * (0.4 + this.audioLevel * 0.9);

      const grad = ctx.createRadialGradient(px, py, 0, px, py, c.radius * (1 + this.audioLevel * 2));
      grad.addColorStop(0, `rgba(255, 255, 255, ${intensity})`);
      grad.addColorStop(0.5, `rgba(107, 231, 167, ${intensity * 0.5})`);
      grad.addColorStop(1, 'rgba(255, 255, 255, 0)');

      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(px, py, c.radius * 3, 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.restore();
  }
}

window.LiquidGlassRefraction = LiquidGlassRefraction;
