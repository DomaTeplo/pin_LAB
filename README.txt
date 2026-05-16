1. Название и назначение сервиса

Food Recipe App – Кулинарный помощник

Веб-приложение, которое помогает готовить из того, что есть в холодильнике. Добавляйте продукты, импортируйте рецепты из TheMealDB, получайте расчёт калорий, стоимости и списка недостающих ингредиентов.

Основные возможности

·  Пользователи (регистрация/вход)
·  Продукты с ценой, единицами измерения и КБЖУ
·  Рецепты – ручное создание или импорт из TheMealDB (по названию, категории, ID)
·  Холодильник – учёт продуктов пользователя
·  Поиск рецептов по наличию продуктов + сортировка по калориям / цене
·  Избранное
·  Автозаполнение КБЖУ для новых продуктов через Open Food Facts
·  Расчёт стоимости блюда и недостающих продуктов

2. Архитектура и зависимости

pin_LAB/
    main.py                    
    database.py                
    models.py                  
    schemas.py                 
    utils.py                   
    populate_test_data.py      
    requirements.txt           
    
    routers/
        __init__.py            
        users.py               
        products.py            
        recipes.py             
        search.py              
    
    static/
        index.html             
        script.js              
        style.css              
        recipe_images/                   
    
    food_app.db                

3. Способы запуска сервиса

python main.py

services:
  - type: web
    name: food-recipe
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT

https://pin-lab.onrender.com/
https://github.com/dmitrycheekmarev-boop/pin_LAB
4. API документация
themealdb API- https://www.themealdb.com/docs_api_guide.php
Open Food Facts API- https://api.openfoodfacts.org/

5. Как тестировать и деплоить

· Написаны unit-тесты для ключевых модулей (маршруты, утилиты, база данных).
· Приложение загружено на сервер и доступно по адресу: [ваш URL] (или укажите локальный http://localhost:8000).
· API документация автоматически генерируется Swagger: /docs.

Тестирование на локалке

  pytest test_main.py -v

6. Контакты и поддержка

Telegram

  Лаврентьева Елизавета-@lizalavrenteva
  Лысовский Глеб-@doma_tepllo
  Чекмарев Дмитрий-@zchmnsncemnk

