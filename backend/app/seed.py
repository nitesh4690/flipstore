"""Seed database with foundational + demo catalog data (idempotent).

Run:  python -m app.seed

Creates:
  - roles (customer/admin) + admin account
  - 8 categories (incl. one sub-category)
  - 11 brands
  - 22 realistic products (images, variants, sale prices, ratings)
  - 3 coupons
  - 12 demo reviewers + product reviews (product rating/count recomputed
    from the real review rows — one source of truth)
"""

import random
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.brand import Brand
from app.models.category import Category
from app.models.coupon import Coupon
from app.models.product import Product, ProductImage, ProductVariant
from app.models.review import Review
from app.models.role import Role
from app.models.user import User
from app.services.auth import DEFAULT_ROLES
from app.utils.datetime import utcnow
from app.utils.text import slugify, unique_sku

# Development defaults — override via environment in production deployments.
# Note: must be a valid email domain (email-validator rejects special-use TLDs like .local).
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin@12345"


def _img(slug: str, index: int = 1, size: str = "600/600") -> str:
    """Deterministic placeholder image URL (stable per product slug)."""
    return f"https://picsum.photos/seed/{slug}-{index}/{size}"


# ---------------------------------------------------------------------------
# Demo catalog data
# ---------------------------------------------------------------------------
CATEGORIES = [
    {"name": "Electronics", "description": "Gadgets, devices and accessories.", "image_url": _img("cat-electronics", 1, "800/400")},
    {"name": "Wearables", "parent": "Electronics", "description": "Smartwatches, fitness bands and trackers."},
    {"name": "Fashion", "description": "Clothing, footwear and accessories.", "image_url": _img("cat-fashion", 1, "800/400")},
    {"name": "Home & Kitchen", "description": "Appliances and essentials for your home.", "image_url": _img("cat-home", 1, "800/400")},
    {"name": "Beauty", "description": "Skincare, haircare and personal care.", "image_url": _img("cat-beauty", 1, "800/400")},
    {"name": "Sports & Outdoors", "description": "Fitness gear and outdoor equipment.", "image_url": _img("cat-sports", 1, "800/400")},
    {"name": "Books", "description": "Bestsellers, fiction and professional reads.", "image_url": _img("cat-books", 1, "800/400")},
    {"name": "Toys & Games", "description": "Toys, puzzles and board games.", "image_url": _img("cat-toys", 1, "800/400")},
]

BRANDS = ["Sonarc", "Novabook", "Technova", "VoltEdge", "Velvet & Co", "Brewstone",
          "HomeHaven", "PureGlow", "FitPulse", "PageTree", "PlayForge"]

