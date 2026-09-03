#!/usr/bin/env python
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BASE_DIR)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rep_fsparse_web.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
