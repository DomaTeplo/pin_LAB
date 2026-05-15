// Глобальная переменная для хранения текущего пользователя
let currentUserId = null;
let userFavorites = new Set();

// Показать выбранную вкладку (исправлено: передан event)
function showTab(tabName, evt) {
    // Скрыть все вкладки
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Обновить активную кнопку
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    if (evt && evt.target) evt.target.classList.add('active');
    else document.querySelector(`.tab-button[onclick="showTab('${tabName}', event)"]`).classList.add('active');

    if (tabName === 'products') { loadProducts(); loadProductSelect(); }
    else if (tabName === 'recipes') { loadRecipes(); loadProductSelect(); }
    else if (tabName === 'fridge') { loadFridge(); loadProductSelect(); }
    else if (tabName === 'favorites') { loadFavoritesRecipes(); }
}

// ========== ПОЛЬЗОВАТЕЛИ ==========
async function registerUser() {
    const username = document.getElementById('username').value;
    if (!username) return showResult('user-result', 'Введите имя', 'error');
    try {
        const res = await fetch('/api/user/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username }) });
        const data = await res.json();
        if (res.ok) {
            currentUserId = data.id;
            await loadFavorites();
            document.getElementById('current-user').textContent = `${data.username} (ID: ${data.id})`;
            showResult('user-result', 'Регистрация успешна!', 'success');
        } else showResult('user-result', data.detail || 'Ошибка', 'error');
    } catch (error) { showResult('user-result', 'Ошибка соединения', 'error'); }
}

async function loginUser() {
    const username = document.getElementById('username').value;
    if (!username) return showResult('user-result', 'Введите имя', 'error');
    try {
        const res = await fetch('/api/user/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username }) });
        const data = await res.json();
        if (res.ok) {
            currentUserId = data.id;
            await loadFavorites();
            document.getElementById('current-user').textContent = `${data.username} (ID: ${data.id})`;
            showResult('user-result', 'Вход выполнен!', 'success');
        } else showResult('user-result', 'Пользователь не найден', 'error');
    } catch (error) { showResult('user-result', 'Ошибка соединения', 'error'); }
}

function clearUser() {
    currentUserId = null;
    userFavorites.clear();
    document.getElementById('current-user').textContent = 'Не выбран';
}

// ========== ПРОДУКТЫ ==========
async function addProduct() {
    const name = document.getElementById('product-name').value;
    if (!name) return alert('Введите название');
    const category = document.getElementById('product-category').value;
    const price = parseFloat(document.getElementById('product-price').value) || 0;
    const base_unit = document.getElementById('product-base-unit').value || '100g';
    const calories = parseFloat(document.getElementById('product-calories').value) || 0;
    const protein = parseFloat(document.getElementById('product-protein').value) || 0;
    const fat = parseFloat(document.getElementById('product-fat').value) || 0;
    const carbs = parseFloat(document.getElementById('product-carbs').value) || 0;

    try {
        const res = await fetch('/api/products/', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, category, price, base_unit, calories, protein, fat, carbs })
        });
        if (res.ok) {
            alert('Продукт добавлен!');
            document.getElementById('product-name').value = '';
            document.getElementById('product-category').value = '';
            document.getElementById('product-price').value = '';
            document.getElementById('product-base-unit').value = '100g';
            document.getElementById('product-calories').value = '';
            document.getElementById('product-protein').value = '';
            document.getElementById('product-fat').value = '';
            document.getElementById('product-carbs').value = '';
            loadProducts(); loadProductSelect();
        } else { const data = await res.json(); alert(data.detail || 'Ошибка'); }
    } catch (error) { alert('Ошибка соединения'); }
}

async function loadProducts() {
    try {
        const res = await fetch('/api/products/');
        const products = await res.json();
        const list = document.getElementById('products-list');
        list.innerHTML = '';
        products.forEach(p => {
            const div = document.createElement('div');
            div.className = 'product-item';
            div.innerHTML = `
                <div class="product-info">
                    <strong>${p.name}</strong> ${p.category ? `<br>Категория: ${p.category}` : ''}
                    <br>💰 ${p.price} руб/${p.base_unit} | 🔥 ${p.calories} ккал
                </div>
                <div class="product-actions"><button class="delete-btn" onclick="deleteProduct(${p.id})">Удалить</button></div>
            `;
            list.appendChild(div);
        });
    } catch (error) { console.error(error); }
}

async function deleteProduct(id) {
    if (!confirm('Удалить продукт?')) return;
    try {
        await fetch(`/api/products/${id}`, { method: 'DELETE' });
        loadProducts(); loadProductSelect();
    } catch (error) { console.error(error); }
}

