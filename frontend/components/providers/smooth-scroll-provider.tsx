"use client";

import { useEffect, useRef } from "react";
import Lenis from "lenis";

/**
 * Wraps the app in Lenis-driven smooth scrolling.
 *
 * Lenis intercepts native scroll and re-drives it on requestAnimationFrame
 * for a smoother, slightly weighted feel — appropriate here because the
 * app's main interaction (submitting a question, watching sections reveal)
 * is itself a scroll-driven narrative, not just static content.
 *
 * Deliberately skipped when the user has prefers-reduced-motion set: smooth
 * scroll is a motion effect, and the accessibility floor in globals.css
 * already asks every animation to back off in that case — Lenis needs an
 * explicit opt-out here since it isn't pure CSS.
 */
export function SmoothScrollProvider({ children }: { children: React.ReactNode }) {
  const lenisRef = useRef<Lenis | null>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    if (prefersReducedMotion) return;

    const lenis = new Lenis({
      duration: 1.1,
      easing: (t: number) => 1 - Math.pow(1 - t, 3),
      smoothWheel: true,
    });
    lenisRef.current = lenis;

    let rafId: number;
    function raf(time: number) {
      lenis.raf(time);
      rafId = requestAnimationFrame(raf);
    }
    rafId = requestAnimationFrame(raf);

    return () => {
      cancelAnimationFrame(rafId);
      lenis.destroy();
      lenisRef.current = null;
    };
  }, []);

  return <>{children}</>;
}
