#!/usr/bin/env python
"""Django's command-line utility for administrative tasks.

Run from project root (ICM/):
    python manage.py runserver
    python manage.py migrate
    python manage.py createsuperuser
"""
import os
import sys
from pathlib import Path

# Add icm_django/ to sys.path so 'icm_django' package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent / 'icm_django'))


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'icm_django.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH? Run: pip install -r requirements.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
