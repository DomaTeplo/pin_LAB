from pydantic import BaseModel
from typing import List, Optional

# Product schemas
class ProductBase(BaseModel):
    name: str
    category: Optional[str] = None
    price: float = 0.0
    base_unit: str = "100g"
    calories: float = 0.0
    protein: float = 0.0
    fat: float = 0.0
    carbs: float = 0.0

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    class Config:
        from_attributes = True

# User schemas
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    pass



class User(UserBase):
    id: int
    fridge_products: List["UserProduct"] = []
    favorite_recipes: List["Recipe"] = []   # новое поле
    class Config:
        from_attributes = True

# Recipe schemas
class RecipeIngredient(BaseModel):
    product_id: int
    quantity: float
    unit: str

class RecipeBase(BaseModel):
    name: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    image_url: Optional[str] = None

class RecipeCreate(RecipeBase):
    ingredients: List[RecipeIngredient]

class Recipe(RecipeBase):
    id: int
    ingredients: List[Product] = []
    class Config:
        from_attributes = True

# UserProduct schemas
class UserProductBase(BaseModel):
    product_id: int
    quantity: float = 1.0
    unit: str = "шт"

class UserProductCreate(UserProductBase):
    pass

class UserProduct(UserProductBase):
    id: int
    user_id: int
    product: Product
    class Config:
        from_attributes = True   

# Search schemas
class MissingIngredient(BaseModel):
    product: Product
    needed_quantity: float
    needed_unit: str
    available_quantity: float
    missing_quantity: float
    missing_cost: float = 0.0

class RecipeSearchResult(BaseModel):
    recipe: Recipe
    missing_ingredients: List[MissingIngredient]
    can_cook: bool
    total_calories: float = 0.0
    total_cost: float = 0.0
    missing_cost: float = 0.0