PRODUCTS = [
    # Electronics ------------------------------------------------------------
    {"name": "Aurora Pro Wireless Noise-Cancelling Headphones", "category": "Electronics", "brand": "Sonarc",
     "price": 249.00, "sale_price": 199.00, "stock": 45, "rating": 4.6, "rating_count": 212, "featured": True,
     "description": "Over-ear headphones with adaptive active noise cancellation, 40-hour battery life, multipoint Bluetooth 5.3 and studio-grade 40mm drivers."},
    {"name": "Nebula X15 Ultrabook 15.6-inch (i7/16GB/512GB)", "category": "Electronics", "brand": "Novabook",
     "price": 999.00, "sale_price": 899.00, "stock": 18, "rating": 4.5, "rating_count": 96, "featured": True,
     "description": "Thin-and-light laptop with a 2.5K IPS display, Intel Core i7, 16GB LPDDR5 memory and a 512GB NVMe SSD. 14-hour battery and Thunderbolt 4."},
    {"name": "Stellar S24 Smartphone 5G", "category": "Electronics", "brand": "Technova",
     "price": 799.00, "sale_price": 749.00, "stock": 60, "rating": 4.7, "rating_count": 340, "featured": True,
     "description": "6.7-inch 120Hz AMOLED display, 50MP triple camera with OIS, 4900mAh battery with 65W fast charging and IP68 water resistance.",
     "variants": [
         {"name": "128GB / Obsidian", "sku": "S24-128-OBS", "attributes": {"storage": "128GB", "color": "Obsidian"}, "stock": 22},
         {"name": "256GB / Obsidian", "sku": "S24-256-OBS", "attributes": {"storage": "256GB", "color": "Obsidian"}, "stock": 24, "price": 849.00},
         {"name": "512GB / Arctic Blue", "sku": "S24-512-BLU", "attributes": {"storage": "512GB", "color": "Arctic Blue"}, "stock": 14, "price": 949.00},
     ]},
    {"name": "VoltEdge 65W USB-C GaN Charger", "category": "Electronics", "brand": "VoltEdge",
     "price": 39.99, "stock": 210, "rating": 4.4, "rating_count": 512,
     "description": "Pocket-size 65W charger with two USB-C and one USB-A port. Charges a laptop and phone simultaneously with smart power allocation."},
    {"name": "BeatGo Portable Bluetooth Speaker", "category": "Electronics", "brand": "Sonarc",
     "price": 59.99, "sale_price": 49.99, "stock": 80, "rating": 4.3, "rating_count": 178,
     "description": "IPX7 waterproof speaker with 24-hour playtime, deep bass radiators and stereo pairing. Weighs just 540g for travel."},

    # Fashion ----------------------------------------------------------------
    {"name": "Classic Cotton Crewneck T-Shirt", "category": "Fashion", "brand": "Velvet & Co",
     "price": 19.99, "stock": 320, "rating": 4.4, "rating_count": 430,
     "description": "Premium 220gsm combed cotton tee with a pre-shrunk fit that holds wash after wash.",
     "variants": [
         {"name": "Small / Red", "attributes": {"size": "S", "color": "Red"}, "stock": 40},
         {"name": "Medium / Red", "attributes": {"size": "M", "color": "Red"}, "stock": 55},
         {"name": "Large / Red", "attributes": {"size": "L", "color": "Red"}, "stock": 48},
         {"name": "Small / Blue", "attributes": {"size": "S", "color": "Blue"}, "stock": 42},
         {"name": "Medium / Blue", "attributes": {"size": "M", "color": "Blue"}, "stock": 51},
         {"name": "Large / Blue", "attributes": {"size": "L", "color": "Blue"}, "stock": 44},
     ]},
    {"name": "Urban Stretch Slim-Fit Jeans", "category": "Fashion", "brand": "Velvet & Co",
     "price": 59.99, "sale_price": 49.99, "stock": 95, "rating": 4.2, "rating_count": 156,
     "description": "Four-way stretch denim with a tapered leg, brushed metal hardware and a comfort waistband."},
    {"name": "Heritage Full-Grain Leather Belt", "category": "Fashion", "brand": "Velvet & Co",
     "price": 34.99, "stock": 140, "rating": 4.5, "rating_count": 89,
     "description": "Full-grain leather belt with a solid antique-brass buckle. Ages beautifully with wear."},
    {"name": "Silk Blend Oversized Scarf", "category": "Fashion", "brand": "Velvet & Co",
     "price": 27.50, "sale_price": 22.00, "stock": 76, "rating": 4.6, "rating_count": 64,
     "description": "Featherweight silk-blend scarf with hand-rolled edges and a subtle herringbone weave."},

    # Home & Kitchen ---------------------------------------------------------
    {"name": "Brewstone 12-Cup Programmable Coffee Maker", "category": "Home & Kitchen", "brand": "Brewstone",
     "price": 89.99, "sale_price": 69.99, "stock": 34, "rating": 4.5, "rating_count": 267, "featured": True,
     "description": "Programmable drip machine with a reusable gold-tone filter, 24-hour timer, brew-strength control and a warming plate."},
    {"name": "HomeHaven Non-Stick Cookware Set (10 Pieces)", "category": "Home & Kitchen", "brand": "HomeHaven",
     "price": 129.99, "stock": 27, "rating": 4.4, "rating_count": 198,
     "description": "Die-cast aluminium set with a PFOA-free ceramic coating: fry pan, sauté pan, saucepans, stockpot and lids."},
    {"name": "Stoneware Dinnerware Set (16 Pieces)", "category": "Home & Kitchen", "brand": "HomeHaven",
     "price": 74.99, "stock": 41, "rating": 4.3, "rating_count": 120,
     "description": "Reactive-glaze stoneware service for four: dinner plates, side plates, bowls and mugs. Dishwasher and microwave safe."},
    {"name": "AirTouch Cordless Stick Vacuum", "category": "Home & Kitchen", "brand": "HomeHaven",
     "price": 149.99, "sale_price": 119.99, "stock": 22, "rating": 4.2, "rating_count": 245,
     "description": "25kPa cordless vacuum with a HEPA filter, 45-minute runtime and an LED motorised brush roll for hard floors and carpets."},

    # Beauty -----------------------------------------------------------------
    {"name": "Vitamin C Brightening Serum 30ml", "category": "Beauty", "brand": "PureGlow",
     "price": 32.99, "sale_price": 27.99, "stock": 150, "rating": 4.7, "rating_count": 540, "featured": True,
     "description": "15% stabilised vitamin C with ferulic acid and hyaluronic acid to visibly brighten skin and fade dark spots."},
    {"name": "Daily Hydrating Face Moisturizer", "category": "Beauty", "brand": "PureGlow",
     "price": 24.99, "stock": 175, "rating": 4.5, "rating_count": 312,
     "description": "Lightweight ceramide moisturiser for all skin types. Fragrance-free, non-comedogenic, 48-hour hydration."},
    {"name": "Argan Repair Hair Mask 200ml", "category": "Beauty", "brand": "PureGlow",
     "price": 18.99, "stock": 120, "rating": 4.4, "rating_count": 145,
     "description": "Deep-conditioning mask with cold-pressed argan oil and keratin that restores shine in 5 minutes."},

    # Sports & Outdoors ------------------------------------------------------
    {"name": "Pro Yoga Mat 6mm (Non-Slip)", "category": "Sports & Outdoors", "brand": "FitPulse",
     "price": 29.99, "sale_price": 24.99, "stock": 190, "rating": 4.6, "rating_count": 389,
     "description": "Dense 6mm TPE mat with alignment guides, dual-texture grip and a free carry strap. Odour-resistant and eco-friendly."},
    {"name": "TrailMax 28L Hiking Backpack", "category": "Sports & Outdoors", "brand": "FitPulse",
     "price": 64.99, "stock": 58, "rating": 4.5, "rating_count": 134,
     "description": "Water-resistant 28L pack with a ventilated back panel, rain cover, hydration sleeve and hip-belt pockets."},
    {"name": "Adjustable Dumbbell Set 20kg", "category": "Sports & Outdoors", "brand": "FitPulse",
     "price": 119.99, "stock": 26, "rating": 4.4, "rating_count": 176,
     "description": "Space-saving adjustable dumbbells with a dial system from 2.5kg to 10kg per hand. Includes storage tray."},

    # Books ------------------------------------------------------------------
    {"name": "The Art of Clean Code (Paperback)", "category": "Books", "brand": "PageTree",
     "price": 34.99, "stock": 88, "rating": 4.8, "rating_count": 210, "featured": True,
     "description": "A practical guide to writing maintainable software: naming, structure, testing and refactoring patterns used by senior engineers."},
    {"name": "Building Resilient Systems (Hardcover)", "category": "Books", "brand": "PageTree",
     "price": 42.50, "sale_price": 36.00, "stock": 47, "rating": 4.7, "rating_count": 98,
     "description": "Designing distributed systems that survive failure — caching, queues, retries, idempotency and observability in practice."},

    # Toys & Games -----------------------------------------------------------
    {"name": "BrainWave Strategy Board Game", "category": "Toys & Games", "brand": "PlayForge",
     "price": 39.99, "sale_price": 32.99, "stock": 65, "rating": 4.6, "rating_count": 157,
     "description": "Award-winning strategy game for 2-5 players, ages 10+. 60-minute play time with modular board and 200 cards."},
]

