import { BedDouble, Leaf, Mountain, HeartHandshake } from "lucide-react";
import { Reveal } from "./Reveal";

const FEATURES = [
  {
    icon: BedDouble,
    title: "Luxury Stay",
    desc: "Elegant villas, premium rooms and world-class comfort.",
    href: "#stay",
  },
  {
    icon: Leaf,
    title: "Natural Therapy",
    desc: "Rejuvenate your body and mind with nature's healing touch.",
    href: "#wellness",
  },
  {
    icon: Mountain,
    title: "Adventure Park",
    desc: "Thrilling activities and adventures for all age groups.",
    href: "#adventure",
  },
  {
    icon: HeartHandshake,
    title: "Destination Weddings",
    desc: "Beautiful venues for your dream wedding celebrations.",
    href: "#weddings",
  },
];

export function Features() {
  return (
    <section className="relative z-20 -mt-16 sm:-mt-20">
      <div className="mx-auto grid max-w-7xl gap-5 px-4 sm:grid-cols-2 sm:px-6 lg:grid-cols-4 lg:px-8">
        {FEATURES.map((feature, i) => (
          <Reveal key={feature.title} delay={i * 90}>
            <article className="group rounded-card h-full bg-white p-6 shadow-(--shadow-lift) transition-all duration-300 hover:-translate-y-2">
              <span className="bg-gold/12 text-gold ring-gold/30 grid size-12 place-items-center rounded-full ring-1">
                <feature.icon className="size-6" strokeWidth={1.3} />
              </span>
              <h3 className="font-display mt-5 text-xl">{feature.title}</h3>
              <p className="text-muted-foreground mt-2 text-sm leading-relaxed">{feature.desc}</p>
              <a
                href={feature.href}
                className="text-gold mt-5 inline-block text-[0.7rem] font-semibold tracking-[0.18em] uppercase"
              >
                Discover More →
              </a>
            </article>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
