from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.categories.services import seed_default_categories


class Command(BaseCommand):
    help = "Create any missing default categories for existing users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            help="Only seed categories for this username.",
        )

    def handle(self, *args, **options):
        users = get_user_model().objects.all()

        if options["user"]:
            users = users.filter(username=options["user"])
            if not users.exists():
                raise CommandError(
                    f"No user found with username {options['user']!r}."
                )

        total_created = 0
        for user in users.iterator():
            created = seed_default_categories(user)
            total_created += created
            if created:
                self.stdout.write(
                    f"{user.get_username()}: created {created} categories"
                )

        noun = "category" if total_created == 1 else "categories"
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {total_created} default {noun}."
            )
        )
