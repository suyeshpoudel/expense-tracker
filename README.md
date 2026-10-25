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

## Milestones

- [x] Milestone 0 - Project planning and setup
- [x] Milestone 1 - Authentication and personal dashboard
- [x] Milestone 2 - Expense and income transactions
- [x] Milestone 3 - Category management
- [x] Milestone 4 - Dashboard calculations and reports
- [x] Milestone 5 - Monthly budgets
- [x] Milestone 6 - Search, filtering, and user experience
- [x] Milestone 7 - Testing, security, and release preparation

## Decisions and assumptions

- The repository previously contained an unused Laravel scaffold. It was
  removed before Django was initialized; the history remains in Git.
- NPR is the display currency, configured as `CURRENCY_CODE = "NPR"` and
  exposed through a template context processor. It can become per-user
  configuration later.
- The default timezone is `Asia/Kathmandu`.
- Bootstrap is vendored in `static/vendor/bootstrap` so the application works
  offline and does not depend on a CDN at runtime.
- SQLite is used for local development. Production may use SQLite on a
  persistent single-instance volume, or PostgreSQL through `DATABASE_URL`.
- Registration uses Django's `UserCreationForm`, with an optional email field.
  A successful registration logs the user in and redirects to the dashboard.
- Logout is a POST request from the navigation bar, protected by CSRF.
- The dashboard shows current-month expenses, income and net cash flow from
  database aggregates, plus recent transactions, category spending, a six-month
  expense trend, and the current month's budget status. When no budget exists,
  the card links to the budget setup form.
- Registration is open to anyone who can reach the site. Restricting or closing
  registration should be considered before any public deployment.
- Transaction amounts are stored as `DecimalField(max_digits=12,
  decimal_places=2)` and must be greater than zero, enforced by a validator and
  a database check constraint.
- Transaction dates cannot be in the future. This is a form-level rule; it can
  be relaxed later if planned transactions become a feature.
- The transaction list shows totals for the active filter and uses 20 items per
  page. The dashboard reports the current calendar month; the reports page
  defaults to the current month and accepts any inclusive `date_from`/
  `date_to` range.
- Categories are user-owned, including the default categories, so one user's
  renames and deletions never affect another user.
- New accounts receive 10 expense and 6 income default categories inside the
  registration transaction. The `seed_default_categories` management command
  adds missing defaults for existing users using `get_or_create`, so it is
  repeatable and does not create duplicates. Running it again can recreate a
  default category that was intentionally deleted.
- Categories used by transactions cannot be deleted (`PROTECT`); transaction
  history is preserved. Users must reassign or delete those transactions first.
- Category names are unique per user and type, and form validation treats names
  case-insensitively. Category type cannot be changed after creation.
- The transaction form requires a category matching the transaction type.
  Transactions recorded before categories existed remain in the database as
  uncategorized and are labeled that way in the UI.
- Users can only list, view, edit, or delete their own transactions,
  categories, and budgets; owner lookups use `get_object_or_404` scoped to the
  logged-in user.
- The transaction list supports a case-insensitive search across titles,
  notes, and category names; type, category, date, and inclusive amount-range
  filters; and sorting by date, amount, or title. Totals reflect every active
  filter, and pagination preserves all filter and sort parameters. Choosing a
  sort order alone does not mark results as filtered. Amount range bounds must
  be zero or greater, with the maximum on or after the minimum.
- The reports page includes quick ranges for this month, last month, the last
  30 days, and year to date. The custom inclusive date-range form remains
  available, and the active preset is highlighted.
- Income and expense totals are calculated separately and never mixed. Net cash
  flow is income minus expenses, and expense category breakdowns and trends
  exclude income transactions.
- Every report query is scoped to the logged-in user. Dashboard and report data
  use database aggregation; the dashboard query count does not grow with the
  number of transactions.
- Empty periods show zero totals and explicit empty states instead of fabricated
  values. Transactions without a category, including pre-category records, are
  grouped under "Uncategorized" in expense breakdowns.
- Chart.js is vendored in `static/vendor/chartjs` with its MIT license. Charts
  are progressive enhancement: category totals remain visible in a table and
  monthly totals are available in an expandable data table.
- Each user can set one overall budget per calendar month. Budgets are stored
  against the first day of the month, use a native month picker in the form, and
  must be greater than zero. Past, current, and future months can be edited.
- Budget usage counts expense transactions only. Income does not increase the
  amount available; budgets are limits, not envelopes. Money does not roll over
  between months, and there are no per-category budgets yet.
- Remaining budget is the monthly budget minus that month's expenses. Usage at
  80% or more is marked "Near limit"; usage above 100% is "Over budget" and the
  progress bar caps at 100%. Every month with a budget shows its own usage.
- Budgets are user-owned and scoped to the logged-in user. Deleting a budget
  never deletes transactions. The reports page remains date-range based and does
  not apply monthly budget limits to arbitrary ranges.
- Production mode requires an explicit secret key and allowed hosts. It enables
  HTTPS redirects, secure session and CSRF cookies, HSTS, safe content-type and
  referrer policies, clickjacking protection, and same-origin opener isolation.
- The reverse-proxy HTTPS header is trusted only when explicitly enabled. CSRF
  trusted origins must be listed explicitly when the public origin differs from
  the request host.
- PostgreSQL is configured through a standard `DATABASE_URL`; SQLite remains the
  zero-configuration local fallback. Database connections use health checks and
  a 60-second maximum age for PostgreSQL.
- WhiteNoise serves compressed, hashed static assets in production after
  `collectstatic`. Gunicorn runs the WSGI application, and CI validates checks,
  migrations, tests, the production security check, static collection, and WSGI
  configuration.
