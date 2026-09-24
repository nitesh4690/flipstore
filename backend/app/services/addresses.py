"""Address book logic (account + checkout)."""

import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.address import Address


def list_addresses(db: Session, user) -> list[Address]:
    return list(
        db.scalars(
            select(Address)
            .where(Address.user_id == user.id)
            .order_by(Address.is_default_shipping.desc(), Address.created_at.desc())
        ).all()
    )


def get_address(db: Session, user, address_id: uuid.UUID) -> Address:
    address = db.get(Address, address_id)
    if address is None or address.user_id != user.id:
        raise AppError("Address not found", 404)
    return address


def _clear_defaults(db: Session, user, shipping: bool, billing: bool) -> None:
    if shipping:
        db.execute(
            update(Address)
            .where(Address.user_id == user.id, Address.is_default_shipping.is_(True))
            .values(is_default_shipping=False)
        )
    if billing:
        db.execute(
            update(Address)
            .where(Address.user_id == user.id, Address.is_default_billing.is_(True))
            .values(is_default_billing=False)
        )


def create_address(db: Session, user, data: dict) -> Address:
    _clear_defaults(db, user, data.get("is_default_shipping", False), data.get("is_default_billing", False))
    address = Address(user_id=user.id, **data)
    db.add(address)
    db.flush()
    # First address becomes the default automatically
    others = list_addresses(db, user)
    if len(others) == 1:
        address.is_default_shipping = True
        address.is_default_billing = True
        db.flush()
    return address


def update_address(db: Session, user, address_id: uuid.UUID, data: dict) -> Address:
    address = get_address(db, user, address_id)
    _clear_defaults(
        db,
        user,
        data.get("is_default_shipping") is True,
        data.get("is_default_billing") is True,
    )
    for key, value in data.items():
        if value is not None:
            setattr(address, key, value)
    db.flush()
    return address


def delete_address(db: Session, user, address_id: uuid.UUID) -> None:
    address = get_address(db, user, address_id)
    db.execute(delete(Address).where(Address.id == address.id))
    db.flush()
