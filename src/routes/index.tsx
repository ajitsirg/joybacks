import { createFileRoute } from "@tanstack/react-router";
import { Header } from "@/components/site/Header";
import { Hero } from "@/components/site/Hero";
import { Features } from "@/components/site/Features";
import { About } from "@/components/site/About";
import { Adventures } from "@/components/site/Adventures";
import { Wellness } from "@/components/site/Wellness";
import { Rooms } from "@/components/site/Rooms";
import { WeddingsCorporate } from "@/components/site/WeddingsCorporate";
import { Testimonials } from "@/components/site/Testimonials";
import { Gallery } from "@/components/site/Gallery";
import { Footer } from "@/components/site/Footer";

const TITLE = "Joy Club Adventure Resort | Luxury Resort in Jaipur, Rajasthan";
const DESCRIPTION =
  "Luxury adventure and wellness resort in the Aravalli Hills near Jaipur — premium villas, 20+ adventure activities, naturopathy retreats and destination weddings.";
const OG_IMAGE =
  "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?auto=format&fit=crop&w=1200&q=80";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: TITLE },
      { name: "description", content: DESCRIPTION },
      { property: "og:title", content: TITLE },
      { property: "og:description", content: DESCRIPTION },
      { property: "og:type", content: "website" },
      { property: "og:image", content: OG_IMAGE },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:image", content: OG_IMAGE },
    ],
  }),
  component: Index,
});

function Index() {
  return (
    <div className="joy-resort min-h-screen bg-cream text-charcoal">
      <Header />
      <main>
        <Hero />
        <Features />
        <About />
        <Adventures />
        <Wellness />
        <Rooms />
        <WeddingsCorporate />
        <Testimonials />
        <Gallery />
      </main>
      <Footer />
    </div>
  );
}
