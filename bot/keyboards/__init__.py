"""
Keyboards module for Telegram Cafe Bot
Contains all inline and reply keyboards
"""

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List, Dict, Any
import os


def get_webapp_url() -> str:
    """Get Web App URL from environment"""
    return os.getenv("WEBAPP_URL", "https://your-domain.com/app/")


# ============ USER KEYBOARDS ============

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard with Web App button for regular users"""
    webapp_url = get_webapp_url()
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍽 Открыть меню", web_app=WebAppInfo(url=webapp_url))],
            [KeyboardButton(text="📦 Мои заказы"), KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="📞 Контакты")],
        ],
        resize_keyboard=True,
        is_persistent=True
    )
    return keyboard


def get_director_menu_keyboard() -> ReplyKeyboardMarkup:
    """Menu keyboard for director - staff management only"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👑 Панель директора")],
            [KeyboardButton(text="🛠 Админ-панель"), KeyboardButton(text="📋 Заказы")],
            [KeyboardButton(text="👥 Управление ролями"), KeyboardButton(text="📊 Статистика")],
        ],
        resize_keyboard=True,
        is_persistent=True
    )
    return keyboard


def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """Menu keyboard for admin - order and menu management"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛠 Админ-панель")],
            [KeyboardButton(text="📋 Заказы"), KeyboardButton(text="🍽 Редактировать меню")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="👤 Профиль")],
        ],
        resize_keyboard=True,
        is_persistent=True
    )
    return keyboard


def get_courier_menu_keyboard() -> ReplyKeyboardMarkup:
    """Menu keyboard for courier - delivery management only"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚚 Мои доставки")],
            [KeyboardButton(text="📍 Активные заказы"), KeyboardButton(text="✅ Завершённые")],
            [KeyboardButton(text="👤 Профиль")],
        ],
        resize_keyboard=True,
        is_persistent=True
    )
    return keyboard


def get_keyboard_by_role(role: str) -> ReplyKeyboardMarkup:
    """Get appropriate keyboard based on user role"""
    if role == 'director':
        return get_director_menu_keyboard()
    elif role == 'admin':
        return get_admin_menu_keyboard()
    elif role == 'courier':
        return get_courier_menu_keyboard()
    else:
        return get_main_menu_keyboard()


def get_share_phone_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard to share phone number"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_order_status_keyboard(order_id: int, status: str) -> InlineKeyboardMarkup:
    """Order status inline keyboard for user"""
    builder = InlineKeyboardBuilder()
    
    if status == 'pending':
        builder.button(text="❌ Отменить заказ", callback_data=f"cancel_order:{order_id}")
    
    builder.button(text="🔄 Обновить статус", callback_data=f"refresh_order:{order_id}")
    builder.adjust(1)
    
    return builder.as_markup()


def get_user_orders_keyboard(orders: List[Dict]) -> InlineKeyboardMarkup:
    """List of user orders"""
    builder = InlineKeyboardBuilder()
    
    for order in orders[:5]:  # Show last 5 orders
        status_emoji = {
            'pending': '⏳',
            'confirmed': '✅',
            'cooking': '👨‍🍳',
            'ready': '📦',
            'delivering': '🚚',
            'delivered': '✅',
            'cancelled': '❌'
        }.get(order['status'], '❓')
        
        builder.button(
            text=f"{status_emoji} Заказ #{order['id']} - {order['total_price']}₽",
            callback_data=f"view_order:{order['id']}"
        )
    
    builder.adjust(1)
    return builder.as_markup()


# ============ DIRECTOR KEYBOARDS ============

