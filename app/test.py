from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_async_db
from app.models.promocode import PromoCodeModel


router = APIRouter()

@router.delete('/{promocode_id}')
async def delete_promocode(promocode_id: int, db: AsyncSession = Depends(get_async_db)):
    promocodes = await db.scalars(
        select(PromoCodeModel).where(PromoCodeModel.id == promocode_id, PromoCodeModel.is_active == True)
    )
    promocode = promocodes.first()
    if not promocode:
        raise HTTPException(status_code=404, detail='Promocode not found')
    promocode.is_active = False
    await db.commit()
    return {"status": "success", "message": "Promocode marked as inactive"}