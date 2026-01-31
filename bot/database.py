"""
Database module for Telegram Cafe Bot
SQLite database with users, orders, and menu management
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "cafe_bot.db")
DIRECTOR_ID = 7592151419


@contextmanager
def get_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Initialize database with all required tables"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                address TEXT,
                role TEXT DEFAULT 'user' CHECK(role IN ('director', 'admin', 'courier', 'user')),
                balance_bonus INTEGER DEFAULT 0,
                balance_cashback INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                items TEXT NOT NULL,
                total_price INTEGER NOT NULL,
                bonus_used INTEGER DEFAULT 0,
                cashback_used INTEGER DEFAULT 0,
                delivery_address TEXT NOT NULL,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'confirmed', 'cooking', 'ready', 'delivering', 'delivered', 'cancelled')),
                courier_id INTEGER,
                payment_method TEXT DEFAULT 'card',
                payment_status TEXT DEFAULT 'pending' CHECK(payment_status IN ('pending', 'paid', 'failed', 'refunded')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id),
                FOREIGN KEY (courier_id) REFERENCES users(telegram_id)
            )
        """)
        
        # Menu categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                emoji TEXT DEFAULT '🍽',
                sort_order INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Menu items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                price INTEGER NOT NULL,
                image_url TEXT,
                is_available INTEGER DEFAULT 1,
                is_new INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        """)
        
        # Stories/Promotions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                image_url TEXT,
                link TEXT,
                story_type TEXT DEFAULT 'promo' CHECK(story_type IN ('promo', 'new', 'channel')),
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert director on first run
        cursor.execute("""
            INSERT OR IGNORE INTO users (telegram_id, role, balance_bonus)
            VALUES (?, 'director', 0)
        """, (DIRECTOR_ID,))
        
        # Insert default categories if not exist
        default_categories = [
            ('Завтраки', '🍳', 1),
            ('Закуски', '🥗', 2),
            ('Салаты', '🥬', 3),
            ('Основные', '🍝', 4),
            ('Напитки', '🥤', 5),
        ]
        
        for name, emoji, order in default_categories:
            cursor.execute("""
                INSERT OR IGNORE INTO categories (name, emoji, sort_order)
                VALUES (?, ?, ?)
            """, (name, emoji, order))
        
        # Insert sample menu items if table is empty
        cursor.execute("SELECT COUNT(*) FROM menu_items")
        if cursor.fetchone()[0] == 0:
            sample_items = [
                # Завтраки
                (1, 'Яичница с беконом', 'Два яйца, хрустящий бекон, тост', 350, None, 1, 0),
                (1, 'Овсянка с ягодами', 'Овсянка на молоке с сезонными ягодами', 280, None, 1, 1),
                (1, 'Сырники со сметаной', 'Домашние сырники, 4 шт.', 320, None, 1, 0),
                # Закуски
                (2, 'Брускетта с томатами', 'Хрустящий хлеб, томаты, базилик', 290, None, 1, 0),
                (2, 'Куриные наггетсы', '8 штук с соусом на выбор', 340, None, 1, 0),
                (2, 'Сырные палочки', '6 штук с томатным соусом', 310, None, 1, 1),
                # Салаты
                (3, 'Цезарь с курицей', 'Классический рецепт с соусом Цезарь', 420, None, 1, 0),
                (3, 'Греческий салат', 'Свежие овощи, сыр фета, оливки', 380, None, 1, 0),
                (3, 'Салат с тунцом', 'Тунец, микс салата, яйцо', 450, None, 1, 1),
                # Основные
                (4, 'Паста Карбонара', 'Спагетти, бекон, сливочный соус', 480, None, 1, 0),
                (4, 'Стейк из говядины', '250г с овощами гриль', 890, None, 1, 0),
                (4, 'Куриная грудка гриль', 'С картофельным пюре', 520, None, 1, 0),
                (4, 'Борщ украинский', 'С пампушками и сметаной', 350, None, 1, 0),
                # Напитки
                (5, 'Американо', 'Классический эспрессо с водой', 180, None, 1, 0),
                (5, 'Капучино', 'Эспрессо с молочной пенкой', 220, None, 1, 0),
                (5, 'Свежевыжатый сок', 'Апельсин/Яблоко/Морковь', 250, None, 1, 0),
                (5, 'Лимонад домашний', 'С лимоном и мятой', 200, None, 1, 1),
            ]
            
            for item in sample_items:
                cursor.execute("""
                    INSERT INTO menu_items (category_id, name, description, price, image_url, is_available, is_new)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, item)
        
        # Insert sample stories if empty
        cursor.execute("SELECT COUNT(*) FROM stories")
        if cursor.fetchone()[0] == 0:
            sample_stories = [
                ('Новинки недели! 🆕', 'Попробуйте наши новые блюда', None, None, 'new'),
                ('Скидка 20% на завтраки', 'До 12:00 каждый день', None, None, 'promo'),
                ('Наш Telegram канал', 'Подписывайтесь на новости', None, 'https://t.me/your_channel', 'channel'),
            ]
            
            for title, desc, img, link, stype in sample_stories:
                cursor.execute("""
                    INSERT INTO stories (title, description, image_url, link, story_type)
                    VALUES (?, ?, ?, ?, ?)
                """, (title, desc, img, link, stype))