COUPONS = [
    {"code": "WELCOME10", "discount_type": "percentage", "value": 10, "min_order_amount": 0,
     "description": "10% off your first order"},
    {"code": "SAVE20", "discount_type": "percentage", "value": 20, "min_order_amount": 100,
     "description": "20% off orders above 100"},
    {"code": "FLAT15", "discount_type": "fixed", "value": 15, "min_order_amount": 50,
     "description": "15 off orders above 50"},
]

# Demo reviewers — one shared password hash (they never sign in via the seed).
REVIEWERS = [
    ("Ava", "Chen"), ("Liam", "Ortiz"), ("Maya", "Patel"), ("Noah", "Kim"),
    ("Sofia", "Reyes"), ("Ethan", "Brooks"), ("Isla", "Novak"), ("Lucas", "Meyer"),
    ("Amara", "Diallo"), ("Jack", "Sullivan"), ("Yuki", "Tanaka"), ("Elena", "Rossi"),
]

REVIEW_COMMENTS = [
    "Exceeded my expectations — the build quality feels premium.",
    "Works exactly as described. Shipping was quick too.",
    "Solid value for the price. I'd buy it again.",
    "Good overall, though the packaging could be better.",
    "Been using it daily for a few weeks and no complaints.",
    "Matches the photos and the description accurately.",
    "Setup was effortless and it performs great.",
    "Happy with this purchase — it does exactly what I need.",
    "Decent product, though there are cheaper alternatives out there.",
    "Arrived earlier than expected and works perfectly.",
    "The little details are well thought out. Nice job.",
    "Reliable so far — support answered my questions quickly.",
    None,  # rating-only review
    None,
]


