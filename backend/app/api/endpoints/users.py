from typing import Any
from fastapi import APIRouter, Depends
from app.api.deps import SessionDep, CurrentUser
from app.models.user import User
from app.schemas.user import UserOut, UserUpdate

router = APIRouter()

@router.get("/me", response_model=UserOut)
def read_user_me(current_user: CurrentUser) -> Any:
    return current_user

@router.put("/me", response_model=UserOut)
def update_user_me(
    *,
    db: SessionDep,
    user_in: UserUpdate,
    current_user: CurrentUser,
) -> Any:
    if user_in.full_name is not None:
        current_user.full_name = user_in.full_name
    if user_in.email is not None:
        current_user.email = user_in.email
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user