# ============ USER FUNCTIONS ============

def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Get user by telegram_id"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_user(telegram_id: int, username: str = None, first_name: str = None, 
                last_name: str = None, welcome_bonus: int = 500) -> Dict[str, Any]:
    """Create new user with welcome bonus"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (telegram_id, username, first_name, last_name, balance_bonus)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                updated_at = CURRENT_TIMESTAMP
        """, (telegram_id, username, first_name, last_name, welcome_bonus))
    return get_user(telegram_id)


def update_user_address(telegram_id: int, address: str):
    """Update user delivery address"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET address = ?, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        """, (address, telegram_id))


def update_user_phone(telegram_id: int, phone: str):
    """Update user phone"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET phone = ?, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        """, (phone, telegram_id))


def update_user_role(telegram_id: int, role: str) -> bool:
    """Update user role (admin, courier, user)"""
    if role not in ('director', 'admin', 'courier', 'user'):
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        # Cannot change director role
        if telegram_id == DIRECTOR_ID and role != 'director':
            return False
        cursor.execute("""
            UPDATE users SET role = ?, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        """, (role, telegram_id))
        return cursor.rowcount > 0


def get_users_by_role(role: str) -> List[Dict[str, Any]]:
    """Get all users with specific role"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE role = ?", (role,))
        return [dict(row) for row in cursor.fetchall()]


def use_user_bonus(telegram_id: int, amount: int) -> bool:
    """Use bonus from user balance"""
    user = get_user(telegram_id)
    if not user or user['balance_bonus'] < amount:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET balance_bonus = balance_bonus - ?, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        """, (amount, telegram_id))
    return True


def add_user_cashback(telegram_id: int, amount: int):
    """Add cashback to user balance"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET balance_cashback = balance_cashback + ?, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        """, (amount, telegram_id))


# ============ MENU FUNCTIONS ============

def get_categories() -> List[Dict[str, Any]]:
    """Get all active categories"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM categories 
            WHERE is_active = 1 
            ORDER BY sort_order
        """)
        return [dict(row) for row in cursor.fetchall()]


def get_menu_items(category_id: int = None) -> List[Dict[str, Any]]:
    """Get menu items, optionally filtered by category"""
    with get_connection() as conn:
        cursor = conn.cursor()
        if category_id:
            cursor.execute("""
                SELECT m.*, c.name as category_name, c.emoji as category_emoji
                FROM menu_items m
                JOIN categories c ON m.category_id = c.id
                WHERE m.category_id = ? AND m.is_available = 1
                ORDER BY m.sort_order
            """, (category_id,))
        else:
            cursor.execute("""
                SELECT m.*, c.name as category_name, c.emoji as category_emoji
                FROM menu_items m
                JOIN categories c ON m.category_id = c.id
                WHERE m.is_available = 1
                ORDER BY c.sort_order, m.sort_order
            """)
        return [dict(row) for row in cursor.fetchall()]


def get_menu_item(item_id: int) -> Optional[Dict[str, Any]]:
    """Get single menu item by id"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.*, c.name as category_name
            FROM menu_items m
            JOIN categories c ON m.category_id = c.id
            WHERE m.id = ?
        """, (item_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def add_menu_item(category_id: int, name: str, description: str, price: int, 
                  image_url: str = None, is_new: int = 0) -> int:
    """Add new menu item"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO menu_items (category_id, name, description, price, image_url, is_new)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (category_id, name, description, price, image_url, is_new))
        return cursor.lastrowid


def update_menu_item(item_id: int, **kwargs) -> bool:
    """Update menu item fields"""
    allowed_fields = ['name', 'description', 'price', 'image_url', 'is_available', 'is_new', 'category_id']
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not updates:
        return False
    
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [item_id]
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE menu_items SET {set_clause} WHERE id = ?", values)
        return cursor.rowcount > 0


def delete_menu_item(item_id: int) -> bool:
    """Delete menu item"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
        return cursor.rowcount > 0


# ============ STORIES FUNCTIONS ============

def get_stories() -> List[Dict[str, Any]]:
    """Get all active stories"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM stories 
            WHERE is_active = 1 
            ORDER BY sort_order
        """)
        return [dict(row) for row in cursor.fetchall()]


