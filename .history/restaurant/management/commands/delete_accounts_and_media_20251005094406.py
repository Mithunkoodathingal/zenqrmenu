# restaurant/management/commands/delete_accounts_and_media.py
import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.apps import apps

User = get_user_model()

# Models and their file fields to consider for deletion
# Add more (ModelClass, ['file_field_name', ...]) tuples as needed
MODEL_FILE_FIELDS = [
    # restaurant app models (adjust if your field names differ)
    ('restaurant', 'Restaurant', ['cover_image', 'logo']),
    ('restaurant', 'FoodItem', ['image']),
    ('restaurant', 'Table', ['qr_code']),
    # Add other app/model/fields here if you store images elsewhere
]


def delete_file_if_exists(path):
    """Delete a file path if it exists (safe)."""
    try:
        if path and os.path.isabs(path) and os.path.exists(path):
            os.remove(path)
            return True
        if path and not os.path.isabs(path):
            # make absolute relative to MEDIA_ROOT
            full = os.path.join(settings.MEDIA_ROOT, path)
            if os.path.exists(full):
                os.remove(full)
                return True
    except Exception as e:
        return False
    return False


class Command(BaseCommand):
    help = "Delete user accounts (optionally include superusers) and remove media files linked to them."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true', dest='dry_run', default=False,
            help='Show what would be deleted without actually deleting.'
        )
        parser.add_argument(
            '--include-super', action='store_true', dest='include_super', default=False,
            help='Also delete superusers. Use with caution.'
        )
        parser.add_argument(
            '--delete-orphans', action='store_true', dest='delete_orphans', default=False,
            help='After deleting referenced files, scan MEDIA_ROOT and remove files not referenced by any model.'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        include_super = options['include_super']
        delete_orphans = options['delete_orphans']

        self.stdout.write(self.style.WARNING("=== Delete Accounts & Linked Media Tool ==="))
        self.stdout.write("MEDIA_ROOT: %s" % getattr(settings, 'MEDIA_ROOT', 'NOT SET'))
        self.stdout.write("Dry run: %s" % dry_run)
        self.stdout.write("Include superusers: %s" % include_super)
        self.stdout.write("Delete orphans: %s" % delete_orphans)
        self.stdout.write("")

        qs = User.objects.all()
        if not include_super:
            qs = qs.filter(is_superuser=False)
        users = list(qs)

        if not users:
            self.stdout.write(self.style.NOTICE("No users found to delete (based on options)."))
            return

        # gather referenced file paths and related objects
        files_to_delete = set()
        user_ids = [u.id for u in users]
        self.stdout.write("Found %d user(s) to delete." % len(users))

        # gather EmailAddress and SocialAccount rows to delete
        ea_qs = EmailAddress.objects.filter(user__in=user_ids)
        sa_qs = SocialAccount.objects.filter(user__in=user_ids)

        # walk configured models to collect file field values for rows owned by these users
        for app_label, model_name, fields in MODEL_FILE_FIELDS:
            try:
                Model = apps.get_model(app_label, model_name)
            except LookupError:
                self.stderr.write(self.style.WARNING("Model not found: %s.%s - skipping" % (app_label, model_name)))
                continue

            # try to filter by user relationship if exists
            # many of your models may have 'owner' or 'restaurant' relation; we'll try some common patterns
            filters_by_user = {}
            # try direct user FK named 'user' or 'owner' or 'created_by' etc.
            possible_user_fields = ['user', 'owner', 'created_by']
            qs_model = Model.objects.all()
            matched = False
            for f in possible_user_fields:
                if f in [fld.name for fld in Model._meta.fields]:
                    qs_model = Model.objects.filter(**{f + '__in': user_ids})
                    matched = True
                    break

            if not matched:
                # fallback: if model has FK to Restaurant which in turn has owner=user
                # e.g. FoodItem.category.restaurant.owner... we can't easily walk all relations generically.
                # We'll just attempt to filter by 'restaurant__owner__in' if field exists.
                try:
                    qs_model = Model.objects.filter(restaurant__owner__in=user_ids)
                except Exception:
                    qs_model = Model.objects.none()

            for obj in qs_model:
                for f in fields:
                    val = getattr(obj, f, None)
                    if not val:
                        continue
                    # val may be a FieldFile — use .path if available, else .name
                    p = None
                    try:
                        # prefer path (absolute) if available
                        p = val.path
                    except Exception:
                        p = getattr(val, 'name', None)
                    if p:
                        # if path is absolute or relative, normalize and add
                        if os.path.isabs(p):
                            files_to_delete.add(p)
                        else:
                            files_to_delete.add(os.path.join(settings.MEDIA_ROOT, p))
        # Also include files referenced directly in user profile if any (common patterns)
        # Example: if you have User.profile.avatar (not declared above), extend here.

        # summarize
        self.stdout.write("")
        self.stdout.write("Summary of items to delete:")
        self.stdout.write("  Users: %d" % len(users))
        self.stdout.write("  EmailAddress rows: %d" % ea_qs.count())
        self.stdout.write("  SocialAccount rows: %d" % sa_qs.count())
        self.stdout.write("  Media files referenced: %d" % len(files_to_delete))
        if len(files_to_delete) > 0:
            for p in sorted(list(files_to_delete))[:200]:
                self.stdout.write("    " + p)
            if len(files_to_delete) > 200:
                self.stdout.write("    ... (%d more) ..." % (len(files_to_delete) - 200))

        if dry_run:
            self.stdout.write(self.style.SUCCESS("\nDry run complete — no changes made."))
            return

        # proceed with deletion inside transaction for DB items
        with transaction.atomic():
            # delete files first
            deleted_files = []
            failed_files = []
            for p in files_to_delete:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                        deleted_files.append(p)
                    else:
                        # maybe path points to MEDIA_ROOT/<name> but was absolute already; try stripping MEDIA_ROOT
                        if p.startswith(settings.MEDIA_ROOT):
                            alt = p[len(settings.MEDIA_ROOT):].lstrip(os.sep)
                            alt_full = os.path.join(settings.MEDIA_ROOT, alt)
                            if os.path.exists(alt_full):
                                os.remove(alt_full)
                                deleted_files.append(alt_full)
                            else:
                                failed_files.append(p)
                        else:
                            failed_files.append(p)
                except Exception as exc:
                    failed_files.append(p)

            # delete EmailAddress and SocialAccount rows
            ea_deleted_count, _ = ea_qs.delete()
            sa_deleted_count, _ = sa_qs.delete()

            # delete users (this cascades to other related rows depending on your models)
            user_deleted_count = 0
            for u in users:
                try:
                    uid = u.id
                    u.delete()
                    user_deleted_count += 1
                except Exception as exc:
                    self.stderr.write(self.style.ERROR("Failed to delete user id=%s: %s" % (getattr(u, 'id', None), exc)))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Deletion complete."))
        self.stdout.write("  Deleted users: %d" % user_deleted_count)
        self.stdout.write("  Deleted EmailAddress rows: %d" % ea_deleted_count)
        self.stdout.write("  Deleted SocialAccount rows: %d" % sa_deleted_count)
        self.stdout.write("  Files removed: %d" % len(deleted_files))
        if failed_files:
            self.stdout.write(self.style.WARNING("  Files that could not be removed: %d" % len(failed_files)))
            for p in failed_files[:50]:
                self.stdout.write("    " + p)
            if len(failed_files) > 50:
                self.stdout.write("    ...")

        # optionally delete orphans: scan MEDIA_ROOT and remove files not referenced by any model
        if delete_orphans:
            self.stdout.write("")
            self.stdout.write("Scanning for orphaned files in MEDIA_ROOT (this may take awhile)...")
            referenced = set()
            # walk through models in MODEL_FILE_FIELDS and add names
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
            for root, dirs, files in os.walk(settings.MEDIA_ROOT):
                for fn in files:
                    full = os.path.join(root, fn)
                    if full not in referenced:
                        try:
                            os.remove(full)
                            removed += 1
                        except Exception:
                            pass
            self.stdout.write("Orphan files removed: %d" % removed)
