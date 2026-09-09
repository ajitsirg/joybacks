import { Check } from "lucide-react";
import { Reveal, SectionHeading } from "./Reveal";
import { IMG } from "./data";
import badgeLogo from "../../Asets/leaf logo.png";

const POINTS = [
  "20+ Adventure Activities",
  "World Class Amenities",
  "Eco Friendly Resort",
  "Award Winning Hospitality",
];

export function About() {
  return (
    <section id="about" className="bg-secondary/60 relative overflow-hidden py-10 sm:py-14">
      <div className="blur-circle bg-gold/15 -top-10 -left-10 size-64" aria-hidden />
      <div className="blur-circle bg-forest/10 -right-16 -bottom-16 size-72" aria-hidden />
      <div className="relative mx-auto grid max-w-7xl items-center gap-8 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
        <Reveal>
          <SectionHeading
            align="left"
            eyebrow="About Joy Club"
            title="Nature. Wellness. Adventure."
          >
            <p className="text-muted-foreground mt-4 max-w-xl leading-relaxed">
              Nestled in the lap of the Aravalli Hills, Joy Club Adventure Resort is spread across
              lush greenery and serene landscapes, offering the perfect escape from the city. Our
              mission is to deliver exceptional value to both our guests and investors through
              quality, innovation and sustainable hospitality.
            </p>
            <ul className="mt-7 grid gap-4 sm:grid-cols-2">
              {POINTS.map((point) => (
                <li key={point} className="flex items-center gap-3 text-sm font-medium">
                  <span className="bg-gold/15 text-gold grid size-7 shrink-0 place-items-center rounded-full">
                    <Check className="size-4" strokeWidth={2} />
                  </span>
                  {point}
                </li>
              ))}
            </ul>
          </SectionHeading>
        </Reveal>

        <Reveal delay={120}>
          <div className="relative grid grid-cols-2 gap-4">
            <img
              src={IMG.aerial}
              alt="Aerial view of the green resort grounds in the Aravalli Hills"
              loading="lazy"
              className="rounded-img h-full max-h-[30rem] w-full object-cover shadow-(--shadow-lift)"
            />
            <div className="grid gap-4">
              <img
                src={IMG.room}
                alt="Interior of a premium resort room with warm lighting"
                loading="lazy"
                className="rounded-img h-full w-full object-cover shadow-(--shadow-soft)"
              />
              <img
                src={IMG.gazebo}
                alt="Garden gazebo lit with lanterns at night"
                loading="lazy"
                className="rounded-img h-full w-full object-cover shadow-(--shadow-soft)"
              />
            </div>
            <span className="ring-secondary/60 absolute top-1/2 left-1/2 size-20 -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-full shadow-(--shadow-lift) ring-8">
              <img src={badgeLogo} alt="Joy Club emblem" className="size-full object-cover" />
            </span>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