def get_director_panel_keyboard() -> InlineKeyboardMarkup:
    """Director control panel"""
    builder = InlineKeyboardBuilder()
    
    # Управление персоналом
    builder.button(text="👥 Управление персоналом", callback_data="director:staff_menu")
    # Управление меню
    builder.button(text="🍽 Управление меню", callback_data="director:menu_management")
    # Заказы
    builder.button(text="📋 Все заказы", callback_data="director:all_orders")
    # Статистика
    builder.button(text="📊 Статистика", callback_data="director:stats")
    builder.button(text="🔙 Закрыть", callback_data="director:close")
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_director_staff_keyboard() -> InlineKeyboardMarkup:
    """Director staff management submenu"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="➕ Добавить админа", callback_data="director:add_admin")
    builder.button(text="➕ Добавить курьера", callback_data="director:add_courier")
    builder.button(text="❌ Удалить роль", callback_data="director:remove_role")
    builder.button(text="📋 Список ролей", callback_data="director:list_roles")
    builder.button(text="🔙 Назад", callback_data="director:back")
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_director_menu_management_keyboard() -> InlineKeyboardMarkup:
    """Director menu management submenu"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="➕ Добавить блюдо", callback_data="director:add_dish")
    builder.button(text="✏️ Изменить блюдо", callback_data="director:edit_dish")
    builder.button(text="❌ Удалить блюдо", callback_data="director:delete_dish")
    builder.button(text="📋 Список блюд", callback_data="director:list_dishes")
    builder.button(text="🔙 Назад", callback_data="director:back")
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_dish_list_keyboard(items: List[Dict], action: str = "edit") -> InlineKeyboardMarkup:
    """List dishes for director management"""
    builder = InlineKeyboardBuilder()
    
    for item in items[:15]:
        status = "✅" if item.get('is_available', 1) else "❌"
        builder.button(
            text=f"{status} {item['name']} - {item['price']}₽",
            callback_data=f"director:{action}_dish_id:{item['id']}"
        )
    
    builder.button(text="🔙 Назад", callback_data="director:menu_management")
    builder.adjust(1)
    
    return builder.as_markup()


def get_dish_edit_keyboard(item_id: int) -> InlineKeyboardMarkup:
    """Dish edit options"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📝 Изменить название", callback_data=f"director:edit_name:{item_id}")
    builder.button(text="💰 Изменить цену", callback_data=f"director:edit_price:{item_id}")
    builder.button(text="📄 Изменить описание", callback_data=f"director:edit_desc:{item_id}")
    builder.button(text="🖼 Изменить фото", callback_data=f"director:edit_image:{item_id}")
    builder.button(text="🔄 Вкл/Выкл доступность", callback_data=f"director:toggle_avail:{item_id}")
    builder.button(text="🔙 Назад", callback_data="director:edit_dish")
    
    builder.adjust(2, 2, 2)
    return builder.as_markup()


def get_role_list_keyboard(users: List[Dict], action: str = "remove") -> InlineKeyboardMarkup:
    """List users with roles for management"""
    builder = InlineKeyboardBuilder()
    
    for user in users:
        role_emoji = {
            'director': '👑',
            'admin': '🛠',
            'courier': '🚚',
            'user': '👤'
        }.get(user['role'], '👤')
        
        name = user.get('first_name') or user.get('username') or str(user['telegram_id'])
        
        if action == "remove" and user['role'] != 'director':
            builder.button(
                text=f"{role_emoji} {name} (ID: {user['telegram_id']})",
                callback_data=f"director:confirm_remove:{user['telegram_id']}"
            )
    
    builder.button(text="🔙 Назад", callback_data="director:back")
    builder.adjust(1)
    
    return builder.as_markup()


def get_confirm_role_action_keyboard(user_id: int, action: str) -> InlineKeyboardMarkup:
    """Confirm role action keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="✅ Подтвердить", callback_data=f"director:do_{action}:{user_id}")
    builder.button(text="❌ Отмена", callback_data="director:back")
    
    builder.adjust(2)
    return builder.as_markup()


# ============ ADMIN KEYBOARDS ============

def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Admin control panel"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📋 Активные заказы", callback_data="admin:orders")
    builder.button(text="🍽 Редактировать меню", callback_data="admin:menu")
    builder.button(text="📊 Статистика", callback_data="admin:stats")
    builder.button(text="🔙 Закрыть", callback_data="admin:close")
    
    builder.adjust(2, 2)
    return builder.as_markup()