# ---------------------------------------------------------------------------
# Seed functions (all idempotent)
# ---------------------------------------------------------------------------
def seed_roles(db: Session) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for name, description in DEFAULT_ROLES.items():
        role = db.scalar(select(Role).where(Role.name == name))
        if role is None:
            role = Role(name=name, description=description)
            db.add(role)
            print(f"+ role: {name}")
        roles[name] = role
    db.flush()
    return roles


def seed_admin(db: Session, roles: dict[str, Role]) -> None:
    existing = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
    if existing is not None:
        print(f"= admin already exists: {ADMIN_EMAIL}")
        return

    admin = User(
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        first_name="Store",
        last_name="Admin",
        role_id=roles["admin"].id,
        is_active=True,
    )
    db.add(admin)
    print(f"+ admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}  (change in production!)")


def seed_categories(db: Session) -> dict[str, Category]:
    categories: dict[str, Category] = {}
    for entry in CATEGORIES:
        slug = slugify(entry["name"])
        category = db.scalar(select(Category).where(Category.slug == slug))
        if category is None:
            category = Category(
                name=entry["name"],
                slug=slug,
                description=entry.get("description"),
                image_url=entry.get("image_url"),
                is_active=True,
            )
            db.add(category)
            db.flush()
            print(f"+ category: {entry['name']}")
        categories[entry["name"]] = category
    db.flush()

    # Second pass: link sub-categories to their parents
    for entry in CATEGORIES:
        parent_name = entry.get("parent")
        if parent_name and categories[entry["name"]].parent_id is None:
            categories[entry["name"]].parent_id = categories[parent_name].id
    return categories


def seed_brands(db: Session) -> dict[str, Brand]:
    brands: dict[str, Brand] = {}
    for name in BRANDS:
        slug = slugify(name)
        brand = db.scalar(select(Brand).where(Brand.slug == slug))
        if brand is None:
            brand = Brand(name=name, slug=slug, is_active=True)
            db.add(brand)
            db.flush()
            print(f"+ brand: {name}")
        brands[name] = brand
    return brands


