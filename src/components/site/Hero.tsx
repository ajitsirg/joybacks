import { Link } from "@tanstack/react-router";
import { IMG } from "./data";

export function Hero() {
  return (
    <section id="home" className="relative isolate min-h-screen w-full overflow-hidden">
      <img
        src={IMG.hero}
        alt="Joy Club Adventure Resort at dusk with a lit lakeside walkway and cottages"
        className="absolute inset-0 -z-20 size-full object-cover"
        loading="eager"
      />
      <div
        className="absolute inset-0 -z-10"
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,.75) 0%, rgba(0,0,0,.45) 45%, rgba(0,0,0,.65) 100%)",
        }}
      />
      <div className="from-background absolute inset-x-0 bottom-0 -z-10 h-40 bg-gradient-to-t to-transparent" />

      <div className="mx-auto flex max-w-7xl items-center px-4 pt-28 pb-16 sm:px-6 lg:min-h-screen lg:px-8 lg:pt-32 lg:pb-20">
        <div className="max-w-2xl">
          <p className="eyebrow text-gold">Welcome To Joy Club Resort</p>
          <h1 className="text-cream font-display mt-4 text-4xl leading-[1.08] font-semibold sm:text-6xl lg:text-7xl">
            Experience Nature.
            <span className="text-gold block">Embrace Luxury.</span>
          </h1>
          <p className="text-cream/80 mt-5 max-w-xl text-base leading-relaxed sm:text-lg">
            A world-class adventure resort in Rajasthan where luxury, nature and unforgettable
            experiences come together.
          </p>
          <div className="mt-7 flex flex-wrap gap-4">
            <Link
              to="/register"
              className="bg-gold hover:bg-gold-light text-forest-deep btn-glow rounded-btn px-8 py-3.5 text-xs font-bold tracking-[0.18em] uppercase transition-colors"
            >
              Book Now
            </Link>
            <a
              href="#about"
              className="border-cream/60 text-cream hover:bg-cream hover:text-forest-deep rounded-btn border px-8 py-3.5 text-xs font-bold tracking-[0.18em] uppercase transition-colors"
            >
              Explore Resort →
            </a>
          </div>
          <p className="text-cream/60 mt-7 text-sm tracking-[0.25em] uppercase">
            Relax. Refresh. Reconnect.
          </p>
        </div>
      </div>
    </section>
  );
}
