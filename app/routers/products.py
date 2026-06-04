from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.auth import get_current_user, get_current_seller
from app.db_depends import get_async_db
from app.models import Product, Category, User as UserModel
from app.schemas import Product as ProductSchema, ProductCreate

# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get("/", response_model=list[ProductSchema])
async def get_all_products(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех товаров.
    """
    result = await db.scalars(select(Product).where(Product.is_active == True))
    return result.all()


@router.post("/", response_model=ProductSchema)
async def create_product(
        product: ProductCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Создаёт новый товар.
    """
    if product.category_id:
        stmt_category = await db.scalars(
            select(Category).where(Category.id == product.category_id, Category.is_active == True)
        )
        if not stmt_category.first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found')
    db_product = Product(**product.model_dump(), seller_id=current_user.id)
    db.add(db_product)
    await db.commit()
    return db_product


@router.get("/category/{category_id}", response_model=list[ProductSchema])
async def get_products_by_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    smtp_category = await db.scalars(select(Category).where(Category.id == category_id, Category.is_active == True))
    category = smtp_category.first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found or inactive')
    stmt = await db.scalars(select(Product).where(Product.category_id == category_id, Product.is_active == True))
    return stmt.all()


@router.get("/{product_id}", response_model=ProductSchema)
async def get_product(
        product_id: int,
        db: AsyncSession = Depends(get_async_db),
):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    stmt = await db.scalars(select(Product).where(Product.id == product_id, Product.is_active == True))
    product = stmt.first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found or inactive')
    return product


@router.put("/{product_id}", response_model=ProductSchema)
async def update_product(
        product_id: int,
        product_data: ProductCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Обновляет товар по его ID.
    """
    stmt = await db.scalars(select(Product).where(Product.id == product_id, Product.is_active == True))
    product = stmt.first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found or inactive')
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own products")
    if product_data.category_id:
        stmt_category = await db.scalars(
            select(Category).where(Category.id == product_data.category_id, Category.is_active == True)
        )
        category = stmt_category.first()
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found or inactive')
    await db.execute(
        update(Product).where(Product.id == product_id).values(**product_data.model_dump())
    )
    await db.commit()
    return product


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(
        product_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Удаляет товар по его ID.
    """
    stmt = await db.scalars(select(Product).where(Product.id == product_id, Product.is_active == True))
    product = stmt.first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found or inactive')
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own products")
    await db.execute(update(Product).where(Product.id == product_id).values(is_active=False))
    await db.commit()
    return {"status": "success", "message": "Product marked as inactive"}
