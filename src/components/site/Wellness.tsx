import { Sparkles, PersonStanding, BrainCircuit, Leaf } from "lucide-react";
import { Reveal, SectionHeading } from "./Reveal";
import { IMG } from "./data";

const THERAPIES = [
  { icon: Sparkles, label: "Spa" },
  { icon: PersonStanding, label: "Yoga" },
  { icon: BrainCircuit, label: "Meditation" },
  { icon: Leaf, label: "Ayurveda" },
];

export function Wellness() {
  return (
    <section id="wellness" className="bg-background py-10 sm:py-14">
      <div className="mx-auto grid max-w-7xl items-center gap-8 px-4 sm:px-6 lg:grid-cols-[1fr_1fr_0.7fr] lg:px-8">
        <Reveal>
          <img
            src={IMG.meditation}
            alt="Guest meditating outdoors at sunrise at the resort"
            loading="lazy"
            className="rounded-img h-[26rem] w-full object-cover shadow-(--shadow-lift)"
          />
        </Reveal>

        <Reveal delay={100}>
          <SectionHeading
            align="left"
            eyebrow="Natural Therapy & Wellness"
            title="Heal in Nature. Live Better."
          >
            <p className="text-muted-foreground mt-4 leading-relaxed">
              Our holistic wellness programs blend ancient naturopathy with modern therapeutic care.
              Guided detox plans, sunrise yoga, mindful breathing and organic farm-to-table meals
              help you reset completely — body, mind and spirit.
            </p>
            <a
              href="#booking"
              className="bg-forest hover:bg-forest-deep text-cream btn-glow rounded-btn mt-7 inline-block px-7 py-3 text-xs font-bold tracking-[0.18em] uppercase transition-colors"
            >
              Explore Wellness
            </a>
          </SectionHeading>
        </Reveal>

        <Reveal delay={180}>
          <ul className="border-border/70 divide-border/70 rounded-card divide-y border bg-card p-2 shadow-(--shadow-soft)">
            {THERAPIES.map((therapy) => (
              <li key={therapy.label} className="flex items-center gap-3 px-4 py-4 text-sm">
                <span className="bg-gold/12 text-gold grid size-9 shrink-0 place-items-center rounded-full">
                  <therapy.icon className="size-4.5" strokeWidth={1.4} />
                </span>
                <span className="font-medium">{therapy.label}</span>
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </section>
  );
}
