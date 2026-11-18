from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.auth import get_current_buyer
from app.db_depends import get_async_db
from app.models.reviews import Review as ReviewModel
from app.models.products import Product as ProductModel
from app.schemas import ReviewCreate, ReviewResponse
from app.routers.products import get_active_product
from app.models.users import User as UserModel
from app.auth import get_current_user

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)
product_reviews_router = APIRouter(
    tags=["reviews"]
)
# все активные отзывы
@router.get("/", response_model=list[ReviewResponse])
async def get_all_reviews(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех активных отзывов.
    """
    stmt = select(ReviewModel).where(ReviewModel.is_active == True)
    result = await db.execute(stmt)
    reviews = result.scalars().all()
    return reviews

# все активные отзывы товара
@product_reviews_router.get("/products/{product_id}/reviews")
async def get_reviews_by_product_id(
    product_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Возвращает список активных отзывов указанного товара.
    """
    await get_active_product(product_id, db)

    stmt = select(ReviewModel).where(
        ReviewModel.is_active == True,
        ReviewModel.product_id == product_id
    )

    result = await db.execute(stmt)
    reviews = result.scalars().all()

    return reviews

# создание отзыва
@router.post("/", response_model=ReviewResponse)
async def create_review(
    review_data: ReviewCreate,
    current_user: UserModel = Depends(get_current_buyer),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Создаёт отзыв на товар от имени авторизованного покупателя
    и пересчитывает средний рейтинг товара.
    """
    product = await db.get(ProductModel, review_data.product_id)

    if product is None or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product not found or inactive"
        )

    new_review = ReviewModel(
        **review_data.model_dump(),
        user_id=current_user.id
    )
    db.add(new_review)
    await db.flush()

    result = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == review_data.product_id,
            ReviewModel.is_active.is_(True)
        )
    )
    avg_rating = result.scalar() or 0.0

    product.rating = avg_rating

    await db.commit()
    await db.refresh(new_review)

    return new_review
@router.delete("/{review_id}", response_model=ReviewResponse)
async def delete_review(review_id: int,
                        current_user: UserModel = Depends(get_current_user),
                        db: AsyncSession = Depends(get_async_db)):
    """
    Выполняет мягкое удаление отзыва по его ID и пересчитывает рейтинг товара.
    """
    review = await db.get(ReviewModel, review_id)
    if review is None or not review.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or inactive"
                            )
    if review.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to delete this review"
        )
    review.is_active = False
    product = await db.get(ProductModel, review.product_id)
    avg_rating = await db.scalar(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == review.product_id,
            ReviewModel.is_active == True
        )
    )
    product.rating = avg_rating or 0.0

    await db.commit()
    await db.refresh(review)

    return review