"""Create or update a Django admin superuser (idempotent)."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ensure a staff superuser exists with the given credentials"

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)

    def handle(self, *args, **options):
        User = get_user_model()
        email = options["email"].strip().lower()
        username = options["username"].strip()
        password = options["password"]

        user = User.objects.filter(email__iexact=email).first()
        created = False
        if user is None:
            user = User.objects.create_superuser(email=email, password=password, username=username)
            created = True
        else:
            user.username = username
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.set_password(password)
            user.save()

        # Staff profile for RBAC console login
        from accounts.models import Role, StaffProfile

        code = f"SU-{username.upper()[:12]}"
        profile, _ = StaffProfile.objects.get_or_create(
            user=user,
            defaults={"employee_code": code},
        )
        admin_role = Role.objects.filter(name__iexact="Super Admin").first()
        if admin_role:
            profile.roles.add(admin_role)

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} superuser {email} (username={username})"))
