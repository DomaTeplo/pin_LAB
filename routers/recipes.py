import os
import requests
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from database import get_db
import models
import schemas
from utils import parse_quantity_unit
import httpx
import asyncio
from functools import lru_cache

# Кэш для результатов Open Food Facts (чтобы не запрашивать одно и то же много раз)
@lru_cache(maxsize=200)
def get_nutrition_from_openfoodfacts(product_name: str):
    """Запрашивает Open Food Facts и возвращает dict с nutrition (на 100г)"""
    try:
        # Поиск продукта по названию
        url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={product_name}&search_simple=1&action=process&json=1&page_size=1"
        response = httpx.get(url, timeout=5)
        data = response.json()
        products = data.get('products', [])
        if not products:
            return None
        p = products[0]
        nutriments = p.get('nutriments', {})
        # Извлекаем значения на 100 г
        calories = nutriments.get('energy-kcal_100g', 0)
        protein = nutriments.get('proteins_100g', 0)
        fat = nutriments.get('fat_100g', 0)
        carbs = nutriments.get('carbohydrates_100g', 0)
        # Базовая единица — 100g
        base_unit = "100g"
        # Цену из Open Food Facts не берём (обычно нет), оставляем 0
        return {
            "calories": calories,
            "protein": protein,
            "fat": fat,
            "carbs": carbs,
            "base_unit": base_unit
        }
    except Exception as e:
        print(f"Ошибка получения данных для {product_name}: {e}")
        return None


# ---------- СЛОВАРЬ СООТВЕТСТВИЙ АНГЛИЙСКИХ НАЗВАНИЙ РУССКИМ ----------
PRODUCT_MAPPING = {
    # Масла
    "vegetable oil": "Масло подсолнечное",
    "sunflower oil": "Масло подсолнечное",
    "olive oil": "Масло оливковое",   # Добавлено
    "butter": "Масло сливочное",
    # Мясо и птица
    "chicken breast": "Куриное филе",
    "chicken": "Куриное филе",
    "beef": "Говядина",
    "pork": "Свинина",
    "lamb": "Баранина",
    "salmon": "Лосось",
    "tuna": "Тунец",
    # Овощи
    "potato": "Картофель",
    "carrot": "Морковь",
    "onion": "Лук репчатый",
    "garlic": "Чеснок",
    "tomato": "Помидоры",
    "cucumber": "Огурцы",
    "lettuce": "Салат",
    # Молочные и яйца
    "egg": "Яйца",
    "milk": "Молоко 3.2%",
    "butter": "Масло сливочное",
    "cheese": "Сыр твердый",
    "cottage cheese": "Творог 5%",
    "cream": "Сливки",
    "yogurt": "Йогурт",
    # Бакалея
    "flour": "Мука пшеничная",
    "plain flour": "Мука пшеничная",
    "sugar": "Сахар",
    "salt": "Соль",
    "rice": "Рис",
    "buckwheat": "Гречка",
    "pasta": "Макароны",
    "bread": "Хлеб",
    # Масла
    "vegetable oil": "Масло подсолнечное",
    "sunflower oil": "Масло подсолнечное",
    "olive oil": "Масло оливковое",
    # Фрукты
    "banana": "Банан",
    "apple": "Яблоко",
    "lemon": "Лимон",
    # Соусы
    "mayonnaise": "Майонез",
    "ketchup": "Кетчуп",
    # Прочее
    "garlic clove": "Чеснок",
    "bay leaf": "Лавровый лист",
    "honey": "Мёд",
    "soy sauce": "Соевый соус",
    "curry powder": "Карри",
    "garam masala": "Гарам масала",
    "breadcrumbs": "Панировочные сухари",
}
def find_or_create_product(ingredient_name: str, db: Session):
    ing_lower = ingredient_name.lower().strip()
    
    # 1. Прямое отображение через словарь
    if ing_lower in PRODUCT_MAPPING:
        product = db.query(models.Product).filter(
            models.Product.name == PRODUCT_MAPPING[ing_lower]
        ).first()
        if product:
            return product
    
    # 2. Поиск по частичному совпадению (например, "olive" найдёт "Масло оливковое")
    for eng, rus in PRODUCT_MAPPING.items():
        if eng in ing_lower or ing_lower in eng:
            product = db.query(models.Product).filter(models.Product.name == rus).first()
            if product:
                return product
    
    # 3. Поиск по словам из названия (например, "oil" -> "Масло подсолнечное")
    words = ing_lower.split()
    for word in words:
        if len(word) > 3:
            product = db.query(models.Product).filter(
                models.Product.name.ilike(f"%{word}%")
            ).first()
            if product:
                return product
    
    # 4. Если ничего не найдено, создаём продукт-заглушку
    product = models.Product(
        name=ingredient_name,
        category="Imported",
        price=0.0,
        base_unit="100g",
        calories=0,
        protein=0,
        fat=0,
        carbs=0
    )
    # Пытаемся обогатить данными из Open Food Facts
    nutrition = get_nutrition_from_openfoodfacts(ingredient_name)
    if nutrition:
        product.calories = nutrition['calories']
        product.protein = nutrition['protein']
        product.fat = nutrition['fat']
        product.carbs = nutrition['carbs']
        product.base_unit = nutrition['base_unit']
        print(f"Обогащён продукт {ingredient_name}: {nutrition['calories']} ккал")
    db.add(product)
    db.flush()
    return product

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

# Папка для сохранения изображений рецептов
RECIPE_IMAGES_DIR = "static/recipe_images"
os.makedirs(RECIPE_IMAGES_DIR, exist_ok=True)