# ============ ORDER FUNCTIONS ============

def create_order(user_id: int, items: List[Dict], total_price: int, 
                 delivery_address: str, bonus_used: int = 0, 
                 cashback_used: int = 0, payment_method: str = 'card') -> int:
    """Create new order"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO orders (user_id, items, total_price, delivery_address, 
                              bonus_used, cashback_used, payment_method)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, json.dumps(items, ensure_ascii=False), total_price, 
              delivery_address, bonus_used, cashback_used, payment_method))
        return cursor.lastrowid


def get_order(order_id: int) -> Optional[Dict[str, Any]]:
    """Get order by id"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.*, u.first_name, u.phone, u.username
            FROM orders o
            JOIN users u ON o.user_id = u.telegram_id
            WHERE o.id = ?
        """, (order_id,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result['items'] = json.loads(result['items'])
            return result
        return None


def get_user_orders(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get user orders"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM orders 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (user_id, limit))
        orders = []
        for row in cursor.fetchall():
            order = dict(row)
            order['items'] = json.loads(order['items'])
            orders.append(order)
        return orders


def get_pending_orders() -> List[Dict[str, Any]]:
    """Get all pending orders for admin"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.*, u.first_name, u.phone, u.username
            FROM orders o
            JOIN users u ON o.user_id = u.telegram_id
            WHERE o.status IN ('pending', 'confirmed', 'cooking', 'ready')
            ORDER BY o.created_at ASC
        """)
        orders = []
        for row in cursor.fetchall():
            order = dict(row)
            order['items'] = json.loads(order['items'])
            orders.append(order)
        return orders


def get_courier_orders(courier_id: int) -> List[Dict[str, Any]]:
    """Get orders assigned to courier"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.*, u.first_name, u.phone, u.username
            FROM orders o
            JOIN users u ON o.user_id = u.telegram_id
            WHERE o.courier_id = ? AND o.status IN ('ready', 'delivering')
            ORDER BY o.created_at ASC
        """, (courier_id,))
        orders = []
        for row in cursor.fetchall():
            order = dict(row)
            order['items'] = json.loads(order['items'])
            orders.append(order)
        return orders


def update_order_status(order_id: int, status: str) -> bool:
    """Update order status"""
    valid_statuses = ['pending', 'confirmed', 'cooking', 'ready', 'delivering', 'delivered', 'cancelled']
    if status not in valid_statuses:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, order_id))
        return cursor.rowcount > 0


def assign_courier(order_id: int, courier_id: int) -> bool:
    """Assign courier to order"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE orders SET courier_id = ?, status = 'ready', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (courier_id, order_id))
        return cursor.rowcount > 0


def update_payment_status(order_id: int, status: str) -> bool:
    """Update payment status"""
    valid_statuses = ['pending', 'paid', 'failed', 'refunded']
    if status not in valid_statuses:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE orders SET payment_status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, order_id))
        return cursor.rowcount > 0


# ============ FULL MENU EXPORT/IMPORT ============

def export_menu_json() -> str:
    """Export full menu as JSON for admin editing"""
    categories = get_categories()
    menu_items = get_menu_items()
    
    menu_data = {
        "categories": categories,
        "items": menu_items
    }
    return json.dumps(menu_data, ensure_ascii=False, indent=2)


def import_menu_json(json_str: str) -> bool:
    """Import menu from JSON"""
    try:
        data = json.loads(json_str)
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Update categories
            if "categories" in data:
                for cat in data["categories"]:
                    cursor.execute("""
                        INSERT OR REPLACE INTO categories (id, name, emoji, sort_order, is_active)
                        VALUES (?, ?, ?, ?, ?)
                    """, (cat.get('id'), cat['name'], cat.get('emoji', '🍽'), 
                          cat.get('sort_order', 0), cat.get('is_active', 1)))
            
            # Update items
            if "items" in data:
                for item in data["items"]:
                    cursor.execute("""
                        INSERT OR REPLACE INTO menu_items 
                        (id, category_id, name, description, price, image_url, is_available, is_new, sort_order)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (item.get('id'), item['category_id'], item['name'], 
                          item.get('description', ''), item['price'], item.get('image_url'),
                          item.get('is_available', 1), item.get('is_new', 0), item.get('sort_order', 0)))
        return True
    except Exception as e:
        print(f"Menu import error: {e}")
        return False


# Initialize database on module load
init_db()