async function loadProductSelect() {
    try {
        const res = await fetch('/api/products/');
        const products = await res.json();
        document.querySelectorAll('#fridge-product, .ingredient-product').forEach(select => {
            if (select) {
                select.innerHTML = '<option value="">Выберите продукт</option>';
                products.forEach(p => { select.innerHTML += `<option value="${p.id}">${p.name}</option>`; });
            }
        });
    } catch (error) { console.error(error); }
}

// ========== РЕЦЕПТЫ ==========
function addIngredientField() {
    const list = document.getElementById('ingredients-list');
    const div = document.createElement('div');
    div.className = 'ingredient-row';
    div.innerHTML = `
        <select class="ingredient-product"><option value="">Выберите продукт</option></select>
        <input type="number" placeholder="Количество" class="ingredient-quantity" value="1">
        <input type="text" placeholder="Ед. изм." class="ingredient-unit" value="шт">
        <button class="remove-btn" onclick="this.parentElement.remove()">✖</button>
    `;
    list.appendChild(div);
    loadProductSelect();
}

async function saveRecipe() {
    if (!currentUserId) { alert('Сначала войдите!'); showTab('users', event); return; }
    const name = document.getElementById('recipe-name').value;
    if (!name) return alert('Введите название рецепта');
    const description = document.getElementById('recipe-description').value;
    const instructions = document.getElementById('recipe-instructions').value;
    const image_url = document.getElementById('recipe-image-url').value;

    const ingredients = [];
    document.querySelectorAll('.ingredient-row').forEach(row => {
        const productId = row.querySelector('.ingredient-product').value;
        const quantity = row.querySelector('.ingredient-quantity').value;
        const unit = row.querySelector('.ingredient-unit').value;
        if (productId && quantity) ingredients.push({ product_id: parseInt(productId), quantity: parseFloat(quantity), unit });
    });
    if (!ingredients.length) return alert('Добавьте ингредиенты');

    try {
        const res = await fetch('/api/recipes/', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description, instructions, image_url, ingredients })
        });
        if (res.ok) {
            alert('Рецепт сохранён!');
            document.getElementById('recipe-name').value = '';
            document.getElementById('recipe-description').value = '';
            document.getElementById('recipe-instructions').value = '';
            document.getElementById('recipe-image-url').value = '';
            document.getElementById('ingredients-list').innerHTML = '';
            loadRecipes();
        } else { const data = await res.json(); alert(data.detail || 'Ошибка'); }
    } catch (error) { alert('Ошибка соединения'); }
}

async function loadRecipes() {
    try {
        const response = await fetch('/api/recipes/');
        const recipes = await response.json();
        const list = document.getElementById('recipes-list');
        list.innerHTML = '';
        for (const recipe of recipes) {
            const div = document.createElement('div');
            div.className = 'recipe-item';
            div.innerHTML = `
                <div class="recipe-info">
                    ${recipe.image_url ? `<img src="${recipe.image_url}" style="max-width:100px; border-radius:8px; float:right;">` : ''}
                    <strong>${recipe.name}</strong>
                    ${recipe.description ? `<br>${recipe.description}` : ''}
                </div>
                <div class="recipe-actions">
                    <button class="fav-btn" data-id="${recipe.id}" onclick="toggleFavorite(${recipe.id})">${userFavorites.has(recipe.id) ? '❤️' : '🤍'}</button>
                    <button class="delete-btn" onclick="deleteRecipe(${recipe.id})">Удалить</button>
                </div>
            `;
            list.appendChild(div);
        }
        updateFavoriteButtons();
    } catch (error) {
        console.error('Ошибка загрузки рецептов:', error);
    }
}

async function deleteRecipe(id) {
    if (!confirm('Удалить рецепт?')) return;
    try {
        await fetch(`/api/recipes/${id}`, { method: 'DELETE' });
        if (userFavorites.has(id)) userFavorites.delete(id);
        loadRecipes();
        if (document.getElementById('favorites-tab').classList.contains('active')) loadFavoritesRecipes();
    } catch (error) { console.error(error); }
}

async function importFromMealDB() {
    const mealName = document.getElementById('import-meal-name').value;
    if (!mealName) return alert('Введите название блюда');
    try {
        const res = await fetch(`/api/recipes/import-from-mealdb?meal_name=${encodeURIComponent(mealName)}`, { method: 'POST' });
        if (res.ok) {
            alert('Рецепт импортирован!');
            document.getElementById('import-meal-name').value = '';
            loadRecipes();
        } else { const data = await res.json(); alert(data.detail || 'Ошибка импорта'); }
    } catch (error) { alert('Ошибка соединения'); }
}