def get_order_manage_keyboard(order_id: int, status: str, couriers: List[Dict] = None) -> InlineKeyboardMarkup:
    """Order management keyboard for admin"""
    builder = InlineKeyboardBuilder()
    
    status_actions = {
        'pending': [('✅ Подтвердить', 'confirmed'), ('❌ Отменить', 'cancelled')],
        'confirmed': [('👨‍🍳 Готовится', 'cooking'), ('❌ Отменить', 'cancelled')],
        'cooking': [('📦 Готов к доставке', 'ready')],
        'ready': [],
        'delivering': [('✅ Доставлен', 'delivered')],
    }
    
    for text, new_status in status_actions.get(status, []):
        builder.button(text=text, callback_data=f"admin:order_status:{order_id}:{new_status}")
    
    # Add courier assignment for ready orders
    if status == 'cooking' or status == 'ready':
        if couriers:
            for courier in couriers:
                name = courier.get('first_name') or str(courier['telegram_id'])
                builder.button(
                    text=f"🚚 {name}",
                    callback_data=f"admin:assign_courier:{order_id}:{courier['telegram_id']}"
                )
    
    builder.button(text="🔙 Назад", callback_data="admin:orders")
    builder.adjust(2)
    
    return builder.as_markup()


def get_menu_edit_keyboard() -> InlineKeyboardMarkup:
    """Menu editing options"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📥 Экспорт меню (JSON)", callback_data="admin:export_menu")
    builder.button(text="📤 Импорт меню (JSON)", callback_data="admin:import_menu")
    builder.button(text="➕ Добавить блюдо", callback_data="admin:add_item")
    builder.button(text="❌ Удалить блюдо", callback_data="admin:delete_item")
    builder.button(text="🔙 Назад", callback_data="admin:back")
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_category_select_keyboard(categories: List[Dict], action: str = "add") -> InlineKeyboardMarkup:
    """Category selection keyboard"""
    builder = InlineKeyboardBuilder()
    
    for cat in categories:
        builder.button(
            text=f"{cat['emoji']} {cat['name']}",
            callback_data=f"admin:{action}_category:{cat['id']}"
        )
    
    builder.button(text="🔙 Назад", callback_data="admin:menu")
    builder.adjust(2)
    
    return builder.as_markup()


def get_menu_items_keyboard(items: List[Dict], action: str = "delete") -> InlineKeyboardMarkup:
    """Menu items list for editing"""
    builder = InlineKeyboardBuilder()
    
    for item in items[:10]:
        builder.button(
            text=f"{item['name']} - {item['price']}₽",
            callback_data=f"admin:{action}_item:{item['id']}"
        )
    
    builder.button(text="🔙 Назад", callback_data="admin:menu")
    builder.adjust(1)
    
    return builder.as_markup()


# ============ COURIER KEYBOARDS ============

def get_courier_panel_keyboard() -> InlineKeyboardMarkup:
    """Courier control panel"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📦 Мои доставки", callback_data="courier:orders")
    builder.button(text="🔙 Закрыть", callback_data="courier:close")
    
    builder.adjust(1)
    return builder.as_markup()


def get_courier_order_keyboard(order_id: int, status: str) -> InlineKeyboardMarkup:
    """Courier order actions"""
    builder = InlineKeyboardBuilder()
    
    if status == 'ready':
        builder.button(text="📦 Забрал заказ", callback_data=f"courier:pickup:{order_id}")
    elif status == 'delivering':
        builder.button(text="✅ Доставил", callback_data=f"courier:delivered:{order_id}")
    
    builder.button(text="📍 Показать адрес", callback_data=f"courier:address:{order_id}")
    builder.button(text="📞 Позвонить клиенту", callback_data=f"courier:call:{order_id}")
    builder.button(text="🔙 Назад", callback_data="courier:orders")
    
    builder.adjust(1)
    return builder.as_markup()


def get_payment_keyboard(order_id: int, total: int) -> InlineKeyboardMarkup:
    """Payment method selection"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="💳 Оплатить картой", callback_data=f"pay:card:{order_id}")
    builder.button(text="💵 Наличными курьеру", callback_data=f"pay:cash:{order_id}")
    builder.button(text="❌ Отмена", callback_data=f"pay:cancel:{order_id}")
    
    builder.adjust(1)
    return builder.as_markup()
