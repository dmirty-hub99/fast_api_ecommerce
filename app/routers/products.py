from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.auth import get_current_user, get_current_seller
from app.db_depends import get_async_db
from app.models import Product, Category, User as UserModel
from app.schemas import Product as ProductSchema, ProductCreate, ProductList

# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get("/", response_model=ProductList)
async def get_all_products(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        search: str | None = Query(None, min_length=1, description='Поиск по названию товара'),
        category_id: int | None = Query(
            None, description='ID категории для фильтрации'
        ),
        min_price: float | None = Query(
            None, ge=0, description='Минимальная цена товара'
        ),
        max_price: float | None = Query(
            None, ge=0, description='Максимальная цена товара'
        ),
        in_stock: bool | None = Query(
            None, description="true — только товары в наличии, false — только без остатка"),
        seller_id: int | None = Query(
            None, description="ID продавца для фильтрации"),
        db: AsyncSession = Depends(get_async_db),
):
    """
    Возвращает список всех товаров.
    """
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price не может быть больше max_price",
        )
    filters = [Product.is_active == True]
    if search is not None:
        search_value = search.strip()
        if search_value:
            filters.append(func.lower(Product.name).like(f'%{search_value.lower()}%'))
    if category_id:
        filters.append(Product.category_id == category_id)
    if min_price is not None:
        filters.append(Product.price >= min_price)
    if max_price is not None:
        filters.append(Product.price <= max_price)
    if in_stock is not None:
        filters.append(Product.stock > 0 if in_stock else Product.stock == 0)
    if seller_id is not None:
        filters.append(Product.seller_id == seller_id)

    total_stmt = select(func.count()).select_from(Product).where(*filters)
    total = await db.scalar(total_stmt) or 0

    products_stmt = (
        select(Product)
        .where(*filters)
        .order_by(Product.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.scalars((products_stmt))).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


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