// ========== ХОЛОДИЛЬНИК ==========
async function addToFridge() {
    if (!currentUserId) { alert('Сначала войдите!'); showTab('users', event); return; }
    const productId = document.getElementById('fridge-product').value;
    const quantity = document.getElementById('fridge-quantity').value;
    const unit = document.getElementById('fridge-unit').value;
    if (!productId) return alert('Выберите продукт');
    try {
        const res = await fetch(`/api/user/products?user_id=${currentUserId}`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: parseInt(productId), quantity: parseFloat(quantity), unit })
        });
        if (res.ok) { alert('Добавлено!'); loadFridge(); }
        else { const data = await res.json(); alert(data.detail || 'Ошибка'); }
    } catch (error) { alert('Ошибка соединения'); }
}

async function loadFridge() {
    if (!currentUserId) { document.getElementById('fridge-contents').innerHTML = 'Сначала войдите'; return; }
    try {
        const res = await fetch(`/api/user/products?user_id=${currentUserId}`);
        const items = await res.json();
        const list = document.getElementById('fridge-contents');
        list.innerHTML = '';
        if (!items.length) { list.innerHTML = '<p>Холодильник пуст</p>'; return; }
        items.forEach(item => {
            const div = document.createElement('div');
            div.className = 'fridge-item';
            div.innerHTML = `
                <div class="product-info"><strong>${item.product.name}</strong><br>${item.quantity} ${item.unit}</div>
                <div class="product-actions"><button class="delete-btn" onclick="deleteFromFridge(${item.id})">Удалить</button></div>
            `;
            list.appendChild(div);
        });
    } catch (error) { console.error(error); }
}

async function deleteFromFridge(itemId) {
    if (!confirm('Удалить?')) return;
    try {
        await fetch(`/api/user/products/${itemId}?user_id=${currentUserId}`, { method: 'DELETE' });
        loadFridge();
    } catch (error) { console.error(error); }
}

// ========== ПОИСК РЕЦЕПТОВ ==========
async function searchRecipes() {
    if (!currentUserId) { alert('Войдите!'); showTab('users', event); return; }
    const sort_by = document.getElementById('sort-by').value;
    const order = document.getElementById('sort-order').value;
    const url = `/api/search/recipes/by-products?user_id=${currentUserId}&sort_by=${sort_by}&order=${order}`;
    try {
        const res = await fetch(url);
        const results = await res.json();
        const container = document.getElementById('search-results');
        container.innerHTML = '<h3>Результаты:</h3>';
        if (!results.length) { container.innerHTML += '<p>Нет рецептов</p>'; return; }
        for (const r of results) {
            const div = document.createElement('div');
            div.className = `search-result ${r.can_cook ? '' : 'missing'}`;
            div.innerHTML = `
                ${r.recipe.image_url ? `<img src="${r.recipe.image_url}" style="max-width:150px; float:right; border-radius:10px;">` : ''}
                <h4>${r.recipe.name}</h4>
                <p>${r.recipe.description || ''}</p>
                <p>🔥 ${r.total_calories.toFixed(0)} ккал | 💰 ${r.total_cost.toFixed(2)} руб.</p>
                <strong>${r.can_cook ? '✅ Можно приготовить!' : '❌ Не хватает:'}</strong>
                <div class="missing-list"><ul>${r.missing_ingredients.map(m => `<li>${m.product.name}: нужно ${m.needed_quantity} ${m.needed_unit}, есть ${m.available_quantity} (не хватает на ${m.missing_cost.toFixed(2)} руб.)</li>`).join('')}</ul></div>
                <div class="recipe-actions">
                    <button class="fav-btn" data-id="${r.recipe.id}" onclick="toggleFavorite(${r.recipe.id})">${userFavorites.has(r.recipe.id) ? '❤️' : '🤍'}</button>
                </div>
            `;
            container.appendChild(div);
        }
        updateFavoriteButtons();
    } catch (error) { console.error(error); alert('Ошибка поиска'); }
}

// ========== ИМПОРТ РЕЦЕПТОВ ==========
async function loadCategories() {
    try {
        const response = await fetch('/api/recipes/categories');
        const categories = await response.json();
        const select = document.getElementById('category-select');
        if (!select) return;
        select.innerHTML = '<option value="">Выберите категорию</option>';
        categories.forEach(cat => {
            select.innerHTML += `<option value="${cat.strCategory}">${cat.strCategory}</option>`;
        });
    } catch (error) {
        console.error('Ошибка загрузки категорий:', error);
    }
}

