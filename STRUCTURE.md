# Структура проекта

```
@lilitDemo_01_Bot/
├── bot/                          # Telegram бот
│   ├── main.py                  # Точка входа бота
│   ├── database.py              # Работа с SQLite БД
│   ├── init_sample_data.py     # Скрипт для заполнения примерными данными
│   ├── handlers/                # Обработчики команд
│   │   ├── __init__.py
│   │   ├── user.py             # Обработчики для пользователей (/start)
│   │   ├── director.py         # Обработчики для директора (/director)
│   │   ├── admin.py            # Обработчики для админов (/admin)
│   │   └── courier.py          # Обработчики для курьеров (/courier)
│   └── keyboards/              # Клавиатуры бота
│       └── __init__.py
├── webapp/                      # Web App (Mini App)
│   ├── api.py                  # FastAPI backend
│   └── static/
│       └── index.html          # Frontend Web App
├── .env                        # Конфигурация (создать вручную)
├── env.example.txt             # Пример конфигурации
├── bot.db                      # SQLite база данных (создается автоматически)
├── requirements.txt            # Python зависимости
└── README.md                   # Документация
```

## Ключевые файлы

### bot/main.py
Главный файл запуска бота. Инициализирует БД, регистрирует роутеры и запускает polling.

### bot/database.py
Все функции работы с базой данных:
- `init_db()` - создание таблиц и инициализация директора
- `get_user()` - получение пользователя
- `create_user()` - создание пользователя
- `update_user_role()` - изменение роли
- `get_menu()` - получение меню
- `create_order()` - создание заказа
- И другие...

### bot/handlers/
- **user.py** - команда `/start`, приветствие, бонусы
- **director.py** - команда `/director`, управление ролями (ID: 7592151419)
- **admin.py** - команда `/admin`, управление меню и заказами
- **courier.py** - команда `/courier`, управление доставкой

### webapp/api.py
FastAPI backend для Web App:
- `/api/menu` - получение меню
- `/api/stories` - получение Stories
- `/api/order` - создание заказа
- `/api/user/{id}` - информация о пользователе

### webapp/static/index.html
Frontend Web App с:
- Поле ввода адреса
- Лента Stories
- Категории меню
- Лента товаров
- Корзина

## База данных

Таблицы:
- `users` - пользователи (telegram_id, role, balance_bonus, balance_cashback)
- `menu` - меню (id, category, name, description, price, image_url, available)
- `orders` - заказы (id, user_id, items, total_price, address, status, courier_id)
- `stories` - Stories (id, title, image_url, link_url, type, active)

## Роли

- **director** (ID: 7592151419) - полный доступ
- **admin** - управление меню и заказами
- **courier** - доставка заказов
- **user** - обычные пользователи
