from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models
import schemas
from utils import convert_quantity, calculate_nutrition

router = APIRouter(prefix="/api/search", tags=["search"])

def get_user_fridge_dict(user_id: int, db: Session):
    user_products = db.query(models.UserProduct).filter(models.UserProduct.user_id == user_id).all()
    fridge = {}
    for up in user_products:
        fridge[up.product_id] = {
            "quantity": up.quantity,
            "unit": up.unit,
            "product": up.product
        }
    return fridge

def compute_recipe_totals(recipe_id: int, db: Session):
    """Return (total_calories, total_cost) for a recipe."""
    ingredient_data = db.execute(
        models.recipe_ingredients.select().where(models.recipe_ingredients.c.recipe_id == recipe_id)
    ).fetchall()
    total_cal = 0.0
    total_cost = 0.0
    for ing in ingredient_data:
        product = db.query(models.Product).filter(models.Product.id == ing.product_id).first()
        if product:
            nutr = calculate_nutrition(product, ing.quantity, ing.unit)
            total_cal += nutr['calories']
            total_cost += nutr['cost']
    return total_cal, total_cost

@router.get("/recipes/by-products", response_model=List[schemas.RecipeSearchResult])
def search_recipes_by_products(
    user_id: int,
    sort_by: Optional[str] = Query(None, pattern="^(calories|price|none)$"),
    order: Optional[str] = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    fridge = get_user_fridge_dict(user_id, db)
    recipes = db.query(models.Recipe).all()
    results = []

    for recipe in recipes:
        ingredient_data = db.execute(
            models.recipe_ingredients.select().where(models.recipe_ingredients.c.recipe_id == recipe.id)
        ).fetchall()
        missing = []
        all_available = True
        total_missing_cost = 0.0

        for ing in ingredient_data:
            product = db.query(models.Product).filter(models.Product.id == ing.product_id).first()
            if not product:
                continue
            needed_qty = ing.quantity
            needed_unit = ing.unit
            if ing.product_id in fridge:
                available_qty = fridge[ing.product_id]["quantity"]
                available_unit = fridge[ing.product_id]["unit"]
                conv_available = convert_quantity(available_qty, available_unit, needed_unit)
                if conv_available < needed_qty:
                    all_available = False
                    missing_qty = needed_qty - conv_available
                    # cost of missing part
                    nutr_missing = calculate_nutrition(product, missing_qty, needed_unit)
                    missing_cost = nutr_missing['cost']
                    total_missing_cost += missing_cost
                    missing.append(schemas.MissingIngredient(
                        product=product,
                        needed_quantity=needed_qty,
                        needed_unit=needed_unit,
                        available_quantity=conv_available,
                        missing_quantity=missing_qty,
                        missing_cost=missing_cost
                    ))
            else:
                all_available = False
                nutr_missing = calculate_nutrition(product, needed_qty, needed_unit)
                missing_cost = nutr_missing['cost']
                total_missing_cost += missing_cost
                missing.append(schemas.MissingIngredient(
                    product=product,
                    needed_quantity=needed_qty,
                    needed_unit=needed_unit,
                    available_quantity=0,
                    missing_quantity=needed_qty,
                    missing_cost=missing_cost
                ))

        total_cal, total_cost = compute_recipe_totals(recipe.id, db)
        results.append(schemas.RecipeSearchResult(
            recipe=recipe,
            missing_ingredients=missing,
            can_cook=all_available,
            total_calories=total_cal,
            total_cost=total_cost,
            missing_cost=total_missing_cost
        ))

    # Sorting
    if sort_by == "calories":
        results.sort(key=lambda x: x.total_calories, reverse=(order == "desc"))
    elif sort_by == "price":
        results.sort(key=lambda x: x.total_cost, reverse=(order == "desc"))
    else:
        # default: can_cook first, then fewest missing
        results.sort(key=lambda x: (not x.can_cook, len(x.missing_ingredients)))

    return results