async function loadMealsByCategory() {
    const category = document.getElementById('category-select').value;
    if (!category) {
        alert('Пожалуйста, выберите категорию');
        return;
    }
    try {
        const response = await fetch(`/api/recipes/by-category/${category}`);
        const meals = await response.json();
        const container = document.getElementById('meals-list');
        container.innerHTML = '<h4>Найденные рецепты:</h4>';
        if (!meals.length) {
            container.innerHTML += '<p>Рецептов в этой категории не найдено.</p>';
            return;
        }
        meals.forEach(meal => {
            const mealDiv = document.createElement('div');
            mealDiv.className = 'meal-item';
            mealDiv.innerHTML = `
                <img src="${meal.strMealThumb}/preview" alt="${meal.strMeal}" style="width: 50px; border-radius: 8px;">
                <strong>${meal.strMeal}</strong>
                <button onclick="importMealById('${meal.idMeal}')">Импортировать</button>
            `;
            container.appendChild(mealDiv);
        });
    } catch (error) {
        console.error('Ошибка загрузки рецептов:', error);
    }
}

async function importMealById(mealId = null) {
    const id = mealId || document.getElementById('meal-id-input').value;
    if (!id) {
        alert('Введите ID рецепта');
        return;
    }
    try {
        const response = await fetch(`/api/recipes/import-by-id/${id}`, { method: 'POST' });
        if (response.ok) {
            alert('Рецепт успешно импортирован!');
            document.getElementById('meal-id-input').value = '';
            document.getElementById('import-result').innerHTML = '<p style="color:green;">✅ Рецепт импортирован!</p>';
            loadRecipes();
        } else {
            const error = await response.json();
            alert('Ошибка: ' + (error.detail || 'Не удалось импортировать рецепт.'));
        }
    } catch (error) {
        console.error('Ошибка импорта:', error);
        alert('Ошибка соединения с сервером.');
    }
}

// ========== ИЗБРАННОЕ ==========
async function loadFavorites() {
    if (!currentUserId) return;
    const res = await fetch(`/api/user/favorites?user_id=${currentUserId}`);
    const favorites = await res.json();
    userFavorites.clear();
    favorites.forEach(f => userFavorites.add(f.id));
}

async function toggleFavorite(recipeId) {
    if (!currentUserId) { alert('Войдите в систему'); return; }
    const isFav = userFavorites.has(recipeId);
    const method = isFav ? 'DELETE' : 'POST';
    const url = `/api/user/favorites/${recipeId}?user_id=${currentUserId}`;
    const res = await fetch(url, { method });
    if (res.ok) {
        if (isFav) userFavorites.delete(recipeId);
        else userFavorites.add(recipeId);
        updateFavoriteButtons();
        if (document.getElementById('favorites-tab').classList.contains('active')) loadFavoritesRecipes();
    } else {
        const data = await res.json();
        alert(data.detail || 'Ошибка');
    }
}

function updateFavoriteButtons() {
    document.querySelectorAll('.fav-btn').forEach(btn => {
        const recipeId = parseInt(btn.dataset.id);
        if (userFavorites.has(recipeId)) {
            btn.textContent = '❤️';
            btn.style.color = 'red';
        } else {
            btn.textContent = '🤍';
            btn.style.color = 'gray';
        }
    });
}

async function loadFavoritesRecipes() {
    if (!currentUserId) { alert('Войдите'); return; }
    const res = await fetch(`/api/user/favorites?user_id=${currentUserId}`);
    const recipes = await res.json();
    const container = document.getElementById('favorites-list');
    container.innerHTML = '';
    if (recipes.length === 0) {
        container.innerHTML = '<p>Нет избранных рецептов</p>';
        return;
    }
    recipes.forEach(recipe => {
        const div = document.createElement('div');
        div.className = 'recipe-item';
        div.innerHTML = `
            <div class="recipe-info">
                ${recipe.image_url ? `<img src="${recipe.image_url}" style="max-width:100px; border-radius:8px;">` : ''}
                <strong>${recipe.name}</strong>
                <br>${recipe.description || ''}
            </div>
            <div class="recipe-actions">
                <button class="fav-btn" data-id="${recipe.id}" onclick="toggleFavorite(${recipe.id})">❤️ Удалить из избранного</button>
                <button onclick="deleteRecipe(${recipe.id})">🗑️ Удалить рецепт</button>
            </div>
        `;
        container.appendChild(div);
    });
    updateFavoriteButtons();
}

function showResult(elementId, message, type) {
    const el = document.getElementById(elementId);
    el.textContent = message;
    el.className = `result ${type}`;
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    loadProducts();
    loadProductSelect();
    loadCategories();
});