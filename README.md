# Expense Tracker

A server-rendered personal expense tracker built with Django. The project is
being developed incrementally; the current state is a working project scaffold
with a home page.

## Stack

- Python 3.14 and Django 6.0
- Django Templates, HTML, CSS and vanilla JavaScript
- Bootstrap 5.3 (vendored locally) with a small custom stylesheet
- SQLite for local development
- Django's built-in test framework

No JavaScript framework, REST API, or separate frontend application is used.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open <http://127.0.0.1:8000/>.

The development defaults require no environment variables. Optional settings
can be provided through the environment (see `.env.example`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | insecure development key | Secret key; must be set in production |
| `DJANGO_DEBUG` | `true` | Set to `false` in production |
| `DJANGO_ALLOWED_HOSTS` | empty | Comma-separated host names |

The settings module reads real environment variables; it does not load `.env`
automatically. Export the values in your shell or use your process manager.

## Tests and checks

```bash
python manage.py check
python manage.py test
```

## Project structure

```
config/                 Project settings and root URL configuration
apps/core/              Home page (dashboard/auth will live here)
templates/              Shared templates (base.html, core/home.html)
static/css/             Application styles
static/vendor/          Vendored Bootstrap CSS/JS and license
requirements.txt        Python dependencies
```

Project conventions:

- Django apps live under `apps/` and are referenced as `apps.<name>`.
- Business rules belong in Python (models, forms, services), not templates.
- Monetary values will use `DecimalField`, never floating point.
- User-owned data will always be scoped to `request.user`.

## Milestones

- [x] Milestone 0 - Project planning and setup
- [ ] Milestone 1 - Authentication and personal dashboard
- [ ] Milestone 2 - Expense and income transactions
- [ ] Milestone 3 - Category management
- [ ] Milestone 4 - Dashboard calculations and reports
- [ ] Milestone 5 - Monthly budgets
- [ ] Milestone 6 - Search, filtering, and user experience
- [ ] Milestone 7 - Testing, security, and release preparation

## Decisions and assumptions

- The repository previously contained an unused Laravel scaffold. It was
  removed before Django was initialized; the history remains in Git.
- NPR is the intended display currency, configured as `CURRENCY_CODE = "NPR"`.
  It is not yet shown in the UI and can become per-user configuration later.
- The default timezone is `Asia/Kathmandu`.
- Bootstrap is vendored in `static/vendor/bootstrap` so the application works
  offline and does not depend on a CDN at runtime.
- SQLite is used for local development; production database configuration will
  be addressed in Milestone 7.
