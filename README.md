# FlipStore — Full-Stack E-Commerce Website

A modern, production-ready e-commerce platform built with a **React (Vite) frontend** and a **FastAPI + PostgreSQL backend**.

> **Status: Phase 6 complete** (admin dashboard: stats, catalog/order management, customers). Remaining phases are listed in the [Roadmap](#roadmap) below.

## Technology Stack

| Layer     | Technologies |
|-----------|--------------|
| Frontend  | React 19, Vite 7, React Router 7, Axios, Tailwind CSS 4, React Hook Form + Zod |
| Backend   | Python, FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, JWT, bcrypt |
| Database  | PostgreSQL (SQLite fallback for quick local dev/tests) |
| Tooling   | `.env` configuration, Swagger/OpenAPI docs, pytest suites, Docker (Phase 8) |

## Project Structure

```
flip/
├── frontend/            # React + Vite storefront & admin
│   ├── src/
│   │   ├── components/  # Reusable UI (Header, Footer, ProductCard, ...)
│   │   ├── pages/       # Route-level pages
│   │   ├── layouts/     # StoreLayout, AdminLayout
│   │   ├── hooks/       # Custom React hooks
│   │   ├── services/    # Axios API layer (JWT interceptors)
│   │   ├── context/     # React Context providers
│   │   ├── store/       # Redux Toolkit (if selected)
│   │   ├── utils/       # Helpers (formatting, validation)
│   │   ├── assets/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── vite.config.js   # Tailwind plugin + /api dev proxy
│   ├── package.json
│   └── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py      # FastAPI app, CORS, error handlers
│   │   ├── core/        # config, database, security, exceptions
│   │   ├── models/      # SQLAlchemy models (Phase 2)
│   │   ├── schemas/     # Pydantic schemas (Phase 2)
│   │   ├── routers/     # /api/* route modules
│   │   ├── services/    # Business logic (Phase 2+)
│   │   ├── dependencies/# FastAPI dependencies
│   │   └── utils/       # Response envelope helpers
│   ├── alembic/         # Migrations (env.py, versions/)
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
├── .gitignore
└── README.md
```

## Requirements

- Python 3.11+
- Node.js 20+ (22 LTS recommended)
- PostgreSQL 14+ (optional for local dev — SQLite fallback available; Docker ships in Phase 8)

## Installation

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                # then edit the values
```

### 2. Frontend

```powershell
cd frontend
npm install
copy .env.example .env                # optional; Vite proxy works without it
```

## Environment Setup

**`backend/.env`** (never commit this file — see `.gitignore`):

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/flipystore
SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_urlsafe(64))">
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
STRIPE_SECRET_KEY=
ENVIRONMENT=development
```

Quick local dev without PostgreSQL:

```env
DATABASE_URL=sqlite:///./dev.db
```

**`frontend/.env`**:

```env
VITE_API_URL=http://localhost:8000
```

## Database Setup

Create the PostgreSQL database (once):

```powershell
psql -U postgres -c "CREATE DATABASE flipystore;"
```

## Migration Commands

```powershell
cd backend
alembic upgrade head                                # apply migrations
alembic revision --autogenerate -m "<description>"  # generate migration from models
alembic downgrade -1                                # roll back one migration
```

## Seed Commands

```powershell
# Roles + admin + 8 categories + 11 brands + 22 products + 3 coupons (idempotent)
cd backend
python -m app.seed
```

Seeded admin login: `admin@example.com` / `Admin@12345` (change in production).

## Development Commands

```powershell
# Terminal 1 — API (reload enabled), http://localhost:8000
cd backend
uvicorn app.main:app --reload

# Terminal 2 — Frontend, http://localhost:5173
cd frontend
npm run dev
```

Storefront pages: `/` (home), `/products` (listing + filters), `/products/:slug`
(detail), `/cart`, `/checkout` (7-step wizard), `/login`, `/register`, the
protected account area `/account` (profile, addresses, orders, order detail,
wishlist, change password), and the admin area `/admin` (dashboard, products,
categories & brands, orders, order detail, customers, customer detail — the
header shows an **Admin** link only for admin accounts).

Dev coupons seeded for checkout testing: **WELCOME10** (10% off), **SAVE20**
(20% off, min $100), **FLAT15** ($15 off, min $50).

## Testing

```powershell
cd backend
python -m pytest          # backend test suite (92 tests, isolated SQLite test DB)
```

Other useful scripts:

```powershell
npm run build     # production build of the frontend
npm run preview   # preview the production build
```

## Frontend Architecture (Phase 4 + 5 + 6)

```
frontend/src/
├── components/   Header, Footer, ProductCard, ProductGrid, ProductFilter,
│                 SearchBar, Pagination, QuantitySelector, RatingStars, Price,
│                 Modal, ConfirmDialog, LoadingSpinner, Skeleton, EmptyState,
│                 ProtectedRoute (auth guard with ?next= redirect),
│                 AdminRoute (admin-role guard for /admin/*)
├── pages/        Home, Products, ProductDetail, Login, Register, Cart,
│                 Checkout (7-step wizard), NotFound
│   ├── account/  AccountLayout (sidebar + Outlet), Profile, Addresses,
│   │             Orders, OrderDetail, Wishlist, ChangePassword
│   └── admin/    Dashboard (KPI cards, 7-day revenue chart, low stock),
│                 Products (search + CRUD modal), Categories (categories +
│                 brands tabs), Orders (status tabs + search), OrderDetail
│                 (lifecycle status controls), Customers, CustomerDetail
├── layouts/      StoreLayout, AdminLayout (sidebar + Outlet, admin topbar)
├── context/      AuthContext, CartContext, WishlistContext, ToastContext
├── services/     api.js (axios + JWT interceptors), catalog.js (browse API),
│                 shop.js (cart/wishlist/addresses/orders/account API),
│                 admin.js (dashboard/orders/customers + admin CRUD API)
├── hooks/        useDocumentTitle
└── utils/        format.js (currency/date/image fallback)
```

Global state uses **React Context** (auth, cart, wishlist, toasts). Cart and
wishlist are **guest-local (localStorage) and server-synced when signed in** —
on login the guest lines merge into the server cart/wishlist automatically, so
a cart follows the account across devices. All API calls go through
`services/api.js`, which attaches the JWT and handles 401 expiry redirects.
Filter/sort/page state on the listing page lives in the URL (shareable,
reload-safe).

**Checkout (Phase 5):** a 7-step wizard — information → shipping address (saved
or new, inline addresses persist to the address book) → billing (defaults to
shipping) → shipping method (standard $9.99, free over $75 after discount ·
express $19.99 · pickup free) → payment (mock card gateway or cash on delivery)
→ review (live totals incl. coupon) → confirmation. The backend reserves stock
atomically in a single transaction and rolls the whole order back if anything
fails.

**Admin dashboard (Phase 6):** every `/admin/*` route is wrapped in `AdminRoute`
(guests are sent to `/login?next=…`, signed-in non-admins never see admin UI)
and rendered by `AdminLayout` with a sidebar. The dashboard shows revenue,
orders, customers and products KPIs, a 7-day revenue bar chart,
orders-by-status chips, recent orders and low-stock alerts. Products and
categories/brands are managed through modal forms with confirm-before-delete;
orders are filterable by status/search and each order has instant
order/payment/shipping status controls; customers show order counts and
lifetime spend with links into their latest orders.

## API Documentation

With the backend running:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json
- **Health check:** http://localhost:8000/api/health

### Auth endpoints (Phase 2)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | — | Create customer account, returns JWT |
| POST | `/api/auth/login` | — | Verify credentials, returns JWT |
| POST | `/api/auth/logout` | Bearer | Revoke the presented token |
| GET | `/api/auth/me` | Bearer | Current user profile |
| POST | `/api/auth/forgot-password` | — | Issue password reset token |
| POST | `/api/auth/reset-password` | — | Reset password with token |
| PUT | `/api/auth/change-password` | Bearer | Change own password |
| GET/PUT | `/api/users/me` | Bearer | View / edit profile |
| GET | `/api/admin/ping` | Admin | RBAC guard probe (403 for customers) |

JWT claims: `sub` (user id), `role` (`customer`/`admin`), `jti`, `exp`.

### Catalog endpoints (Phase 3)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/products` | — | Search/filter/sort/paginate |
| GET | `/api/products/featured` | — | Featured collection |
| GET | `/api/products/new-arrivals` | — | Newest products |
| GET | `/api/products/best-sellers` | — | Best sellers |
| GET | `/api/products/{id\|slug}` | — | Detail (images + variants) |
| GET | `/api/products/{id\|slug}/related` | — | Related products |
| POST/PUT/DELETE | `/api/products...` | Admin | Catalog CRUD |
| GET | `/api/categories?tree=1` | — | Flat list or nested tree (with product counts) |
| POST/PUT/DELETE | `/api/categories...` | Admin | Category CRUD |
| GET | `/api/brands` | — | Brand list (with product counts) |
| POST/PUT/DELETE | `/api/brands...` | Admin | Brand CRUD |

Supported query params on `GET /api/products`:

```
search, category (uuid|slug), brand (uuid|slug), min_price, max_price,
min_rating, in_stock, is_featured,
sort (price_asc|price_desc|newest|oldest|rating|popular|name_asc|name_desc),
page, limit (1-50)
```

All endpoints return a consistent envelope:

```json
{ "success": true,  "message": "OK", "data": { } }
{ "success": false, "message": "Product not found", "data": null }
```

### Cart / orders endpoints (Phase 5)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/cart` | Bearer | Current cart with totals (subtotal, discount, shipping, tax) |
| POST | `/api/cart/items` | Bearer | Add product/variant (merges quantity, enforces stock) |
| PUT | `/api/cart/items/{id}` | Bearer | Update line quantity (stock-capped) |
| DELETE | `/api/cart/items/{id}` | Bearer | Remove line |
| DELETE | `/api/cart` | Bearer | Clear cart |
| PUT | `/api/cart/coupon` | Bearer | Apply coupon code (`code: null` removes) |
| GET | `/api/wishlist` | Bearer | Wishlist with product snapshots |
| POST | `/api/wishlist/items` | Bearer | Save product (idempotent) |
| DELETE | `/api/wishlist/items/{product_id}` | Bearer | Unsave product |
| GET/POST | `/api/addresses` | Bearer | Address book list / create (first = default) |
| PUT/DELETE | `/api/addresses/{id}` | Bearer | Update / delete address |
| POST | `/api/orders` | Bearer | **Checkout** — validates cart + stock, reserves inventory atomically, creates order + payment, applies coupon, clears cart |
| GET | `/api/orders?page=&limit=` | Bearer | Own order history (paginated) |
| GET | `/api/orders/{id}` | Bearer | Order detail (items, totals, addresses, payments) — owner or admin |

Totals rules: tax 8% of (subtotal − discount); standard shipping $9.99
(**free** when that amount ≥ $75), express $19.99, pickup free.
`payment_method`: `card_mock` → order confirmed/paid immediately;
`cod` → pending. Stock is decremented with conditional UPDATEs inside one
transaction — a concurrent-sell conflict returns 409 and rolls everything back.

### Admin endpoints (Phase 6)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/admin/stats` | Admin | KPIs: revenue, order/customer/product counts, low stock, orders-by-status, 7-day revenue series, recent orders |
| GET | `/api/admin/products?search=&page=&limit=` | Admin | All products **including inactive/drafts** (CRUD stays on `/api/products`) |
| GET | `/api/admin/orders?status=&search=&page=&limit=` | Admin | Every customer's orders, lifecycle filter, search by order # / name / email |
| GET | `/api/admin/orders/{id}` | Admin | Full order detail (items, totals, addresses, payments) + embedded customer |
| PATCH | `/api/admin/orders/{id}` | Admin | Update `status` / `payment_status` / `shipping_status` (validated values, at least one field) |
| GET | `/api/admin/customers?search=&page=&limit=` | Admin | Customers annotated with `order_count` + `total_spent` |
| GET | `/api/admin/customers/{id}` | Admin | Customer profile, spend stats and latest 5 orders |

Admin frontend routes: `/admin` (dashboard), `/admin/products`,
`/admin/categories`, `/admin/orders`, `/admin/orders/:orderId`,
`/admin/customers`, `/admin/customers/:customerId`.

## Docker Setup

*Docker configuration (frontend + backend + PostgreSQL via `docker compose up`) ships in **Phase 8**.*

## Production Deployment

*Deployment instructions ship in **Phase 8** (uvicorn/gunicorn workers, static build, reverse proxy, env hardening).*

## Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Project setup: React + Vite, FastAPI, PostgreSQL config, SQLAlchemy, Alembic, env config | ✅ |
| 2 | Database models, authentication, JWT, user roles | ✅ |
| 3 | Product/category APIs, search, filter, sorting | ✅ |
| 4 | React storefront: header, home, listing, details | ✅ |
| 5 | Cart, wishlist, checkout, orders | ✅ |
| 6 | Admin dashboard (products, categories, orders, customers) | ✅ |
| 7 | Payments, email notifications, reviews, coupons | ⬜ |
| 8 | Testing, security hardening, performance, Docker, deployment | ⬜ |
