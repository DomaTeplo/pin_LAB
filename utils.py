import re
from typing import Tuple, Optional

def parse_quantity_unit(measure: str) -> Tuple[float, str]:
    """Parse a string like '200g', '1 cup', '2 tablespoons' into (quantity, unit)."""
    measure = measure.strip().lower()
    # Try to extract number and unit
    match = re.match(r'^([\d\.]+)\s*([a-z]+)', measure)
    if match:
        qty = float(match.group(1))
        unit = match.group(2)
        # Normalize common units
        unit_map = {
            'g': 'g', 'gram': 'g', 'grams': 'g',
            'kg': 'kg', 'kilogram': 'kg',
            'ml': 'ml', 'milliliter': 'ml', 'milliliters': 'ml',
            'l': 'l', 'liter': 'l', 'liters': 'l',
            'cup': 'cup', 'cups': 'cup',
            'tbsp': 'tbsp', 'tablespoon': 'tbsp', 'tablespoons': 'tbsp',
            'tsp': 'tsp', 'teaspoon': 'tsp', 'teaspoons': 'tsp',
            'piece': 'piece', 'pieces': 'piece',
            'шт': 'piece', 'шт.': 'piece'
        }
        unit = unit_map.get(unit, unit)
        return qty, unit
    # If no unit, assume 'piece'
    return 1.0, 'piece'

def convert_quantity(quantity: float, from_unit: str, to_unit: str) -> float:
    """Convert quantity from one unit to another."""
    if from_unit == to_unit:
        return quantity
    # Simple conversion table (expand as needed)
    conversions = {
        ('kg', 'g'): 1000,
        ('g', 'kg'): 0.001,
        ('l', 'ml'): 1000,
        ('ml', 'l'): 0.001,
        ('cup', 'ml'): 240,
        ('tbsp', 'ml'): 15,
        ('tsp', 'ml'): 5,
    }
    key = (from_unit, to_unit)
    if key in conversions:
        return quantity * conversions[key]
    # Default: no conversion, assume same
    return quantity

def calculate_nutrition(product, quantity: float, unit: str):
    """Calculate nutrition values for a given product and quantity (with unit conversion)."""
    # Convert ingredient quantity to product's base_unit
    qty_in_base = convert_quantity(quantity, unit, product.base_unit)
    factor = qty_in_base / 100.0 if product.base_unit == '100g' else qty_in_base
    return {
        'calories': product.calories * factor,
        'protein': product.protein * factor,
        'fat': product.fat * factor,
        'carbs': product.carbs * factor,
        'cost': product.price * factor
    }