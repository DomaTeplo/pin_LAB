from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from collections import defaultdict

from database import get_db
import models
import schemas

router = APIRouter(prefix="/api/search", tags=["search"])


def get_user_fridge_dict(user_id: int, db: Session) -> Dict[int, Dict]:
    """Get user's fridge products as a dictionary"""
    user_products = db.query(models.UserProduct).filter(
        models.UserProduct.user_id == user_id
    ).all()

    fridge = {}
    for up in user_products:
        fridge[up.product_id] = {
            "quantity": up.quantity,
            "unit": up.unit,
            "product": up.product
        }
    return fridge


def normalize_quantity(quantity: float, from_unit: str, to_unit: str) -> float:
    """Simple quantity normalization (can be expanded)"""
    # This is a simplified version - you might want to add more conversions
    conversion_factors = {
        ("kg", "g"): 1000,
        ("g", "kg"): 0.001,
        ("l", "ml"): 1000,
        ("ml", "l"): 0.001,
    }

    if from_unit == to_unit:
        return quantity

    key = (from_unit, to_unit)
    if key in conversion_factors:
        return quantity * conversion_factors[key]

    # If no conversion available, assume same unit
    return quantity


@router.get("/recipes/by-products", response_model=List[schemas.RecipeSearchResult])
def search_recipes_by_products(
        user_id: int,
        db: Session = Depends(get_db)
):
    """Find recipes based on products in user's fridge"""
    # Get user's fridge
    fridge = get_user_fridge_dict(user_id, db)

    # Get all recipes
    recipes = db.query(models.Recipe).all()
    results = []

    for recipe in recipes:
        # Get recipe ingredients with quantities
        ingredient_data = db.execute(
            models.recipe_ingredients.select().where(
                models.recipe_ingredients.c.recipe_id == recipe.id
            )
        ).fetchall()

        missing_ingredients = []
        all_available = True

        for ing in ingredient_data:
            product_id = ing.product_id
            needed_qty = ing.quantity
            needed_unit = ing.unit

            # Get product details
            product = db.query(models.Product).filter(
                models.Product.id == product_id
            ).first()

            # Check if user has this product
            if product_id in fridge:
                available_qty = fridge[product_id]["quantity"]
                available_unit = fridge[product_id]["unit"]

                # Normalize quantities for comparison
                normalized_needed = needed_qty
                normalized_available = normalize_quantity(
                    available_qty, available_unit, needed_unit
                )

                if normalized_available < normalized_needed:
                    all_available = False
                    missing_ingredients.append(
                        schemas.MissingIngredient(
                            product=product,
                            needed_quantity=needed_qty,
                            needed_unit=needed_unit,
                            available_quantity=normalized_available,
                            missing_quantity=normalized_needed - normalized_available
                        )
                    )
            else:
                all_available = False
                missing_ingredients.append(
                    schemas.MissingIngredient(
                        product=product,
                        needed_quantity=needed_qty,
                        needed_unit=needed_unit,
                        available_quantity=0,
                        missing_quantity=needed_qty
                    )
                )

        results.append(
            schemas.RecipeSearchResult(
                recipe=recipe,
                missing_ingredients=missing_ingredients,
                can_cook=all_available
            )
        )

    # Sort: recipes you can cook first
    results.sort(key=lambda x: (not x.can_cook, len(x.missing_ingredients)))
    return results


@router.get("/recipes/by-products/available", response_model=List[schemas.Recipe])
def get_available_recipes(user_id: int, db: Session = Depends(get_db)):
    """Get only recipes that can be cooked with current fridge products"""
    results = search_recipes_by_products(user_id, db)
    available = [result.recipe for result in results if result.can_cook]
    return available


@router.get("/recipes/{recipe_id}/missing")
def get_missing_ingredients(
        recipe_id: int,
        user_id: int,
        db: Session = Depends(get_db)
):
    """Get missing ingredients for a specific recipe"""
    # Get user's fridge
    fridge = get_user_fridge_dict(user_id, db)

    # Get recipe ingredients
    ingredient_data = db.execute(
        models.recipe_ingredients.select().where(
            models.recipe_ingredients.c.recipe_id == recipe_id
        )
    ).fetchall()

    if not ingredient_data:
        raise HTTPException(status_code=404, detail="Recipe not found")

    missing = []
    for ing in ingredient_data:
        product_id = ing.product_id
        product = db.query(models.Product).filter(
            models.Product.id == product_id
        ).first()

        if product_id in fridge:
            available_qty = fridge[product_id]["quantity"]
            available_unit = fridge[product_id]["unit"]

            normalized_available = normalize_quantity(
                available_qty, available_unit, ing.unit
            )

            if normalized_available < ing.quantity:
                missing.append({
                    "product": product.name,
                    "needed": ing.quantity,
                    "unit": ing.unit,
                    "available": normalized_available,
                    "missing": ing.quantity - normalized_available
                })
        else:
            missing.append({
                "product": product.name,
                "needed": ing.quantity,
                "unit": ing.unit,
                "available": 0,
                "missing": ing.quantity
            })

    return {
        "recipe_id": recipe_id,
        "missing_ingredients": missing,
        "total_missing": len(missing)
    }