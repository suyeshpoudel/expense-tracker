# Expense Tracker

A server-rendered personal expense tracker built with Django. The project is
being developed incrementally; the current state includes user accounts, a
login-protected dashboard, expense/income transactions, category management,
and monthly reports with charts.

## Stack

- Python 3.14 and Django 6.0
- Django Templates, HTML, CSS and vanilla JavaScript
- Bootstrap 5.3 and Chart.js 4.4 (both vendored locally) with a small custom
  stylesheet
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
python manage.py seed_default_categories  # existing users only
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

## Routes

| URL | Purpose | Access |
| --- | --- | --- |
| `/` | Home page | Public |
| `/accounts/register/` | Create an account | Public |
| `/accounts/login/` | Log in | Public |
| `/accounts/logout/` | Log out (POST only) | Any |
| `/dashboard/` | Personal dashboard and spending overview | Logged-in users |
| `/reports/` | Date-range income, expense, category and trend reports | Logged-in users |
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
python manage.py test
```

## Project structure

```
config/                 Project settings and root URL configuration
apps/accounts/          Registration, login and logout
apps/categories/        Category model, defaults, forms and views
apps/core/              Home, dashboard, reports, calculations and shared context
apps/transactions/      Transaction model, forms, views and tests
apps/common/            Shared form helpers
templates/              Shared, account, dashboard, report, transaction and category templates
static/css/             Application styles
static/js/              Chart.js configuration
static/vendor/          Vendored Bootstrap and Chart.js assets with licenses
requirements.txt        Python dependencies
```

Project conventions:

- Django apps live under `apps/` and are referenced as `apps.<name>`.
- Business rules belong in Python (models, forms, services), not templates.
- Monetary values will use `DecimalField`, never floating point.
- User-owned data will always be scoped to `request.user`.

## Milestones

- [x] Milestone 0 - Project planning and setup
- [x] Milestone 1 - Authentication and personal dashboard
- [x] Milestone 2 - Expense and income transactions
- [x] Milestone 3 - Category management
- [x] Milestone 4 - Dashboard calculations and reports
- [ ] Milestone 5 - Monthly budgets
- [ ] Milestone 6 - Search, filtering, and user experience
- [ ] Milestone 7 - Testing, security, and release preparation

## Decisions and assumptions

- The repository previously contained an unused Laravel scaffold. It was
  removed before Django was initialized; the history remains in Git.
- NPR is the display currency, configured as `CURRENCY_CODE = "NPR"` and
  exposed through a template context processor. It can become per-user
  configuration later.
- The default timezone is `Asia/Kathmandu`.
- Bootstrap is vendored in `static/vendor/bootstrap` so the application works
  offline and does not depend on a CDN at runtime.
- SQLite is used for local development; production database configuration will
  be addressed in Milestone 7.
- Registration uses Django's `UserCreationForm`, with an optional email field.
  A successful registration logs the user in and redirects to the dashboard.
- Logout is a POST request from the navigation bar, protected by CSRF.
- The dashboard shows current-month expenses, income and net cash flow from
  database aggregates, plus recent transactions, category spending, and a
  six-month expense trend. The remaining-budget card stays a placeholder until
  budgets are implemented in Milestone 5.
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
- Users can only list, view, edit, or delete their own transactions and
  categories; owner lookups use `get_object_or_404` scoped to the logged-in user.
- The transaction list can be filtered by type, category, and date range, and
  pagination preserves those filters.
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
