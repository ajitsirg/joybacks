import heroImg from "../../Asets/Warm boardwalk lights frame a serene lagoon resort at dusk.png";
import aerialImg from "../../Asets/Lakeside Forest Resort.png";
import roomInsetImg from "../../Asets/Tropical Wooden Retreat.png";
import gazeboImg from "../../Asets/Golden Pavilion at Sunset.png";
import meditationImg from "../../Asets/Golden Forest Meditation.png";
import weddingImg from "../../Asets/Twilight Garden Wedding Canopy.png";
import corporateImg from "../../Asets/Boardroom Elegance at Dusk.png";

import ziplineImg from "../../Asets/Zipline.png";
import atvImg from "../../Asets/ATV Ride.png";
import ropeCourseImg from "../../Asets/Rope Cource.png";
import kayakingImg from "../../Asets/KayaKing.png";
import campingImg from "../../Asets/Campfire.png";

import premiumRoomImg from "../../Asets/Warm Lodge Bedroom Retreat.png";
import luxuryVillaImg from "../../Asets/Warm Tropical Villa by the Pool.png";
import executiveSuiteImg from "../../Asets/Rustic Luxury Bedroom Retreat.png";

import goldenDockImg from "../../Asets/Golden Dock at Sunset.png";

export const IMG = {
  hero: heroImg,
  aerial: aerialImg,
  room: roomInsetImg,
  gazebo: gazeboImg,
  meditation: meditationImg,
  wedding: weddingImg,
  corporate: corporateImg,
};

export const activities = [
  { name: "Zipline", img: ziplineImg },
  { name: "ATV Ride", img: atvImg },
  { name: "Rope Course", img: ropeCourseImg },
  { name: "Kayaking", img: kayakingImg },
  { name: "Camping", img: campingImg },
];

export const rooms = [
  {
    name: "Premium Room",
    desc: "Comfortable stay with garden view and modern amenities.",
    price: "₹6,999",
    img: premiumRoomImg,
    amenities: ["Free WiFi", "AC", "Breakfast"],
  },
  {
    name: "Luxury Villa",
    desc: "Private villa with pool, gazebos and exclusive services.",
    price: "₹14,999",
    img: luxuryVillaImg,
    amenities: ["Private Pool", "Butler Service", "Breakfast"],
  },
  {
    name: "Executive Suite",
    desc: "Spacious suite with premium facilities and balcony.",
    price: "₹9,999",
    img: executiveSuiteImg,
    amenities: ["Free WiFi", "Balcony", "Mini Bar"],
  },
];

export const gallery = [
  { alt: "Warm boardwalk lights framing a lakeside resort at dusk", img: heroImg },
  { alt: "Aerial view of the green resort grounds", img: aerialImg },
  { alt: "Guest ziplining through the forest canopy", img: ziplineImg },
  { alt: "Golden dock stretching into the lake at sunset", img: goldenDockImg },
  { alt: "Luxury villa by the pool at golden hour", img: luxuryVillaImg },
  { alt: "Guest meditating in the golden forest light", img: meditationImg },
  { alt: "Wedding canopy decorated for a twilight ceremony", img: weddingImg },
];

export const testimonials = [
  {
    name: "Amit Sharma",
    city: "Jaipur",
    avatar: "https://i.pravatar.cc/160?img=12",
    quote:
      "An absolutely stunning escape. The villas are spacious, the food was exceptional, and the adventure park kept our kids busy all weekend.",
  },
  {
    name: "Priya Mehta",
    city: "Delhi",
    avatar: "https://i.pravatar.cc/160?img=45",
    quote:
      "The naturopathy and yoga sessions at sunrise were transformative. I left feeling lighter, calmer and completely reconnected with nature.",
  },
  {
    name: "Rahul & Ananya",
    city: "Udaipur",
    avatar: "https://i.pravatar.cc/160?img=32",
    quote:
      "We hosted our wedding here and every single detail was perfect. The mandap under the fairy lights was pure magic for our families.",
  },
  {
    name: "Kavya Nair",
    city: "Mumbai",
    avatar: "https://i.pravatar.cc/160?img=20",
    quote:
      "Our corporate retreat felt effortless — great meeting spaces by day and bonfires by the lake at night. The team is still talking about it.",
  },
  {
    name: "Vikram Singh",
    city: "Gurugram",
    avatar: "https://i.pravatar.cc/160?img=59",
    quote:
      "Ziplining across the Aravalli slopes was the highlight of our year. Warm hospitality from check-in to check-out.",
  },
];
