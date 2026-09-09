import { Reveal } from "./Reveal";
import { IMG } from "./data";

const PANELS = [
  {
    id: "weddings",
    eyebrow: "Weddings",
    title: "Celebrate Love In Nature.",
    text: "Magical venues for unforgettable wedding moments.",
    cta: "Explore Weddings",
    img: IMG.wedding,
    alt: "Wedding mandap decorated with fairy lights at night",
  },
  {
    id: "corporate",
    eyebrow: "Corporate Retreats",
    title: "Inspire. Connect. Achieve.",
    text: "Perfect destination for corporate events, meetings and team building.",
    cta: "Explore Corporate",
    img: IMG.corporate,
    alt: "Conference room set up for a corporate retreat",
  },
];

export function WeddingsCorporate() {
  return (
    <section id="weddings" className="grid md:grid-cols-2">
      {PANELS.map((panel, i) => (
        <Reveal key={panel.id} delay={i * 120} className="relative isolate min-h-[22rem]">
          <article className="relative flex h-full min-h-[22rem] flex-col justify-end overflow-hidden p-7 sm:p-10">
            <img
              src={panel.img}
              alt={panel.alt}
              loading="lazy"
              className="absolute inset-0 -z-10 size-full object-cover transition-transform duration-700 hover:scale-105"
            />
            <div className="from-forest-deep/95 via-forest-deep/55 absolute inset-0 -z-10 bg-gradient-to-t to-transparent" />
            <p className="eyebrow text-gold">{panel.eyebrow}</p>
            <h2 className="text-cream font-display mt-3 text-3xl sm:text-4xl">{panel.title}</h2>
            <p className="text-cream/80 mt-3 max-w-md text-sm leading-relaxed">{panel.text}</p>
            <a
              href="#contact"
              className="bg-gold hover:bg-gold-light text-forest-deep btn-glow rounded-btn mt-6 w-fit px-7 py-3 text-xs font-bold tracking-[0.18em] uppercase transition-colors"
            >
              {panel.cta}
            </a>
          </article>
        </Reveal>
      ))}
    </section>
  );
}
