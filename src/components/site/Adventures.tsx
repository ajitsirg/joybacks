import { Reveal, SectionHeading } from "./Reveal";
import { activities } from "./data";

export function Adventures() {
  return (
    <section id="adventure" className="bg-forest-deep relative overflow-hidden py-10 sm:py-14">
      <div className="blur-circle bg-gold/10 -top-20 -right-10 size-72" aria-hidden />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Reveal>
          <SectionHeading title={<span className="text-cream">Adventure Experiences</span>}>
            <p className="text-cream/70 mt-3 max-w-2xl text-sm leading-relaxed sm:text-base">
              From treetop ziplines to lakeside camps — adrenaline for every age group, guided by
              certified instructors.
            </p>
          </SectionHeading>
        </Reveal>

        <div className="no-scrollbar mt-8 flex snap-x snap-mandatory gap-4 overflow-x-auto pb-2 lg:grid lg:grid-cols-6 lg:overflow-visible">
          {activities.map((activity, i) => (
            <Reveal
              key={activity.name}
              delay={i * 70}
              className="w-[70%] shrink-0 snap-start sm:w-[42%] lg:w-auto"
            >
              <article className="group border-gold/20 rounded-card relative h-72 overflow-hidden border">
                <img
                  src={activity.img}
                  alt={`${activity.name} activity at Joy Club Adventure Resort`}
                  loading="lazy"
                  className="size-full object-cover transition-transform duration-700 group-hover:scale-110"
                />
                <div className="from-forest-deep/95 absolute inset-0 bg-gradient-to-t via-transparent to-transparent" />
                <h3 className="text-cream font-display absolute inset-x-0 bottom-0 p-5 text-xl">
                  {activity.name}
                </h3>
              </article>
            </Reveal>
          ))}
          <Reveal delay={400} className="w-[70%] shrink-0 snap-start sm:w-[42%] lg:w-auto">
            <article className="from-gold to-gold-light text-forest-deep rounded-card flex h-72 flex-col items-center justify-center gap-4 bg-gradient-to-br p-6 text-center">
              <p className="font-display text-4xl leading-none font-bold">20+</p>
              <p className="font-display text-2xl">Activities</p>
              <a
                href="#gallery"
                className="bg-forest-deep text-cream hover:bg-forest rounded-btn px-6 py-2.5 text-[0.68rem] font-bold tracking-[0.18em] uppercase transition-colors"
              >
                Explore All
              </a>
            </article>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