def download_recipe_image(image_url: str) -> str:
    """Скачивает изображение и возвращает локальный путь"""
    if not image_url:
        return ""
    try:
        ext = image_url.split('.')[-1].split('?')[0]
        if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            ext = 'jpg'
        filename = f"{uuid.uuid4().hex}.{ext}"
        local_path = os.path.join(RECIPE_IMAGES_DIR, filename)
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        with open(local_path, 'wb') as f:
            f.write(response.content)
        return f"/static/recipe_images/{filename}"
    except Exception as e:
        print(f"Ошибка загрузки изображения: {e}")
        return ""

# ---------- СПЕЦИАЛЬНЫЕ МАРШРУТЫ (без параметров или с фиксированными именами) ----------
@router.get("/categories")
def get_categories() -> List[Dict[str, Any]]:
    url = "https://www.themealdb.com/api/json/v1/1/categories.php"
    response = requests.get(url)
    data = response.json()
    return data.get("categories", [])

@router.get("/by-category/{category_name}")
def get_meals_by_category(category_name: str) -> List[Dict[str, Any]]:
    url = f"https://www.themealdb.com/api/json/v1/1/filter.php?c={category_name}"
    response = requests.get(url)
    data = response.json()
    return data.get("meals", [])

@router.post("/import-by-id/{meal_id}")
def import_recipe_by_id(meal_id: str, db: Session = Depends(get_db)):
    url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}"
    response = requests.get(url)
    data = response.json()
    meals = data.get("meals")
    if not meals:
        raise HTTPException(status_code=404, detail="Рецепт с таким ID не найден.")
    meal = meals[0]
    name = meal["strMeal"]
    instructions = meal["strInstructions"]
    external_image_url = meal["strMealThumb"]
    description = meal.get("strCategory", "") + " - " + meal.get("strArea", "")
    ingredients = []
    for i in range(1, 21):
        ing = meal.get(f"strIngredient{i}")
        measure = meal.get(f"strMeasure{i}")
        if ing and ing.strip():
            qty, unit = parse_quantity_unit(measure or "1 piece")
            product = find_or_create_product(ing, db)
            ingredients.append({
                "product_id": product.id,
                "quantity": qty,
                "unit": unit
            })
    recipe_create = schemas.RecipeCreate(
        name=name,
        description=description,
        instructions=instructions,
        image_url=external_image_url,
        ingredients=ingredients
    )
    return create_recipe(recipe_create, db)

@router.post("/import-from-mealdb")
def import_from_mealdb(meal_name: str, db: Session = Depends(get_db)):
    url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={meal_name}"
    resp = requests.get(url)
    data = resp.json()
    meals = data.get("meals")
    if not meals:
        raise HTTPException(status_code=404, detail="No recipe found")
    meal = meals[0]
    name = meal["strMeal"]
    instructions = meal["strInstructions"]
    external_image_url = meal["strMealThumb"]
    description = meal.get("strCategory", "") + " - " + meal.get("strArea", "")
    ingredients = []
    for i in range(1, 21):
        ing = meal.get(f"strIngredient{i}")
        measure = meal.get(f"strMeasure{i}")
        if ing and ing.strip():
            qty, unit = parse_quantity_unit(measure or "1 piece")
            product = find_or_create_product(ing, db)
            ingredients.append({
                "product_id": product.id,
                "quantity": qty,
                "unit": unit
            })
    recipe_create = schemas.RecipeCreate(
        name=name,
        description=description,
        instructions=instructions,
        image_url=external_image_url,
        ingredients=ingredients
    )
    return create_recipe(recipe_create, db)

# ---------- ОСНОВНЫЕ CRUD ----------
@router.post("/", response_model=schemas.Recipe)
def create_recipe(recipe: schemas.RecipeCreate, db: Session = Depends(get_db)):
    image_url_final = recipe.image_url or ""
    if image_url_final and not image_url_final.startswith("/static/"):
        downloaded_path = download_recipe_image(image_url_final)
        if downloaded_path:
            image_url_final = downloaded_path
    db_recipe = models.Recipe(
        name=recipe.name,
        description=recipe.description,
        instructions=recipe.instructions,
        image_url=image_url_final
    )
    db.add(db_recipe)
    db.flush()
    for ing in recipe.ingredients:
        product = db.query(models.Product).filter(models.Product.id == ing.product_id).first()
        if not product:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Product {ing.product_id} not found")
        stmt = models.recipe_ingredients.insert().values(
            recipe_id=db_recipe.id,
            product_id=ing.product_id,
            quantity=ing.quantity,
            unit=ing.unit
        )
        db.execute(stmt)
    db.commit()
    db.refresh(db_recipe)
    return db_recipe

@router.get("/", response_model=List[schemas.Recipe])
def get_recipes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    recipes = db.query(models.Recipe).offset(skip).limit(limit).all()
    return recipes

# ---------- ДИНАМИЧЕСКИЕ МАРШРУТЫ (с параметром пути) ----------
@router.get("/{recipe_id}", response_model=schemas.Recipe)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe

@router.delete("/{recipe_id}")
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    db.execute(models.recipe_ingredients.delete().where(
        models.recipe_ingredients.c.recipe_id == recipe_id
    ))
    if recipe.image_url and recipe.image_url.startswith("/static/recipe_images/"):
        file_path = recipe.image_url.lstrip("/")
        full_path = os.path.join(os.getcwd(), file_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception as e:
                print(f"Ошибка удаления файла: {e}")
    db.delete(recipe)
    db.commit()
    return {"message": "Recipe deleted"}