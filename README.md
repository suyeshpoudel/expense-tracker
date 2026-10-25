# Expense Tracker

A server-rendered personal expense tracker built with Django. The project is
being developed incrementally; the current state includes user accounts, a
login-protected dashboard, expense/income transactions, category management,
monthly budgets, searchable and filterable transactions, reports with charts
and quick date ranges, and production-oriented security and deployment settings.

## Stack

- Python 3.14 and Django 6.0
- Django Templates, HTML, CSS and vanilla JavaScript
- Bootstrap 5.3 and Chart.js 4.4 (both vendored locally) with a small custom
  stylesheet
- WhiteNoise for production static files and Gunicorn as the WSGI server
- SQLite for local development and optional PostgreSQL for production
- Django's built-in test framework and GitHub Actions CI

No JavaScript framework, REST API, or separate frontend application is used.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_default_categories  # existing users only
python manage.py runserver
```

Open <http://127.0.0.1:8000/>.

The development defaults require no environment variables. Optional settings
can be provided through the environment (see `.env.example`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | insecure development key | Required in production; use a long random value |
| `DJANGO_DEBUG` | `true` | Set to `false` in production |
| `DJANGO_ALLOWED_HOSTS` | empty | Comma-separated host names; required in production |
| `DATABASE_URL` | empty (SQLite) | PostgreSQL URL, for example `postgresql://user:password@host:5432/expense_tracker` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty | Comma-separated HTTPS origins trusted for POST requests |
| `DJANGO_TRUST_X_FORWARDED_PROTO` | `false` | Trust `X-Forwarded-Proto` from a controlled reverse proxy |
| `DJANGO_SECURE_SSL_REDIRECT` | `true` in production | Redirect HTTP requests to HTTPS |
| `DJANGO_SESSION_COOKIE_SECURE` | `true` in production | Send session cookies over HTTPS only |
| `DJANGO_CSRF_COOKIE_SECURE` | `true` in production | Send the CSRF cookie over HTTPS only |
| `DJANGO_SECURE_HSTS_SECONDS` | 1 year in production, `0` in development | HSTS lifetime; set `0` while staging TLS |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | `true` in production | Apply HSTS to every subdomain |
| `DJANGO_SECURE_HSTS_PRELOAD` | `true` in production | Add the HSTS preload directive |
| `DJANGO_LOG_LEVEL` | `INFO` | Console log level |

The settings module reads real environment variables; it does not load `.env`
automatically. Export the values in your shell or use your process manager.

## Production deployment

The application fails fast if `DJANGO_DEBUG=false` is combined with a missing
`DJANGO_SECRET_KEY` or empty `DJANGO_ALLOWED_HOSTS`.

A typical single-instance deployment:

```bash
export DJANGO_DEBUG=false
export DJANGO_SECRET_KEY='replace-with-a-long-random-secret'
export DJANGO_ALLOWED_HOSTS='expenses.example.com'
export DJANGO_CSRF_TRUSTED_ORIGINS='https://expenses.example.com'
# Enable only behind a trusted TLS-terminating proxy:
# export DJANGO_TRUST_X_FORWARDED_PROTO=true

python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 127.0.0.1:8000
```

WhiteNoise serves files from `staticfiles/` after `collectstatic`, so a separate
static file server is optional. Run Gunicorn behind an HTTPS reverse proxy or a
platform load balancer. If TLS terminates at a trusted proxy that sets
`X-Forwarded-Proto` and strips client-supplied values, set
`DJANGO_TRUST_X_FORWARDED_PROTO=true`; otherwise Django may redirect in a loop or
misidentify secure requests. Never enable that setting for a proxy you do not
control.

Production defaults enable one-year HSTS with subdomains and preload. Keep
these defaults only after every subdomain supports HTTPS. To stage TLS, set
`DJANGO_SECURE_HSTS_SECONDS=0` and disable the include-subdomains and preload
options before serving real users.

SQLite remains the default for local development and small single-instance
deployments. Keep `db.sqlite3` on persistent storage and back it up regularly.
For multiple application instances or managed hosting, set `DATABASE_URL` to a
PostgreSQL URL; `psycopg` is included in `requirements.txt`. PostgreSQL URLs may
include `?sslmode=require`.

Operational notes:

- Application logs are written to stdout for collection by the hosting platform.
- Custom 400, 403, 404, and 500 pages avoid exposing framework debug details.
- Account registration is open by default; review or close it before a public launch.
- Email verification and password-reset flows are not implemented yet.
- Back up the database before applying migrations, and run
  `python manage.py check --deploy` for every environment.

## Routes

| URL | Purpose | Access |
| --- | --- | --- |
| `/` | Home page | Public |
| `/accounts/register/` | Create an account | Public |
| `/accounts/login/` | Log in | Public |
| `/accounts/logout/` | Log out (POST only) | Any |
| `/dashboard/` | Personal dashboard and spending overview | Logged-in users |
| `/reports/` | Date-range reports with quick presets | Logged-in users |
| `/budgets/` | Monthly budgets and spending usage | Logged-in users |
| `/budgets/new/` | Set a budget for a month | Logged-in users |
| `/budgets/<id>/edit/` | Edit a monthly budget | Owner only |
| `/budgets/<id>/delete/` | Delete confirmation for a budget | Owner only |
| `/transactions/` | Transaction list, totals and filters | Logged-in users |
| `/transactions/new/` | Add an expense or income | Logged-in users |
| `/transactions/<id>/` | Transaction details | Owner only |
| `/transactions/<id>/edit/` | Edit a transaction | Owner only |
| `/transactions/<id>/delete/` | Delete confirmation | Owner only |
| `/categories/` | Category list and usage counts | Logged-in users |
| `/categories/new/` | Add an expense or income category | Logged-in users |
| `/categories/<id>/edit/` | Rename a category | Owner only |
| `/categories/<id>/delete/` | Delete confirmation | Owner only |
| `/admin/` | Django admin | Staff users |

## Tests and checks

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Production configuration check:

```bash
DJANGO_DEBUG=false \
DJANGO_SECRET_KEY='replace-with-a-long-random-secret' \
DJANGO_ALLOWED_HOSTS='expenses.example.com' \
python manage.py check --deploy
```

## Project structure

```
config/                 Project settings, database parsing and root URLs
.github/workflows/      Continuous integration checks
apps/accounts/          Registration, login and logout
apps/budgets/           Monthly budget model, calculations, forms and views
apps/categories/        Category model, defaults, forms and views
apps/core/              Home, dashboard, reports, calculations and shared context
apps/transactions/      Transaction model, forms, views and tests
apps/common/            Shared form helpers
templates/              Shared, account, dashboard, report, budget, transaction and category templates
static/css/             Application styles
static/js/              Chart.js configuration
static/vendor/          Vendored Bootstrap and Chart.js assets with licenses
requirements.txt        Python dependencies
```

Project conventions:

- Django apps live under `apps/` and are referenced as `apps.<name>`.
- Business rules belong in Python (models, forms, services), not templates.
- Monetary values use `DecimalField`, never floating point.
- User-owned data is always scoped to `request.user`.

, the production security check, static collection, and WSGI
  configuration.
