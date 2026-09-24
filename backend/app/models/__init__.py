"""SQLAlchemy models package.

Importing every model here guarantees that Alembic autogenerate and
`Base.metadata.create_all()` see the complete schema.
"""

from app.models.address import Address
from app.models.brand import Brand
from app.models.cart import Cart, CartItem
from app.models.category import Category
from app.models.coupon import Coupon
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.product import Product, ProductImage, ProductVariant
from app.models.review import Review
from app.models.role import Role
from app.models.user import User
from app.models.wishlist import Wishlist, WishlistItem

__all__ = [
    "Address",
    "Brand",
    "Cart",
    "CartItem",
    "Category",
    "Coupon",
    "Order",
    "OrderItem",
    "Payment",
    "Product",
    "ProductImage",
    "ProductVariant",
    "Review",
    "Role",
    "User",
    "Wishlist",
    "WishlistItem",
]
