"""Seed default landing page partner section for the public home page."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from cms.models import LandingBenefit, LandingGalleryItem, LandingPageSettings

DEFAULT_BENEFITS = [
    ("trending", "High-Demand Investment Opportunity", "Premium resort villa assets with strong market interest."),
    ("money", "Attractive Brokerage & Incentive Structure", "Earn real money with clear partner incentives."),
    ("users", "Dedicated Sales & Marketing Support", "Partner with a team that helps you close faster."),
    ("clipboard", "Hassle-Free Booking Process", "Simple documentation and smooth booking flow."),
    ("shield", "Transparent Documentation & Timely Payouts", "Clear paperwork and reliable payout cycles."),
    ("handshake", "Long-Term Business Association", "Grow together with a lasting partner relationship."),
]

DEFAULT_GALLERY = [
    "Premium Lifestyle Assets",
    "Strong Appreciation Potential",
    "Maximize Earnings",
    "Real Money · Real Growth · Real Success",
]


class Command(BaseCommand):
    help = "Ensure landing page settings + default benefits exist"

    def handle(self, *args, **options):
        settings_obj = LandingPageSettings.current()
        self.stdout.write(f"Landing settings: {settings_obj.headline}")

        if not LandingBenefit.objects.exists():
            for i, (icon, title, body) in enumerate(DEFAULT_BENEFITS):
                LandingBenefit.objects.create(
                    title=title,
                    body=body,
                    icon_key=icon,
                    sort_order=i,
                    is_active=True,
                )
            self.stdout.write(f"Created {len(DEFAULT_BENEFITS)} landing benefits")
        else:
            self.stdout.write(f"Benefits already present ({LandingBenefit.objects.count()})")

        if not LandingGalleryItem.objects.exists():
            for i, title in enumerate(DEFAULT_GALLERY):
                LandingGalleryItem.objects.create(title=title, sort_order=i, is_active=True)
            self.stdout.write(f"Created {len(DEFAULT_GALLERY)} gallery placeholders (upload images in admin)")
        else:
            self.stdout.write(f"Gallery items already present ({LandingGalleryItem.objects.count()})")

        self.stdout.write(self.style.SUCCESS("Landing page CMS ready"))
