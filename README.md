# BrewMate — Coffee Shop Management System

**Full-stack Django application with SQL database, custom security, REST API, and cloud-ready architecture.**

---

## Quick Start (5 Steps)

```bash
# 1. Create & activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 2. Install all dependencies
pip install -r requirements.txt

# 3. Run database migrations
python manage.py makemigrations
python manage.py migrate

# 4. Load sample data (menu, users, tables)
python manage.py seed_data

# 5. Start the server
python manage.py runserver
```

Open: **http://127.0.0.1:8000**

---

## Login Accounts (created by seed_data)

| Role     | Email                 | Password  | Access                                    |
|----------|-----------------------|-----------|-------------------------------------------|
| Admin    | admin@brewmate.com    | admin123  | Everything + Admin Dashboard + Django Admin |
| Staff    | staff@brewmate.com    | staff123  | Kitchen Board + Orders + Inventory        |
| Customer | demo@brewmate.com     | demo123   | Ordering + Reservations + Loyalty         |
| Customer | rahul@brewmate.com    | demo123   | Same as above                             |

---

## All Pages & URLs

| URL                          | Page                   | Access         |
|------------------------------|------------------------|----------------|
| /                            | Redirect to home       | All            |
| /home/                       | Homepage               | All            |
| /about/                      | About page             | All            |
| /menu/                       | Full menu              | All            |
| /menu/<slug>/                | Product detail         | All            |
| /register/                   | Sign up                | Public         |
| /login/                      | Login                  | Public         |
| /logout/                     | Logout                 | Auth           |
| /dashboard/                  | Role-based dashboard   | Auth           |
| /profile/                    | Edit profile           | Auth           |
| /cart/                       | Shopping cart          | Customer       |
| /cart/add/<id>/              | Add to cart            | Customer       |
| /checkout/                   | Place order            | Customer       |
| /orders/                     | Order history          | Customer       |
| /orders/<id>/                | Order detail + track   | Auth           |
| /reservations/               | Book + view tables     | Customer       |
| /loyalty/                    | Points dashboard       | Customer       |
| /notifications/              | Notifications          | Auth           |
| /staff/                      | Kitchen live board     | Staff + Admin  |
| /staff/orders/               | All orders management  | Staff + Admin  |
| /staff/inventory/            | Stock management       | Staff + Admin  |
| /admin-panel/                | Admin dashboard        | Admin only     |
| /admin-panel/products/       | Menu management        | Admin only     |
| /admin-panel/users/          | User management        | Admin only     |
| /admin-panel/reservations/   | Reservation management | Admin only     |
| /admin/                      | Django admin panel     | Admin only     |

---

## REST API Endpoints (JSON)

All APIs require JWT token in header: `Authorization: Bearer <token>`

| Method | URL                          | Auth         | Description              |
|--------|------------------------------|--------------|--------------------------|
| POST   | /api/auth/register/          | None         | Register new user        |
| POST   | /api/auth/login/             | None         | Login, get JWT tokens    |
| GET    | /api/categories/             | None         | All categories           |
| GET    | /api/products/               | None         | All available products   |
| GET    | /api/products/?category=<id> | None         | Filter by category       |
| GET    | /api/products/<id>/          | None         | Single product           |
| GET    | /api/cart/                   | JWT          | View cart                |
| POST   | /api/cart/add/               | JWT          | Add item to cart         |
| GET    | /api/orders/                 | JWT          | My orders                |
| GET    | /api/orders/<id>/            | JWT          | Single order             |
| GET    | /api/orders/all/             | Staff+Admin  | All orders               |
| PATCH  | /api/orders/<id>/status/     | Staff+Admin  | Update order status      |
| GET    | /api/reservations/           | JWT          | My reservations          |
| GET    | /api/loyalty/                | JWT          | Loyalty account          |

### Example API calls:

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123","first_name":"Test"}'

# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@brewmate.com","password":"demo123"}'

# Get Menu (no auth needed)
curl http://localhost:8000/api/products/

# Get Cart (needs token)
curl http://localhost:8000/api/cart/ \
  -H "Authorization: Bearer <your_token>"
