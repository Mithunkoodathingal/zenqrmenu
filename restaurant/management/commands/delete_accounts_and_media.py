# restaurant/management/commands/delete_accounts_and_media.py
import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from allauth.account.models import EmailAddress, EmailConfirmation
from allauth.socialaccount.models import SocialAccount
from django.apps import apps

User = get_user_model()

# Configure here the models and fields which may reference files you want removed.
MODEL_FILE_FIELDS = [
    # (app_label, model_name, ['file_field1', 'file_field2'])
    ('restaurant', 'Restaurant', ['cover_image', 'logo']),
    ('restaurant', 'FoodItem', ['image']),
    ('restaurant', 'Table', ['qr_code']),
]

def safe_remove(path):
    try:
        if not path:
            return False
        if os.path.isabs(path):
            full = path
        else:
            full = os.path.join(settings.MEDIA_ROOT, path)
        if os.path.exists(full) and os.path.isfile(full):
            os.remove(full)
            return True
    except Exception:
        return False
    return False

class Command(BaseCommand):
    help = "Delete users (non-super by default) and their linked allauth rows and media files."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Show what would be deleted without deleting.')
        parser.add_argument('--include-super', action='store_true', default=False,
                            help='Include superusers in deletion (dangerous).')
        parser.add_argument('--emails', nargs='*', default=None,
                            help='Only delete accounts with these email addresses (case-insensitive).')
        parser.add_argument('--delete-orphans', action='store_true', default=False,
                            help='After deletion, scan MEDIA_ROOT and try to remove unreferenced files.')

    def handle(self, *args, **opts):
        dry_run = opts['dry_run']
        include_super = opts['include_super']
        emails = opts['emails']
        delete_orphans = opts['delete_orphans']

        self.stdout.write(self.style.WARNING("=== delete_accounts_and_media ==="))
        self.stdout.write(f"MEDIA_ROOT: {getattr(settings, 'MEDIA_ROOT', 'NOT SET')}")
        self.stdout.write(f"Dry run: {dry_run}")
        self.stdout.write(f"Include superusers: {include_super}")
        self.stdout.write(f"Filter emails: {emails}")
        self.stdout.write("")

        # Build user queryset
        qs = User.objects.all()
        if not include_super:
            qs = qs.filter(is_superuser=False)
        if emails:
            # filter by EmailAddress or User.email
            lowered = [e.lower() for e in emails]
            qs = qs.filter(email__in=lowered) | qs.filter(email__in=[e for e in emails])
            # ensure case-insensitive match: use icontains union as simple approach
            # (we'll convert to distinct list)
            qs = User.objects.filter(email__iexact__in=emails) if False else qs

        qs = qs.distinct()
        users = list(qs)

        if not users:
            self.stdout.write(self.style.NOTICE("No users matched the criteria."))
            return

        self.stdout.write(f"Users matched: {len(users)}")
        for u in users[:200]:
            self.stdout.write(f"  - id={u.id} username={u.username} email={u.email}")

        # Find related allauth rows
        user_ids = [u.id for u in users]
        ea_qs = EmailAddress.objects.filter(user__in=user_ids)
        sa_qs = SocialAccount.objects.filter(user__in=user_ids)
        ec_qs = EmailConfirmation.objects.filter(email_address__in=ea_qs)  # email confirmations

        # Collect files to remove
        files = set()

        # model file fields
        for app_label, model_name, fields in MODEL_FILE_FIELDS:
            try:
                Model = apps.get_model(app_label, model_name)
            except LookupError:
                self.stdout.write(self.style.WARNING(f"Model not found {app_label}.{model_name}, skipping."))
                continue

            # Try some common related lookups:
            model_qs = Model.objects.none()
            # direct user FK
            if 'user' in [f.name for f in Model._meta.fields]:
                model_qs = Model.objects.filter(user__in=user_ids)
            elif 'owner' in [f.name for f in Model._meta.fields]:
                model_qs = Model.objects.filter(owner__in=user_ids)
            else:
                # try restaurant owner chain
                try:
                    model_qs = Model.objects.filter(restaurant__owner__in=user_ids)
                except Exception:
                    model_qs = Model.objects.none()

            for obj in model_qs:
                for f in fields:
                    val = getattr(obj, f, None)
                    if val:
                        # FieldFile may have .path or .name
                        p = None
                        try:
                            p = val.path
                        except Exception:
                            p = getattr(val, 'name', None)
                        if p:
                            if os.path.isabs(p):
                                files.add(p)
                            else:
                                files.add(os.path.join(settings.MEDIA_ROOT, p))

        # Also check common user profile attrs if present (avatar, picture)
        for u in users:
            for candidate in ('avatar', 'profile_image', 'picture', 'photo'):
                if hasattr(u, candidate):
                    val = getattr(u, candidate)
                    if val:
                        try:
                            p = val.path
                        except Exception:
                            p = getattr(val, 'name', None)
                        if p:
                            files.add(p if os.path.isabs(p) else os.path.join(settings.MEDIA_ROOT, p))

        # Report summary
        self.stdout.write("")
        self.stdout.write("Summary to delete:")
        self.stdout.write(f"  Users: {len(users)}")
        self.stdout.write(f"  EmailAddress rows: {ea_qs.count()}")
        self.stdout.write(f"  SocialAccount rows: {sa_qs.count()}")
        self.stdout.write(f"  EmailConfirmation rows: {ec_qs.count()}")
        self.stdout.write(f"  Media files referenced: {len(files)}")
        if files:
            for p in sorted(list(files))[:200]:
                self.stdout.write("    " + p)
            if len(files) > 200:
                self.stdout.write(f"    ... ({len(files)-200} more) ...")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("\nDry run finished — no changes made."))
            return

        # Proceed with deletion
        with transaction.atomic():
            # delete EmailConfirmation, EmailAddress, SocialAccount first
            ec_count, _ = ec_qs.delete()
            ea_count, _ = ea_qs.delete()
            sa_count, _ = sa_qs.delete()

            # delete media files
            deleted = []
            failed = []
            for p in files:
                try:
                    full = p if os.path.isabs(p) else os.path.join(settings.MEDIA_ROOT, p)
                    if os.path.exists(full) and os.path.isfile(full):
                        os.remove(full)
                        deleted.append(full)
                    else:
                        failed.append(full)
                except Exception:
                    failed.append(p)

            # delete users via queryset (let cascades run)
            u_deleted_count, _ = qs.delete()

        # final report
        self.stdout.write(self.style.SUCCESS("\nDeletion complete."))
        self.stdout.write(f"  EmailConfirmation rows deleted: {ec_count}")
        self.stdout.write(f"  EmailAddress rows deleted: {ea_count}")
        self.stdout.write(f"  SocialAccount rows deleted: {sa_count}")
        self.stdout.write(f"  Users deleted: {u_deleted_count}")
        self.stdout.write(f"  Files removed: {len(deleted)}")
        if failed:
            self.stdout.write(self.style.WARNING(f"  Files that could not be removed: {len(failed)}"))
            for p in failed[:50]:
                self.stdout.write("    " + p)

        # optionally remove orphans
        if delete_orphans:
            self.stdout.write("\nScanning MEDIA_ROOT for orphan files...")
            referenced = set()
            for app_label, model_name, fields in MODEL_FILE_FIELDS:
                try:
                    Model = apps.get_model(app_label, model_name)
                except LookupError:
                    continue
                for obj in Model.objects.all():
                    for f in fields:
                        val = getattr(obj, f, None)
                        if val:
                            name = getattr(val, 'name', None)
                            if name:
                                referenced.add(os.path.join(settings.MEDIA_ROOT, name))
            removed = 0
            for root, dirs, files_in in os.walk(settings.MEDIA_ROOT):
                for fn in files_in:
                    full = os.path.join(root, fn)
                    if full not in referenced:
                        try:
                            os.remove(full)
                            removed += 1
                        except Exception:
                            pass
            self.stdout.write(f"Orphan files removed: {removed}")
