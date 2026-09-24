"""Address book endpoints — /api/addresses"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_active_user, get_db
from app.schemas.address import AddressOut, AddressPayload, AddressUpdate
from app.services import addresses as address_service
from app.utils.responses import ok

router = APIRouter(prefix="/addresses", tags=["addresses"])


@router.get("", response_model=dict)
def list_addresses(
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    rows = address_service.list_addresses(db, user)
    return ok(data={"items": [AddressOut.model_validate(row) for row in rows]})


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_address(
    payload: AddressPayload,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    address = address_service.create_address(db, user, payload.model_dump())
    db.commit()
    return ok(message="Address saved", data=AddressOut.model_validate(address))


@router.put("/{address_id}", response_model=dict)
def update_address(
    address_id: uuid.UUID,
    payload: AddressUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    data = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    address = address_service.update_address(db, user, address_id, data)
    db.commit()
    return ok(message="Address updated", data=AddressOut.model_validate(address))


@router.delete("/{address_id}", response_model=dict)
def delete_address(
    address_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    address_service.delete_address(db, user, address_id)
    db.commit()
    return ok(message="Address deleted")
