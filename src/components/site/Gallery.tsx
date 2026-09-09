import { Instagram } from "lucide-react";
import { Reveal, SectionHeading } from "./Reveal";
import { gallery } from "./data";

export function Gallery() {
  return (
    <section id="gallery" className="bg-secondary/60 py-10 sm:py-14">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Reveal>
          <SectionHeading eyebrow="@joyclubresort" title="Moments That Stay With You" />
        </Reveal>

        <div className="no-scrollbar mt-8 flex snap-x gap-4 overflow-x-auto pb-2 lg:grid lg:grid-cols-7 lg:overflow-visible">
          {gallery.map((item, i) => (
            <Reveal
              key={item.img}
              delay={i * 60}
              className="w-40 shrink-0 snap-start sm:w-52 lg:w-auto"
            >
              <a
                href="#gallery"
                className="rounded-img group relative block aspect-square overflow-hidden"
              >
                <img
                  src={item.img}
                  alt={item.alt}
                  loading="lazy"
                  className="size-full object-cover transition-transform duration-700 group-hover:scale-110"
                />
                <span className="bg-forest-deep/60 text-gold absolute inset-0 grid place-items-center opacity-0 transition-opacity duration-300 group-hover:opacity-100">
                  <Instagram className="size-6" strokeWidth={1.4} />
                </span>
              </a>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
