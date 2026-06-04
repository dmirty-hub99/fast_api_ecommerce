from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.auth import get_current_user
from app.db_depends import get_async_db
from app.models import Product, User
from app.models.reviews import Review as ReviewModel
from app.schemas import ReviewCreate, Review as ReviewSchema

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)


@router.get('/', response_model=list[ReviewSchema])
async def get_all_reviews(db: AsyncSession = Depends(get_async_db)):
    result = await db.scalars(
        select(ReviewModel).where(ReviewModel.is_active == True)
    )
    return result.all()


@router.get('/product/{product_id}', response_model=list[ReviewSchema])
async def get_review_by_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    result_product = await db.scalars(
        select(Product).where(Product.id == product_id, Product.is_active == True)
    )
    product = result_product.first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    reviews_result = await db.scalars(
        select(ReviewModel).where(ReviewModel.product_id == product.id, ReviewModel.is_active == True)
    )
    return reviews_result.all()


@router.post('/', response_model=ReviewSchema)
async def create_review(
        review_data: ReviewCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != 'buyer':
        raise HTTPException(status_code=403, detail="Only buyer can perform this action")
    product_result = await db.execute(
        select(Product).where(Product.id == review_data.product_id, Product.is_active == True)
    )
    product = product_result.first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db_review = ReviewModel(**review_data.model_dump(), user_id=current_user.id)
    db.add(db_review)
    await db.commit()
    return db_review


@router.delete('/{review_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
        review_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user)
):
    review_result = await db.scalars(
        select(ReviewModel).where(ReviewModel.id == review_id, ReviewModel.is_active == True)
    )
    review = review_result.first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.user_id != current_user.id or current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="You are not allowed to perform this action")
    review.is_active = False
    await db.commit()
    return {"status": "success", "message": "Review marked as inactive"}
