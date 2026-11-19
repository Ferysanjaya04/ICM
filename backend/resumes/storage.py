"""Private uploads with confined, read-only fallback for pre-existing CV files."""

from pathlib import Path, PureWindowsPath

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files import File
from django.core.files.storage import FileSystemStorage, Storage


class _ConfinedFileSystemStorage(FileSystemStorage):
    def path(self, name):
        # Reject both POSIX and Windows traversal/absolute paths, including drive/ADS names.
        if (
            not isinstance(name, str) or not name or "\x00" in name
            or ":" in name or PureWindowsPath(name).drive
        ):
            raise SuspiciousFileOperation("Invalid private document path.")
        # Django's collision handling uses os.path.join (backslashes on Windows).
        name = name.replace("\\", "/")
        if any(part in {"", ".", ".."} for part in name.split("/")):
            raise SuspiciousFileOperation("Invalid private document path.")
        root = Path(self.location).resolve()
        target = (root / name).resolve()
        if not target.is_relative_to(root) or target == root:
            raise SuspiciousFileOperation("Document path is outside its storage root.")
        return str(target)


class PrivateResumeStorage(Storage):
    """No public URL. New writes use private storage; legacy paths remain readable.

    Used as default storage so existing FileFields and database names need no migration.
    The legacy directory is never a write or delete destination. Host filesystem ACLs
    must also prevent untrusted users from modifying roots or creating symlinks.
    """

    def _stores(self):
        return (
            _ConfinedFileSystemStorage(
                # Match path()'s canonical root. Otherwise Windows short paths or
                # junction aliases can make FileSystemStorage._save return ../... .
                location=Path(settings.PRIVATE_RESUME_ROOT).resolve(),
                file_permissions_mode=0o600,
                directory_permissions_mode=0o700,
            ),
            _ConfinedFileSystemStorage(location=Path(settings.MEDIA_ROOT).resolve()),
        )

    def path(self, name):
        primary, legacy = self._stores()
        primary_path = primary.path(name)
        if Path(primary_path).exists():
            return primary_path
        legacy_path = legacy.path(name)
        return legacy_path if Path(legacy_path).exists() else primary_path

    def _open(self, name, mode="rb"):
        if mode not in {"r", "rb"}:
            raise ValueError("Use storage.save() to write private documents.")
        return File(open(self.path(name), mode))

    def _save(self, name, content):
        primary, _ = self._stores()
        return primary._save(name, content)

    def exists(self, name):
        primary, legacy = self._stores()
        return primary.exists(name) or legacy.exists(name)

    def size(self, name):
        return Path(self.path(name)).stat().st_size

    def url(self, name):
        raise ValueError("Private documents have no public URL; use the authenticated download endpoint.")
