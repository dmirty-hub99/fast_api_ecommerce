from sqlalchemy import Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Category(Base):
    __tablename__ = 'categories'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    products: Mapped[list['Product']] = relationship('Product', back_populates='category')
    parent_id: Mapped[int] = mapped_column(ForeignKey('categories.id'), nullable=True)
    parent: Mapped['Category'] = relationship(
        'Category', back_populates='children', remote_side='Category.id'
    )
    children: Mapped[list['Category']] = relationship('Category', back_populates='parent')
