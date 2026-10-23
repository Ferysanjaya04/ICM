import { useEffect, useRef } from "react";

const CAM = 0.62;
const NEAR = 0.35;
const FAR = 3.4;

export default function WaveMesh({ colors, crests = false }) {
  const hostRef = useRef(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return undefined;

    const canvas = document.createElement("canvas");
    canvas.setAttribute("aria-hidden", "true");
    canvas.style.cssText = "position:absolute;inset:0;width:100%;height:100%;display:block";
    host.appendChild(canvas);

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      canvas.remove();
      return undefined;
    }

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const coarsePointer = !window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    const toRgb = (hex) => {
      const value = Number.parseInt(hex.slice(1), 16);
      return `${(value >> 16) & 255},${(value >> 8) & 255},${value & 255}`;
    };
    const dotColor = toRgb(colors[1]);
    const accentColor = toRgb(colors[2]);

    let width = 0;
    let height = 0;
    let columns = 0;
    let rows = 0;
    let focalLength = 0;
    let horizon = 0;
    let animationFrame = 0;
    let visible = true;
    let lastFrame = 0;

    const startTime = performance.now();
    const pointer = { x: 0, z: 1.4, strength: 0, targetX: 0, targetZ: 1.4, targetStrength: 0 };
    const rings = [];

    const resize = () => {
      const nextWidth = host.clientWidth;
      const nextHeight = host.clientHeight;
      if (!nextWidth || !nextHeight || (nextWidth === width && nextHeight === height)) return false;

      width = nextWidth;
      height = nextHeight;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      focalLength = Math.max(width, height * 1.2) * 0.55;
      horizon = height * 0.3;
      columns = Math.round(Math.min(110, Math.max(46, width / 14)));
      rows = Math.round(Math.min(60, Math.max(32, height / 14)));
      return true;
    };

    const halfWidthAtFarEdge = () => (width / 2 / focalLength) * FAR * 1.05;

    const waveHeight = (x, z, time) => {
      let y =
        0.075 * Math.sin(x * 2.2 + time * 0.45) +
        0.06 * Math.sin(z * 2.9 - time * 0.55 + x * 0.8) +
        0.02 * Math.sin((x + z) * 6.1 + time * 0.9);

      if (pointer.strength > 0.01) {
        const distanceSquared = (x - pointer.x) ** 2 + (z - pointer.z) ** 2;
        y += 0.18 * pointer.strength * Math.exp(-distanceSquared / 0.07);
      }

      for (const ring of rings) {
        const age = time - ring.time;
        const distance = Math.hypot(x - ring.x, z - ring.z);
        const front = age * 1.15;
        y += 0.14 * Math.exp(-((distance - front) ** 2) / 0.014) * Math.exp(-age * 0.75);
      }
      return y;
    };

    const drawFrame = (time) => {
      ctx.clearRect(0, 0, width, height);
      pointer.x += (pointer.targetX - pointer.x) * 0.1;
      pointer.z += (pointer.targetZ - pointer.z) * 0.1;
      pointer.strength += (pointer.targetStrength - pointer.strength) * 0.06;
      while (rings.length && time - rings[0].time > 5) rings.shift();

      const halfWidth = halfWidthAtFarEdge();
      const highlightedPoints = [];

      for (let row = 0; row < rows; row++) {
        const z = FAR * Math.pow(NEAR / FAR, row / (rows - 1));
        const fog = Math.pow(1 - (z - NEAR) / (FAR - NEAR), 1.25);
        const dotSize = Math.max(0.8, Math.min(2.7, 2.1 / z));
        ctx.fillStyle = `rgba(${dotColor},${(0.04 + fog * 0.38).toFixed(3)})`;

        for (let column = 0; column < columns; column++) {
          const x = -halfWidth + (column / (columns - 1)) * halfWidth * 2;
          const y = waveHeight(x, z, time);
          const screenX = width / 2 + (x / z) * focalLength;
          if (screenX < -4 || screenX > width + 4) continue;

          const screenY = horizon + ((CAM - y) / z) * focalLength;
          if (crests && y > 0.12) {
            highlightedPoints.push(screenX, screenY, dotSize, fog);
            continue;
          }
          ctx.fillRect(screenX - dotSize / 2, screenY - dotSize / 2, dotSize, dotSize);
        }
      }

      for (let index = 0; index < highlightedPoints.length; index += 4) {
        ctx.fillStyle = `rgba(${accentColor},${(0.12 + highlightedPoints[index + 3] * 0.45).toFixed(3)})`;
        const dotSize = highlightedPoints[index + 2] * 1.1;
        ctx.fillRect(
          highlightedPoints[index] - dotSize / 2,
          highlightedPoints[index + 1] - dotSize / 2,
          dotSize,
          dotSize,
        );
      }
    };

    const currentTime = () => (performance.now() - startTime) / 1000;
    const animationLoop = (timestamp) => {
      if (!visible || document.hidden) {
        animationFrame = 0;
        return;
      }
      animationFrame = window.requestAnimationFrame(animationLoop);
      if (coarsePointer && timestamp - lastFrame < 40) return;
      lastFrame = timestamp;
      resize();
      drawFrame(currentTime());
    };

    const startAnimation = () => {
      if (!reducedMotion && !animationFrame && visible && !document.hidden) {
        animationFrame = window.requestAnimationFrame(animationLoop);
      }
    };

    const getGroundPoint = (event) => {
      const rect = host.getBoundingClientRect();
      const screenX = event.clientX - rect.left;
      const screenY = event.clientY - rect.top;
      if (screenX < 0 || screenY < horizon + 4 || screenX > rect.width || screenY > rect.height) return null;

      const z = Math.min(FAR, Math.max(NEAR, (CAM * focalLength) / (screenY - horizon)));
      return { x: ((screenX - width / 2) * z) / focalLength, z };
    };

    const onPointerMove = (event) => {
      const point = getGroundPoint(event);
      if (point) {
        pointer.targetX = point.x;
        pointer.targetZ = point.z;
        if (pointer.strength < 0.05) {
          pointer.x = point.x;
          pointer.z = point.z;
        }
      }
      pointer.targetStrength = point ? 1 : 0;
    };

    const onPointerDown = (event) => {
      const point = getGroundPoint(event);
      if (point) rings.push({ x: point.x, z: point.z, time: currentTime() });
    };

    resize();
    drawFrame(reducedMotion ? 3 : 0);

    const intersectionObserver = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      startAnimation();
    });
    intersectionObserver.observe(host);

    const resizeObserver = new ResizeObserver(() => {
      if (resize() && reducedMotion) drawFrame(3);
    });
    resizeObserver.observe(host);

    document.addEventListener("visibilitychange", startAnimation);
    if (!reducedMotion) {
      startAnimation();
      if (!coarsePointer) window.addEventListener("pointermove", onPointerMove, { passive: true });
      window.addEventListener("pointerdown", onPointerDown, { passive: true });
    }

    return () => {
      window.cancelAnimationFrame(animationFrame);
      intersectionObserver.disconnect();
      resizeObserver.disconnect();
      document.removeEventListener("visibilitychange", startAnimation);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerdown", onPointerDown);
      canvas.remove();
    };
  }, [colors, crests]);

  return (
    <div
      ref={hostRef}
      className="wave-mesh-background"
      style={{ background: colors[0] }}
      aria-hidden="true"
    />
  );
}
