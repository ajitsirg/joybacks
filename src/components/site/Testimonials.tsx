import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Quote, Star } from "lucide-react";
import { Reveal, SectionHeading } from "./Reveal";
import { testimonials } from "./data";
import { cn } from "@/lib/utils";
import { useIsMobile } from "@/hooks/use-mobile";

export function Testimonials() {
  const isMobile = useIsMobile();
  const perView = isMobile ? 1 : 3;
  const pages = Math.max(1, testimonials.length - perView + 1);
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    setIndex((i) => Math.min(i, pages - 1));
  }, [pages]);

  const next = useCallback(() => setIndex((i) => (i + 1) % pages), [pages]);
  const prev = useCallback(() => setIndex((i) => (i - 1 + pages) % pages), [pages]);

  useEffect(() => {
    if (paused) return;
    const id = window.setInterval(next, 5000);
    return () => window.clearInterval(id);
  }, [next, paused]);

  return (
    <section className="bg-background py-10 sm:py-14">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Reveal>
          <SectionHeading eyebrow="Testimonials" title="Guest Experiences" />
        </Reveal>

        <div
          className="relative mt-8"
          onMouseEnter={() => setPaused(true)}
          onMouseLeave={() => setPaused(false)}
        >
          <div className="overflow-hidden">
            <div
              className="flex transition-transform duration-700 ease-[cubic-bezier(0.22,1,0.36,1)]"
              style={{ transform: `translateX(-${index * (100 / perView)}%)` }}
            >
              {testimonials.map((t) => (
                <figure
                  key={t.name}
                  className="w-full shrink-0 px-3 md:w-1/3"
                  style={{ width: `${100 / perView}%` }}
                >
                  <div className="border-border/70 rounded-card flex h-full flex-col border bg-card p-7 shadow-(--shadow-soft)">
                    <Quote className="text-gold/50 size-7" strokeWidth={1.3} />
                    <div className="mt-4 flex gap-1" aria-label="Rated 5 out of 5">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <Star key={i} className="fill-gold text-gold size-4" strokeWidth={0} />
                      ))}
                    </div>
                    <blockquote className="text-muted-foreground mt-4 flex-1 text-sm leading-relaxed">
                      “{t.quote}”
                    </blockquote>
                    <figcaption className="mt-6 flex items-center gap-3">
                      <img
                        src={t.avatar}
                        alt={`Portrait of ${t.name}`}
                        loading="lazy"
                        className="ring-gold/40 size-11 rounded-full object-cover ring-2"
                      />
                      <span>
                        <span className="block text-sm font-semibold">{t.name}</span>
                        <span className="text-muted-foreground block text-xs">{t.city}</span>
                      </span>
                    </figcaption>
                  </div>
                </figure>
              ))}
            </div>
          </div>

          <div className="mt-6 flex items-center justify-center gap-5">
            <button
              type="button"
              onClick={prev}
              aria-label="Previous testimonial"
              className="border-forest/30 text-forest hover:bg-forest hover:text-cream grid size-10 place-items-center rounded-full border transition-colors"
            >
              <ChevronLeft className="size-5" />
            </button>
            <div className="flex items-center gap-2">
              {Array.from({ length: pages }).map((_, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setIndex(i)}
                  aria-label={`Go to slide ${i + 1}`}
                  aria-current={i === index}
                  className={cn(
                    "h-2 rounded-full transition-all",
                    i === index ? "bg-gold w-7" : "bg-forest/25 w-2",
                  )}
                />
              ))}
            </div>
            <button
              type="button"
              onClick={next}
              aria-label="Next testimonial"
              className="border-forest/30 text-forest hover:bg-forest hover:text-cream grid size-10 place-items-center rounded-full border transition-colors"
            >
              <ChevronRight className="size-5" />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
