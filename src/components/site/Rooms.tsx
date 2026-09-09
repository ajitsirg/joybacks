import { Check } from "lucide-react";
import { Reveal, SectionHeading } from "./Reveal";
import { rooms } from "./data";

export function Rooms() {
  return (
    <section id="stay" className="bg-secondary/60 py-10 sm:py-14">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Reveal>
          <SectionHeading eyebrow="Stay With Us" title="Luxury Villas & Rooms" />
        </Reveal>

        <div className="mt-8 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {rooms.map((room, i) => (
            <Reveal key={room.name} delay={i * 100}>
              <article className="group rounded-card border-border/70 h-full overflow-hidden border bg-card shadow-(--shadow-soft) transition-transform duration-300 hover:-translate-y-1.5">
                <div className="h-60 overflow-hidden">
                  <img
                    src={room.img}
                    alt={`${room.name} at Joy Club Adventure Resort`}
                    loading="lazy"
                    className="size-full object-cover transition-transform duration-700 group-hover:scale-105"
                  />
                </div>
                <div className="p-6">
                  <h3 className="font-display text-2xl">{room.name}</h3>
                  <p className="text-muted-foreground mt-2 text-sm leading-relaxed">{room.desc}</p>
                  <ul className="mt-4 flex flex-wrap gap-x-4 gap-y-1.5">
                    {room.amenities.map((amenity) => (
                      <li
                        key={amenity}
                        className="text-muted-foreground flex items-center gap-1.5 text-xs"
                      >
                        <Check className="text-gold size-3.5" strokeWidth={2} />
                        {amenity}
                      </li>
                    ))}
                  </ul>
                </div>
              </article>
            </Reveal>
          ))}
        </div>

        <div className="mt-8 text-center">
          <a
            href="#booking"
            className="bg-forest-deep text-cream hover:bg-forest btn-glow rounded-btn inline-block px-8 py-3.5 text-xs font-bold tracking-[0.18em] uppercase transition-colors"
          >
            View All Rooms
          </a>
        </div>
      </div>
    </section>
  );
}
