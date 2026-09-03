# rep_fsparse — Django web migration

This is the first migration slice from the existing Flask UI to Django.

## What moved

- Flask routes in `web.py` -> `webapp/views.py` + `webapp/urls.py`
- Jinja templates -> Django templates under `webapp/templates/webapp/`
- `url_for()` / `static` -> Django `{% url %}` / `{% static %}`
- `request.session` -> Django session middleware
- Flask `send_file` / `send_from_directory` -> Django `FileResponse`
- Bootstrap 5.3 is now the primary UI framework.
- Existing parser/domain code in the repository's `app/` package is reused; the migration does not duplicate `sqlconnect`, logging, constants, or parser logic.
- The old CSS has been replaced by `webapp/static/webapp/css/app.css`; `legacy.css` is retained only as a reference during migration.

## Important repository integration

The uploaded source did not include the repository's existing `app/` package, `paths.json`, or image assets. Therefore this scaffold expects those files to remain in the repository root when you copy these files into `C:\Users\rando\Office Projects\rep_fsparse`.

Set `REPO_FS_ROOT` if the Django project is run from a different directory.

## Windows setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Current authentication behaviour

The Flask source currently has LDAP authentication commented out and uses `auth_success = True`. The Django migration preserves that behaviour. LDAP should be moved behind Django authentication before production deployment.

## Next migration slices

1. Move the existing `app/` package responsibilities into explicit Django service modules without changing business behaviour.
2. Replace the raw `app.sqlconnect` status/job access with a Django data-access/service layer; only introduce Django models when the existing DB schema has been mapped and verified.
3. Move configuration from `paths.json` into environment-specific Django settings while keeping the existing parser config files intact.
4. Add proper CSRF handling to every state-changing AJAX endpoint instead of the temporary `csrf_exempt` compatibility layer used in this first slice.
5. Replace the remaining browser `alert/confirm` flows with Bootstrap modals/toasts.
6. Add tests for every route before deleting `web.py`.
7. Once parity is verified, remove Flask and the old templates/static bundle.
