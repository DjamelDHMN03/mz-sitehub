from fastapi import APIRouter, status
from schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    return {
        "id": 1,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": True
    }
