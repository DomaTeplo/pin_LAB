from main import SessionLocal
import models
from routers import recipes


def create_test_data():
    db = SessionLocal()

    # Create products
    products = [
        {"name": "Картошка", "category": "Овощи"},
        {"name": "Морковь", "category": "Овощи"},
        {"name": "Лук", "category": "Овощи"},
        {"name": "Мясо", "category": "Мясо"},
        {"name": "Яйца", "category": "Яйца"},
        {"name": "Молоко", "category": "Молочные"},
        {"name": "Мука", "category": "Бакалея"},
    ]

    for prod in products:
        existing = db.query(models.Product).filter(
            models.Product.name == prod["name"]
        ).first()
        if not existing:
            db.add(models.Product(**prod))

    db.commit()

    # Create users
    users = ["Анна", "Петр", "Мария"]
    for user in users:
        existing = db.query(models.User).filter(
            models.User.username == user
        ).first()
        if not existing:
            db.add(models.User(username=user))

    db.commit()
    print("Test data created!")


if __name__ == "__main__":
    create_test_data()