```

---

## Project Structure

```
brewmate/                        ← Open THIS in PyCharm
│
├── manage.py                    ← Django entry point
├── requirements.txt
├── Procfile                     ← For Render/Heroku
├── .env.example                 ← Copy to .env
├── brewmate.db                  ← SQLite database (auto-created)
│
├── brewmate/                    ← Django project config
│   ├── __init__.py
│   ├── settings.py              ← All settings
│   ├── urls.py                  ← Root URL routing
│   └── wsgi.py
│
├── coffee/                      ← Main app (all features)
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py                ← ALL 14 database models
│   ├── views.py                 ← ALL views (customer+staff+admin)
│   ├── urls.py                  ← HTML URL patterns
│   ├── api_urls.py              ← REST API URL patterns
│   ├── api_views.py             ← REST API views
│   ├── serializers.py           ← DRF serializers
│   ├── forms.py                 ← All Django forms
│   ├── admin.py                 ← Django admin config
│   ├── context_processors.py   ← Cart count, notif count
│   ├── management/commands/
│   │   └── seed_data.py        ← python manage.py seed_data
│   ├── migrations/
│   └── templates/coffee/
│       ├── base.html            ← Master layout
│       ├── home.html
│       ├── about.html
│       ├── menu.html
│       ├── product_detail.html
│       ├── login.html
│       ├── register.html
│       ├── customer_dashboard.html
│       ├── profile.html
│       ├── cart.html
│       ├── order_detail.html
│       ├── my_orders.html
│       ├── reservations.html
│       ├── loyalty.html
│       ├── notifications.html
│       ├── staff_home.html      ← Kitchen POS
│       ├── staff_orders.html
│       ├── inventory.html
│       ├── admin_home.html      ← Admin dashboard
│       ├── admin_products.html
│       ├── admin_product_form.html
│       ├── admin_users.html
│       ├── admin_reservations.html
│       └── partials/
│           └── product_card.html
│
├── security/                    ← Custom security layer
│   ├── __init__.py
│   └── middleware.py            ← Rate limiter + RBAC + sanitizer
│
├── templates/errors/            ← Error pages
│   ├── 403.html
│   ├── 404.html
│   └── 500.html
│
├── static/                      ← CSS, JS, images
└── media/                       ← Uploaded files
```

---

## Database Models (14 tables)

| Model              | Table                 | Description                      |
|--------------------|-----------------------|----------------------------------|
| User               | coffee_user           | Custom user with roles           |
| Category           | coffee_category       | Menu categories                  |
| Product            | coffee_product        | Menu items                       |
| Inventory          | coffee_inventory      | Stock per product (OneToOne)     |
| Cart               | coffee_cart           | User cart (OneToOne with User)   |
| CartItem           | coffee_cartitem       | Items in cart (FK to Cart)       |
| Order              | coffee_order          | Placed orders                    |
| OrderItem          | coffee_orderitem      | Items in order (FK to Order)     |
| Payment            | coffee_payment        | Payment record (OneToOne Order)  |
| ShopTable          | coffee_shoptable      | Physical tables                  |
| Reservation        | coffee_reservation    | Table bookings                   |
| LoyaltyAccount     | coffee_loyaltyaccount | Points balance (OneToOne User)   |
| LoyaltyTransaction | coffee_loyaltytx      | Points earn/spend log            |
| Notification       | coffee_notification   | In-app notifications             |

---

## Security Layer (custom-built)

Located in `security/middleware.py`:

1. **RateLimitMiddleware** — 200 req/min per IP, supports 5000+ total hits
2. **AuditLogMiddleware** — logs every request for security audit
3. **InputSanitizer** — detects SQL injection and XSS in API data
4. **role_required()** — decorator for RBAC: `@role_required('admin')`
5. **DRF Permission classes** — `IsCustomerOrAbove`, `IsStaffOrAdmin`, `IsAdminOnly`

RBAC Rules:
- Customer: order, cart, reservations, loyalty (own data only)
- Staff: kitchen board, all orders, inventory management
- Admin: everything + product management + user management

---

## Cloud Deployment (Render)

1. Push code to GitHub
2. Create new Web Service on render.com
3. Set environment variables:
   - `SECRET_KEY=<random 50+ char string>`
   - `DEBUG=False`
   - `DATABASE_URL=<postgres connection string>`
4. Set build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
5. Set start command: `gunicorn brewmate.wsgi:application`

---

## To Use PostgreSQL (production)

In settings.py it auto-detects PostgreSQL when DATABASE_URL starts with "postgres".
Just set: `DATABASE_URL=postgres://user:password@host:5432/dbname`
And install: `pip install psycopg2-binary`

---

## Support 5000+ API Hits

- Rate limiter: 200 req/min per IP (5000+ total across 25+ users)
- DRF throttling: 100 req/min anon, 300 req/min authenticated
- Database indexes on frequently queried fields
- Paginated API responses (20 per page)
- Query optimization with select_related() and prefetch_related()
- Whitenoise for static file serving (no separate static server needed)
- Gunicorn with 4 workers in production
