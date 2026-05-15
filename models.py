from sqlalchemy import Column, Integer, String, Float, ForeignKey, Table, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base



# Association table for Recipe - Ingredient many-to-many
recipe_ingredients = Table(
    'recipe_ingredients',
    Base.metadata,
    Column('recipe_id', Integer, ForeignKey('recipes.id')),
    Column('product_id', Integer, ForeignKey('products.id')),
    Column('quantity', Float),
    Column('unit', String)
)



class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    fridge_products = relationship("UserProduct", back_populates="user")
    favorite_recipes = relationship("UserFavorite", back_populates="user", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    category = Column(String, nullable=True)
    # New fields
    price = Column(Float, default=0.0)          # price per base_unit
    base_unit = Column(String, default="100g")  # kg, g, piece, 100g, etc.
    calories = Column(Float, default=0.0)       # per base_unit
    protein = Column(Float, default=0.0)
    fat = Column(Float, default=0.0)
    carbs = Column(Float, default=0.0)

    recipes = relationship("Recipe", secondary=recipe_ingredients, back_populates="ingredients")
    user_products = relationship("UserProduct", back_populates="product")


class Recipe(Base):
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    instructions = Column(String)
    image_url = Column(String, nullable=True)   # New field for recipe photo

    ingredients = relationship("Product", secondary=recipe_ingredients, back_populates="recipes")


class UserProduct(Base):
    __tablename__ = "user_products"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float, default=1.0)
    unit = Column(String, default="шт")

    user = relationship("User", back_populates="fridge_products")
    product = relationship("Product", back_populates="user_products")


class UserFavorite(Base):
    __tablename__ = "user_favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    recipe_id = Column(Integer, ForeignKey("recipes.id"))
    created_at = Column(DateTime, default=func.now())  # исправлено

    user = relationship("User", back_populates="favorite_recipes")
    recipe = relationship("Recipe")