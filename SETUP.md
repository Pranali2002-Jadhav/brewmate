# BrewMate — Setup Guide
# READ THIS FIRST — especially if you had errors before

## STEP 0 — Delete old database (CRITICAL if you used a previous version)

If you already ran the old version, the SQLite database has outdated columns.
You MUST delete it before running this version.

In Windows Explorer, delete this file if it exists:
  C:\Users\Asus\PycharmProjects\Demo\brewmate\brewmate.db

Or in PowerShell:
  del brewmate.db

Also delete any old migration files (keep only __init__.py):
  del coffee\migrations\0001_initial.py
  del coffee\migrations\0002_*.py
  (delete any file that is NOT __init__.py inside coffee/migrations/)

---

## STEP 1 — Open the right folder in PyCharm

Extract the zip. Open the folder named "brewmate" (the one containing manage.py).
The structure must be:
  brewmate/          ← Open THIS in PyCharm
    manage.py
    requirements.txt
    brewmate/
      settings.py
    coffee/
      models.py

---

## STEP 2 — Create virtual environment

  python -m venv venv
  venv\Scripts\activate

---

## STEP 3 — Install packages

  pip install -r requirements.txt

---

## STEP 4 — Run migrations (NO prompts — zero questions)

  python manage.py makemigrations coffee
  python manage.py migrate

  Expected output:
    Creating tables...
    Running deferred SQL...
    OK

---

## STEP 5 — Load sample data

  python manage.py seed_data

  Expected output:
    ✓ Users ready
    ✓ 6 categories ready
    ✓ 20 products + inventory ready
    ✓ 10 tables ready
    ✅  Seeding complete!

---

## STEP 6 — Start the server

  python manage.py runserver

  Open: http://127.0.0.1:8000

---

## Login Accounts

  Role      Email                  Password
  ──────────────────────────────────────────
  Admin     admin@brewmate.com     admin123
  Staff     staff@brewmate.com     staff123
  Customer  demo@brewmate.com      demo123
  Customer  rahul@brewmate.com     demo123

---

## All Pages

  /                    → redirects to home
  /home/               → public homepage
  /menu/               → browse menu
  /register/           → sign up
  /login/              → login
  /dashboard/          → role-based dashboard
  /cart/               → shopping cart
  /checkout/           → place order (POST)
  /orders/             → order history
  /orders/<id>/        → order tracking
  /reservations/       → book a table
  /loyalty/            → points dashboard
  /notifications/      → notifications
  /staff/              → kitchen board (staff/admin)
  /staff/orders/       → all orders management
  /staff/inventory/    → stock management
  /admin-panel/        → admin dashboard
  /admin/              → Django admin

---

## API Endpoints (JSON)

  POST  /api/auth/register/       register new user
  POST  /api/auth/login/          login, returns JWT
  GET   /api/products/            all products
  GET   /api/categories/          all categories
  GET   /api/cart/                view cart (JWT required)
  POST  /api/cart/add/            add to cart (JWT required)
  GET   /api/orders/              my orders (JWT required)
  GET   /api/loyalty/             loyalty balance (JWT required)

---

## If you see "Session data corrupted" errors

This means the old database is still there.
Stop the server (Ctrl+C) and delete brewmate.db then run steps 4-6 again.

---

## Why these errors happened in the previous zip

1. loyalty_discount renamed to discount → Django asked "was X renamed to Y?"
   FIX: field is now always called "discount" with a default of 0.00

2. LoyaltyTransaction.account was non-nullable → Django asked for a default
   FIX: null=True, blank=True, default=None added

3. OrderItem.product was non-nullable → Django asked for a default
   FIX: fresh database has no existing rows, so this is not an issue

4. Session corruption → caused by old database with wrong schema
   FIX: delete brewmate.db and run migrate fresh