def seed_products(db: Session, categories: dict[str, Category], brands: dict[str, Brand]) -> None:
    for entry in PRODUCTS:
        slug = slugify(entry["name"])
        if db.scalar(select(Product).where(Product.slug == slug)) is not None:
            continue

        product = Product(
            name=entry["name"],
            slug=slug,
            description=entry["description"],
            sku=entry.get("sku") or f"SKU-{slug[:12].upper().replace('-', '')}",
            price=entry["price"],
            sale_price=entry.get("sale_price"),
            stock=entry["stock"],
            is_active=True,
            is_featured=entry.get("featured", False),
            rating=entry.get("rating", 0),
            rating_count=entry.get("rating_count", 0),
            category_id=categories[entry["category"]].id,
            brand_id=brands[entry["brand"]].id,
        )
        db.add(product)
        db.flush()

        # Two gallery images per product (first is primary)
        db.add(ProductImage(product_id=product.id, url=_img(slug, 1), alt_text=entry["name"], position=0, is_primary=True))
        db.add(ProductImage(product_id=product.id, url=_img(slug, 2, "800/600"), alt_text=f"{entry['name']} — alternate view", position=1))

        for variant in entry.get("variants", []):
            variant_stock = variant.get("stock", 0)
            db.add(ProductVariant(
                product_id=product.id,
                sku=variant.get("sku") or unique_sku(prefix=slug[:6].upper().replace("-", "")),
                name=variant.get("name"),
                attributes=variant.get("attributes", {}),
                price=variant.get("price"),
                stock=variant_stock,
            ))
            # Parent stock should cover its variants
            product.stock = max(product.stock, sum(
                v.get("stock", 0) for v in entry.get("variants", [])
            ))
        print(f"+ product: {entry['name']}")


def seed_coupons(db: Session) -> None:
    for entry in COUPONS:
        code = entry["code"].upper()
        if db.scalar(select(Coupon).where(Coupon.code == code)) is not None:
            continue
        db.add(Coupon(
            code=code,
            discount_type=entry["discount_type"],
            value=entry["value"],
            min_order_amount=entry["min_order_amount"],
            is_active=True,
        ))
        print(f"+ coupon: {code}")


def seed_reviews(db: Session, roles: dict[str, Role]) -> None:
    """Demo reviewers + review rows; product rating/count follow real rows."""
    shared_hash = hash_password("Reviewer123!")  # hashed once, reused for all

    reviewers: list[User] = []
    for first_name, last_name in REVIEWERS:
        email = f"{first_name.lower()}.{last_name.lower()}@example.com"
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                password_hash=shared_hash,
                first_name=first_name,
                last_name=last_name,
                role_id=roles["customer"].id,
                is_active=True,
            )
            db.add(user)
        reviewers.append(user)
    db.flush()

    inserted = 0
    seeded_products = 0
    for product in db.scalars(select(Product)).all():
        if db.scalar(select(Review.id).where(Review.product_id == product.id).limit(1)) is not None:
            continue  # idempotent — reviews already exist for this product

        rng = random.Random(f"flip-reviews-{product.slug}")
        count = rng.randint(5, 9)
        ratings: list[int] = []
        for reviewer in rng.sample(reviewers, count):
            rating = rng.choices([5, 4, 3], weights=[6, 3, 1])[0]
            review = Review(
                product_id=product.id,
                user_id=reviewer.id,
                rating=rating,
                comment=rng.choice(REVIEW_COMMENTS),
                is_approved=True,
            )
            # Backdate so the reviews page shows a natural spread of dates
            stamp = utcnow() - timedelta(days=rng.randint(3, 240))
            review.created_at = stamp
            review.updated_at = stamp
            db.add(review)
            ratings.append(rating)
            inserted += 1

        # Single source of truth: aggregates come from the rows we just wrote
        product.rating = round(sum(ratings) / len(ratings), 1)
        product.rating_count = len(ratings)
        db.add(product)
        seeded_products += 1

    db.flush()
    if seeded_products:
        print(f"+ reviews: {inserted} rows across {seeded_products} products "
              f"({len(REVIEWERS)} demo reviewers)")


def main() -> None:
    with SessionLocal() as db:
        roles = seed_roles(db)
        seed_admin(db, roles)
        categories = seed_categories(db)
        brands = seed_brands(db)
        seed_products(db, categories, brands)
        seed_coupons(db)
        seed_reviews(db, roles)
        db.commit()
    print("Seed complete.")


if __name__ == "__main__":
    main()
