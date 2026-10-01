"use client";

import { useEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import { motion } from "motion/react";
import { ArrowUpRight } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { DataFieldCanvas } from "@/components/background/data-field-canvas";

interface QueryHeroProps {
  onSubmit: (question: string) => void;
  isLoading: boolean;
  hasAnswered: boolean;
}

const EXAMPLE_QUESTIONS = [
  "What were the top 5 products by revenue?",
  "How many orders are in each status?",
  "Which region had the most revenue in 2025?",
];

export function QueryHero({ onSubmit, isLoading, hasAnswered }: QueryHeroProps) {
  const [value, setValue] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  // The single orchestrated page-load moment: headline, input, and
  // examples arrive in one deliberate sequence, not as separate
  // scattered fade-ins on every element.
  useEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
      tl.from(".hero-eyebrow", { opacity: 0, y: 8, duration: 0.5 })
        .from(".hero-title", { opacity: 0, y: 18, duration: 0.7 }, "-=0.3")
        .from(".hero-input", { opacity: 0, y: 14, duration: 0.6 }, "-=0.35")
        .from(".hero-example", { opacity: 0, y: 8, stagger: 0.06, duration: 0.4 }, "-=0.25");
    }, rootRef);
    return () => ctx.revert();
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;
    onSubmit(trimmed);
  }

  return (
    <section
      ref={rootRef}
      className="relative flex min-h-[86vh] flex-col justify-center overflow-hidden border-b border-ink-line px-6 py-24 md:px-12"
    >
      <DataFieldCanvas />

      <div className="relative mx-auto w-full max-w-3xl">
        <p className="hero-eyebrow mb-5 text-sm text-ivory-dim">AI SQL Analyst</p>

        <h1 className="hero-title font-display text-4xl leading-[1.1] tracking-tightish text-ivory sm:text-5xl md:text-6xl">
          Ask your database a question,
          <br />
          in the words you already use.
        </h1>

        <motion.form
          onSubmit={handleSubmit}
          className="hero-input mt-10 rounded-sm border border-ink-line bg-ink-panel/70 p-1.5 backdrop-blur-sm"
          animate={hasAnswered ? { scale: 0.98 } : { scale: 1 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        >
          <Textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder="What were the top 5 products by revenue?"
            rows={2}
            className="min-h-[64px] px-4 py-3 text-lg"
            aria-label="Ask a question about your data"
          />
          <div className="flex items-center justify-between px-3 pb-2 pt-1">
            <span className="text-xs text-ivory-dim">
              Enter to ask &middot; Shift+Enter for a new line
            </span>
            <Button type="submit" disabled={isLoading || !value.trim()} size="sm">
              {isLoading ? "Thinking…" : "Ask"}
              {!isLoading && <ArrowUpRight className="h-3.5 w-3.5" />}
            </Button>
          </div>
        </motion.form>

        <div className="mt-6 flex flex-wrap gap-2">
          {EXAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => {
                setValue(q);
              }}
              className="hero-example rounded-sm border border-ink-line px-3 py-1.5 text-xs text-ivory-dim transition-colors hover:border-amber/50 hover:text-ivory"
            >
              {q}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
