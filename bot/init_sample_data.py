"""
Скрипт для инициализации примерных данных меню
Запустите один раз после первого запуска бота для заполнения меню
"""
import asyncio
from bot.database import init_db, add_menu_item, get_menu


async def init_sample_menu():
    """Инициализация примерного меню"""
    await init_db()
    
    # Примерные данные меню
    sample_menu = [
        # Завтраки
        {"category": "Завтраки", "name": "Омлет с ветчиной", "description": "Нежный омлет с ветчиной и сыром", "price": 350.0},
        {"category": "Завтраки", "name": "Блины с медом", "description": "Тонкие блины с медом и маслом", "price": 280.0},
        {"category": "Завтраки", "name": "Яичница с беконом", "description": "Яичница глазунья с хрустящим беконом", "price": 320.0},
        
        # Закусы
        {"category": "Закусы", "name": "Сырная тарелка", "description": "Ассорти из сыров с орехами и медом", "price": 450.0},
        {"category": "Закусы", "name": "Брускетта с томатами", "description": "Хрустящий хлеб с томатами и базиликом", "price": 280.0},
        {"category": "Закусы", "name": "Куриные крылышки", "description": "Острые куриные крылышки в соусе", "price": 380.0},
        
        # Салаты
        {"category": "Салаты", "name": "Цезарь", "description": "Классический салат Цезарь с курицей", "price": 420.0},
        {"category": "Салаты", "name": "Греческий", "description": "Свежие овощи с сыром фета и оливками", "price": 380.0},
        {"category": "Салаты", "name": "Оливье", "description": "Традиционный салат Оливье", "price": 320.0},
        
        # Основные
        {"category": "Основные", "name": "Стейк из говядины", "description": "Сочный стейк средней прожарки", "price": 850.0},
        {"category": "Основные", "name": "Паста Карбонара", "description": "Итальянская паста с беконом и сыром", "price": 480.0},
        {"category": "Основные", "name": "Бургер классический", "description": "Сочная котлета с овощами и соусом", "price": 450.0},
        {"category": "Основные", "name": "Рыба на гриле", "description": "Свежая рыба с овощами", "price": 650.0},
        
        # Напитки
        {"category": "Напитки", "name": "Кофе эспрессо", "description": "Крепкий эспрессо", "price": 150.0},
        {"category": "Напитки", "name": "Капучино", "description": "Кофе с молочной пенкой", "price": 200.0},
        {"category": "Напитки", "name": "Свежевыжатый сок", "description": "Апельсиновый или яблочный", "price": 250.0},
        {"category": "Напитки", "name": "Лимонад", "description": "Освежающий лимонад", "price": 180.0},
    ]
    
    # Проверяем, есть ли уже меню
    existing_menu = await get_menu()
    if existing_menu:
        print(f"В меню уже есть {len(existing_menu)} позиций. Пропускаем добавление примерных данных.")
        return
    
    # Добавляем примерные данные
    for item in sample_menu:
        await add_menu_item(
            category=item["category"],
            name=item["name"],
            description=item["description"],
            price=item["price"]
        )
    
    print(f"✅ Добавлено {len(sample_menu)} позиций в меню")


if __name__ == "__main__":
    asyncio.run(init_sample_menu())
