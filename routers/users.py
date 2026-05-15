from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import models
import schemas
from datetime import datetime



router = APIRouter(prefix="/api/user", tags=["users"])


@router.post("/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user (simple by username)"""
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    new_user = models.User(username=user.username)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=schemas.User)
def login_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Simple login by username"""
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.get("/products", response_model=List[schemas.UserProduct])
def get_user_products(user_id: int, db: Session = Depends(get_db)):
    """Get all products in user's fridge"""
    products = db.query(models.UserProduct).filter(
        models.UserProduct.user_id == user_id
    ).all()
    return products


@router.post("/products", response_model=schemas.UserProduct)
def add_user_product(
        user_id: int,
        product: schemas.UserProductCreate,
        db: Session = Depends(get_db)
):
    """Add product to user's fridge"""
    # Check if user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if product exists
    db_product = db.query(models.Product).filter(
        models.Product.id == product.product_id
    ).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if product already in fridge
    existing = db.query(models.UserProduct).filter(
        models.UserProduct.user_id == user_id,
        models.UserProduct.product_id == product.product_id
    ).first()

    if existing:
        # Update quantity
        existing.quantity += product.quantity
        db.commit()
        db.refresh(existing)
        return existing

    # Create new
    user_product = models.UserProduct(
        user_id=user_id,
        **product.dict()
    )
    db.add(user_product)
    db.commit()
    db.refresh(user_product)
    return user_product


@router.delete("/products/{product_id}")
def delete_user_product(user_id: int, product_id: int, db: Session = Depends(get_db)):
    """Remove product from user's fridge"""
    user_product = db.query(models.UserProduct).filter(
        models.UserProduct.user_id == user_id,
        models.UserProduct.id == product_id
    ).first()

    if not user_product:
        raise HTTPException(status_code=404, detail="Product not found in fridge")

    db.delete(user_product)
    db.commit()
    return {"message": "Product removed from fridge"}

@router.post("/favorites/{recipe_id}")
def add_favorite(user_id: int, recipe_id: int, db: Session = Depends(get_db)):
    """Добавить рецепт в избранное"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    existing = db.query(models.UserFavorite).filter(
        models.UserFavorite.user_id == user_id,
        models.UserFavorite.recipe_id == recipe_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already in favorites")

    favorite = models.UserFavorite(user_id=user_id, recipe_id=recipe_id, created_at=datetime.utcnow())
    db.add(favorite)
    db.commit()
    return {"message": "Recipe added to favorites"}

@router.delete("/favorites/{recipe_id}")
def remove_favorite(user_id: int, recipe_id: int, db: Session = Depends(get_db)):
    """Удалить рецепт из избранного"""
    favorite = db.query(models.UserFavorite).filter(
        models.UserFavorite.user_id == user_id,
        models.UserFavorite.recipe_id == recipe_id
    ).first()
    if not favorite:
        raise HTTPException(status_code=404, detail="Not in favorites")
    db.delete(favorite)
    db.commit()
    return {"message": "Recipe removed from favorites"}

@router.get("/favorites", response_model=List[schemas.Recipe])
def get_favorites(user_id: int, db: Session = Depends(get_db)):
    """Получить список избранных рецептов пользователя"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    favorites = db.query(models.Recipe).join(
        models.UserFavorite, models.UserFavorite.recipe_id == models.Recipe.id
    ).filter(models.UserFavorite.user_id == user_id).all()
    return favorites


