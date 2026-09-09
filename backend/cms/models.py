from django.db import models

from core.models import BaseModel


class NewsItem(BaseModel):
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at"]


class HelpTicket(BaseModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PENDING = "pending", "Pending"
        CLOSED = "closed", "Closed"

    subject = models.CharField(max_length=200)
    body = models.TextField()
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    associate_id = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["-created_at"]


class QRWalletSetting(BaseModel):
    label = models.CharField(max_length=80)
    wallet_address = models.CharField(max_length=255, blank=True)
    qr_image = models.ImageField(upload_to="qr/", blank=True, null=True)
    is_active = models.BooleanField(default=True)


class LandingPageSettings(BaseModel):
    """Singleton-ish public home page bottom / partner section."""

    eyebrow = models.CharField(max_length=120, default="Exclusive Channel Partner Invitation")
    headline = models.CharField(max_length=200, default="Join Our Resort Villa Partner Network")
    intro = models.TextField(
        blank=True,
        default=(
            "We invite brokers, consultants, and channel partners to join our "
            "Resort Villa Investment Project — designed for premium lifestyle assets "
            "and high appreciation potential."
        ),
    )
    investment_label = models.CharField(max_length=120, default="Investment starts at just")
    investment_value = models.CharField(max_length=80, default="₹ 2 Lakh")
    income_banner = models.CharField(max_length=160, default="One Time & Regular Income")
    cta_title = models.CharField(
        max_length=200,
        default="Join our channel partner network today and grow with us",
    )
    cta_body = models.TextField(
        blank=True,
        default="Partner with us to grow your business with transparent payouts and long-term association.",
    )
    slogan = models.CharField(
        max_length=200,
        default="Build Wealth | Earn More | Grow Together",
    )
    phone = models.CharField(max_length=40, blank=True, default="+91 800 0928 080")
    email = models.EmailField(blank=True, default="info@joyadventureresort.com")
    website = models.CharField(max_length=200, blank=True, default="www.joyadventureresort.com")
    address = models.TextField(
        blank=True,
        default="Joy Adventure Resort, Jaipur, Rajasthan",
    )
    banner_image = models.ImageField(
        upload_to="landing/",
        blank=True,
        null=True,
        help_text="Optional wide banner. Recommended: 1200×675 px (16:9), JPG/WebP under 800 KB.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Landing page settings"
        verbose_name_plural = "Landing page settings"

    def __str__(self) -> str:
        return self.headline or "Landing page"

    @classmethod
    def current(cls) -> "LandingPageSettings":
        obj = cls.objects.filter(is_active=True).order_by("created_at").first()
        if obj:
            return obj
        return cls.objects.create()


class LandingBenefit(BaseModel):
    title = models.CharField(max_length=160)
    body = models.CharField(max_length=255, blank=True)
    icon_key = models.CharField(
        max_length=40,
        default="trending",
        help_text="Icon key: trending, money, users, clipboard, shield, handshake",
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "created_at"]
        verbose_name = "Landing benefit"
        verbose_name_plural = "Landing benefits"

    def __str__(self) -> str:
        return self.title


class LandingGalleryItem(BaseModel):
    title = models.CharField(max_length=160)
    image = models.ImageField(
        upload_to="landing/gallery/",
        blank=True,
        null=True,
        help_text="Recommended: 800×500 px, JPG/WebP under 400 KB.",
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "created_at"]
        verbose_name = "Landing gallery item"
        verbose_name_plural = "Landing gallery"

    def __str__(self) -> str:
        return self.title


class KnowledgeItem(BaseModel):
    """Tutorial for a panel: PDF, image, or video. Staff upload; users only see their audience."""

    class Audience(models.TextChoices):
        ALL = "all", "Everyone"
        ASSOCIATE = "associate", "Associates"
        STAFF = "staff", "Admin / Staff"
        FINANCE = "finance", "Finance Manager"

    class MediaType(models.TextChoices):
        PDF = "pdf", "PDF"
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        LINK = "link", "Video link"

    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, help_text="Steps or short description.")
    audience = models.CharField(
        max_length=20, choices=Audience.choices, default=Audience.ALL, db_index=True
    )
    media_type = models.CharField(max_length=20, choices=MediaType.choices, default=MediaType.PDF)
    file = models.FileField(upload_to="knowledge/%Y/%m/", blank=True, null=True)
    video_url = models.URLField(blank=True, help_text="YouTube / Vimeo link if no file.")
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        verbose_name = "Knowledge item"
        verbose_name_plural = "Knowledge center"

    def __str__(self) -> str:
        return self.title
