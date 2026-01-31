"""
User handlers for Telegram Cafe Bot
Handles all regular user interactions
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import (
    get_user, create_user, update_user_address, update_user_phone,
    get_user_orders, get_order, update_order_status
)
from keyboards import (
    get_main_menu_keyboard, get_share_phone_keyboard,
    get_order_status_keyboard, get_user_orders_keyboard,
    get_keyboard_by_role, get_admin_panel_keyboard,
    get_director_panel_keyboard, get_courier_panel_keyboard
)

router = Router()


class UserStates(StatesGroup):
    """User conversation states"""
    waiting_phone = State()
    waiting_address = State()


# Status translations
STATUS_NAMES = {
    'pending': '⏳ Ожидает подтверждения',
    'confirmed': '✅ Подтверждён',
    'cooking': '👨‍🍳 Готовится',
    'ready': '📦 Готов к доставке',
    'delivering': '🚚 Доставляется',
    'delivered': '✅ Доставлен',
    'cancelled': '❌ Отменён'
}


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command - register user and show welcome based on role"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Check if user exists
    existing_user = get_user(user_id)
    
    if existing_user:
        role = existing_user.get('role', 'user')
        keyboard = get_keyboard_by_role(role)
        
        # Different welcome messages based on role
        if role == 'director':
            await message.answer(
                f"👑 Добро пожаловать, Директор {first_name}!\n\n"
                f"Используйте панель управления для:\n"
                f"• Управления персоналом\n"
                f"• Просмотра заказов\n"
                f"• Редактирования меню\n"
                f"• Просмотра статистики",
                reply_markup=keyboard
            )
        elif role == 'admin':
            await message.answer(
                f"🛠 Добро пожаловать, Администратор {first_name}!\n\n"
                f"Ваши возможности:\n"
                f"• Управление заказами\n"
                f"• Редактирование меню\n"
                f"• Назначение курьеров\n"
                f"• Просмотр статистики",
                reply_markup=keyboard
            )
        elif role == 'courier':
            await message.answer(
                f"🚚 Добро пожаловать, Курьер {first_name}!\n\n"
                f"Ваши возможности:\n"
                f"• Просмотр назначенных доставок\n"
                f"• Отметка о получении заказа\n"
                f"• Отметка о доставке",
                reply_markup=keyboard
            )
        else:
            # Regular user
            await message.answer(
                f"👋 С возвращением, {first_name}!\n\n"
                f"💰 Ваш баланс:\n"
                f"🎁 Бонусы: {existing_user['balance_bonus']}₽\n"
                f"💵 Кешбэк: {existing_user['balance_cashback']}₽\n\n"
                f"Нажмите «Открыть меню» чтобы сделать заказ!",
                reply_markup=keyboard
            )
    else:
        # New user - give welcome bonus
        create_user(user_id, username, first_name, last_name, welcome_bonus=500)
        
        await message.answer(
            f"🎉 Добро пожаловать в наше кафе, {first_name}!\n\n"
            f"🎁 Вам начислено 500 приветственных бонусов!\n\n"
            f"ℹ️ Бонусами можно оплатить до 50% заказа.\n"
            f"Минимальная сумма заказа для использования бонусов: 500₽\n\n"
            f"Нажмите «Открыть меню» чтобы сделать первый заказ!",
            reply_markup=get_main_menu_keyboard()
        )


@router.message(F.text == "👤 Профиль")
async def profile_handler(message: Message):
    """Show user profile"""
    user = get_user(message.from_user.id)
    
    if not user:
        await message.answer("Пожалуйста, начните с команды /start")
        return
    
    role_names = {
        'director': '👑 Директор',
        'admin': '🛠 Администратор',
        'courier': '🚚 Курьер',
        'user': '👤 Пользователь'
    }
    
    profile_text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"📛 Имя: {user.get('first_name', 'Не указано')}\n"
        f"🆔 ID: {user['telegram_id']}\n"
        f"👤 Роль: {role_names.get(user['role'], 'Пользователь')}\n"
        f"📱 Телефон: {user.get('phone') or 'Не указан'}\n"
        f"📍 Адрес: {user.get('address') or 'Не указан'}\n\n"
        f"💰 <b>Баланс:</b>\n"
        f"🎁 Бонусы: {user['balance_bonus']}₽\n"
        f"💵 Кешбэк: {user['balance_cashback']}₽"
    )
    
    await message.answer(profile_text, parse_mode="HTML")


@router.message(F.text == "💰 Баланс")
async def balance_handler(message: Message):
    """Show user balance"""
    user = get_user(message.from_user.id)
    
    if not user:
        await message.answer("Пожалуйста, начните с команды /start")
        return
    
    await message.answer(
        f"💰 <b>Ваш баланс</b>\n\n"
        f"🎁 Бонусы: <b>{user['balance_bonus']}₽</b>\n"
        f"<i>Можно использовать до 50% от суммы заказа (мин. 500₽)</i>\n\n"
        f"💵 Кешбэк: <b>{user['balance_cashback']}₽</b>\n"
        f"<i>Начисляется 5% с каждого заказа</i>",
        parse_mode="HTML"
    )


@router.message(F.text == "📦 Мои заказы")
async def my_orders_handler(message: Message):
    """Show user orders"""
    user_id = message.from_user.id
    orders = get_user_orders(user_id)
    
    if not orders:
        await message.answer(
            "📦 У вас пока нет заказов.\n"
            "Нажмите «Открыть меню» чтобы сделать первый заказ!"
        )
        return
    
    await message.answer(
        "📦 <b>Ваши заказы:</b>\n\n"
        "Выберите заказ для просмотра деталей:",
        parse_mode="HTML",
        reply_markup=get_user_orders_keyboard(orders)
    )


@router.callback_query(F.data.startswith("view_order:"))
async def view_order_callback(callback: CallbackQuery):
    """View order details"""
    order_id = int(callback.data.split(":")[1])
    order = get_order(order_id)
    
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    # Format items
    items_text = "\n".join([
        f"  • {item['name']} × {item['quantity']} = {item['price'] * item['quantity']}₽"
        for item in order['items']
    ])
    
    order_text = (
        f"📦 <b>Заказ #{order['id']}</b>\n\n"
        f"📍 Адрес: {order['delivery_address']}\n"
        f"📊 Статус: {STATUS_NAMES.get(order['status'], order['status'])}\n\n"
        f"🍽 <b>Состав заказа:</b>\n{items_text}\n\n"
        f"💰 <b>Итого: {order['total_price']}₽</b>"
    )
    
    if order['bonus_used'] > 0:
        order_text += f"\n🎁 Использовано бонусов: {order['bonus_used']}₽"
    
    await callback.message.edit_text(
        order_text,
        parse_mode="HTML",
        reply_markup=get_order_status_keyboard(order_id, order['status'])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("refresh_order:"))
async def refresh_order_callback(callback: CallbackQuery):
    """Refresh order status"""
    order_id = int(callback.data.split(":")[1])
    order = get_order(order_id)
    
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    # Format items
    items_text = "\n".join([
        f"  • {item['name']} × {item['quantity']} = {item['price'] * item['quantity']}₽"
        for item in order['items']
    ])
    
    order_text = (
        f"📦 <b>Заказ #{order['id']}</b>\n\n"
        f"📍 Адрес: {order['delivery_address']}\n"
        f"📊 Статус: {STATUS_NAMES.get(order['status'], order['status'])}\n\n"
        f"🍽 <b>Состав заказа:</b>\n{items_text}\n\n"
        f"💰 <b>Итого: {order['total_price']}₽</b>"
    )
    
    await callback.message.edit_text(
        order_text,
        parse_mode="HTML",
        reply_markup=get_order_status_keyboard(order_id, order['status'])
    )
    await callback.answer("Статус обновлён ✅")


@router.callback_query(F.data.startswith("cancel_order:"))
async def cancel_order_callback(callback: CallbackQuery):
    """Cancel order"""
    order_id = int(callback.data.split(":")[1])
    order = get_order(order_id)
    
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    if order['status'] != 'pending':
        await callback.answer("Заказ уже нельзя отменить", show_alert=True)
        return
    
    update_order_status(order_id, 'cancelled')
    
    await callback.message.edit_text(
        f"❌ Заказ #{order_id} отменён.\n\n"
        f"Если были использованы бонусы, они будут возвращены на баланс.",
        parse_mode="HTML"
    )
    await callback.answer("Заказ отменён")


@router.message(F.text == "📞 Контакты")
async def contacts_handler(message: Message):
    """Show contacts"""
    await message.answer(
        "📞 <b>Контакты</b>\n\n"
        "📍 Адрес: г. Москва, ул. Примерная, д. 1\n"
        "📱 Телефон: +7 (999) 123-45-67\n"
        "⏰ Время работы: 09:00 - 23:00\n\n"
        "📲 Наш канал: @your_channel\n"
        "💬 Поддержка: @your_support",
        parse_mode="HTML"
    )


@router.message(F.web_app_data)
async def web_app_data_handler(message: Message):
    """Handle data from Web App"""
    from database import get_users_by_role, get_order as get_order_details
    
    try:
        data = json.loads(message.web_app_data.data)
        
        if data.get('action') == 'order_created':
            order_id = data.get('order_id')
            total = data.get('total')
            
            # Уведомление клиенту
            await message.answer(
                f"✅ <b>Заказ #{order_id} создан!</b>\n\n"
                f"💰 Сумма: {total}₽\n\n"
                f"⏳ Ожидайте подтверждения от оператора.\n"
                f"Мы уведомим вас о каждом изменении статуса!",
                parse_mode="HTML"
            )
            
            # Уведомление всем админам и директору о новом заказе
            order_details = get_order_details(order_id)
            admins = get_users_by_role('admin')
            directors = get_users_by_role('director')
            staff = admins + directors
            
            if order_details:
                items_text = "\n".join([
                    f"  • {item['name']} × {item['quantity']}"
                    for item in order_details['items']
                ])
                
                notification_text = (
                    f"🆕 <b>Новый заказ #{order_id}!</b>\n\n"
                    f"👤 Клиент: {message.from_user.first_name}\n"
                    f"📍 Адрес: {order_details['delivery_address']}\n\n"
                    f"🍽 Состав:\n{items_text}\n\n"
                    f"💰 Сумма: {total}₽\n\n"
                    f"Используйте /admin для управления заказами."
                )
                
                bot = message.bot
                for admin in staff:
                    try:
                        await bot.send_message(
                            admin['telegram_id'],
                            notification_text,
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        print(f"Failed to notify admin {admin['telegram_id']}: {e}")
        
        elif data.get('action') == 'address_updated':
            address = data.get('address')
            update_user_address(message.from_user.id, address)
            await message.answer(f"📍 Адрес доставки обновлён:\n{address}")
            
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"Web App data error: {e}")


@router.message(F.contact)
async def contact_handler(message: Message, state: FSMContext):
    """Handle shared contact"""
    phone = message.contact.phone_number
    update_user_phone(message.from_user.id, phone)
    
    await state.clear()
    user = get_user(message.from_user.id)
    role = user.get('role', 'user') if user else 'user'
    await message.answer(
        f"✅ Номер телефона сохранён: {phone}",
        reply_markup=get_keyboard_by_role(role)
    )


# ============ STAFF BUTTON HANDLERS ============

@router.message(F.text == "👑 Панель директора")
async def director_panel_button(message: Message):
    """Director panel button handler"""
    from database import DIRECTOR_ID
    if message.from_user.id != DIRECTOR_ID:
        await message.answer("⛔ Доступ запрещён")
        return
    
    await message.answer(
        "👑 <b>Панель директора</b>\n\n"
        f"🆔 Ваш ID: <code>{message.from_user.id}</code>\n\n"
        "Управление ролями персонала:",
        parse_mode="HTML",
        reply_markup=get_director_panel_keyboard()
    )


@router.message(F.text == "👥 Управление ролями")
async def manage_roles_button(message: Message):
    """Manage roles button - redirect to director panel"""
    from database import DIRECTOR_ID
    if message.from_user.id != DIRECTOR_ID:
        await message.answer("⛔ Доступ запрещён")
        return
    
    await message.answer(
        "👑 <b>Панель директора</b>\n\n"
        "Управление ролями персонала:",
        parse_mode="HTML",
        reply_markup=get_director_panel_keyboard()
    )


@router.message(F.text == "🛠 Админ-панель")
async def admin_panel_button(message: Message):
    """Admin panel button handler"""
    user = get_user(message.from_user.id)
    if not user or user['role'] not in ('admin', 'director'):
        await message.answer("⛔ Доступ запрещён")
        return
    
    await message.answer(
        "🛠 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_admin_panel_keyboard()
    )


@router.message(F.text == "📋 Заказы")
async def orders_button(message: Message):
    """Orders button for admin/director"""
    from database import get_pending_orders
    
    user = get_user(message.from_user.id)
    if not user or user['role'] not in ('admin', 'director'):
        await message.answer("⛔ Доступ запрещён")
        return
    
    orders = get_pending_orders()
    
    if not orders:
        await message.answer(
            "📋 <b>Активные заказы</b>\n\n"
            "Нет активных заказов.",
            parse_mode="HTML"
        )
        return
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    STATUS_EMOJI = {
        'pending': '⏳',
        'confirmed': '✅',
        'cooking': '👨‍🍳',
        'ready': '📦',
        'delivering': '🚚',
    }
    
    orders_text = "📋 <b>Активные заказы:</b>\n\n"
    
    for order in orders[:10]:
        emoji = STATUS_EMOJI.get(order['status'], '❓')
        orders_text += (
            f"{emoji} #{order['id']} | {order.get('first_name', 'Клиент')} | {order['total_price']}₽\n"
        )
        builder.button(
            text=f"#{order['id']} - {order['total_price']}₽",
            callback_data=f"admin:view_order:{order['id']}"
        )
    
    builder.adjust(1)
    
    await message.answer(
        orders_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.message(F.text == "🍽 Редактировать меню")
async def edit_menu_button(message: Message):
    """Edit menu button for admin"""
    from keyboards import get_menu_edit_keyboard
    
    user = get_user(message.from_user.id)
    if not user or user['role'] not in ('admin', 'director'):
        await message.answer("⛔ Доступ запрещён")
        return
    
    await message.answer(
        "🍽 <b>Редактирование меню</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_menu_edit_keyboard()
    )


@router.message(F.text == "📊 Статистика")
async def stats_button(message: Message):
    """Statistics button for admin/director"""
    from database import get_connection
    
    user = get_user(message.from_user.id)
    if not user or user['role'] not in ('admin', 'director'):
        await message.answer("⛔ Доступ запрещён")
        return
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE date(created_at) = date('now')")
        today_orders = cursor.fetchone()[0]
        
        cursor.execute("SELECT COALESCE(SUM(total_price), 0) FROM orders WHERE status = 'delivered'")
        total_revenue = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status NOT IN ('delivered', 'cancelled')")
        active_orders = cursor.fetchone()[0]
    
    await message.answer(
        "📊 <b>Статистика</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📦 Всего заказов: {total_orders}\n"
        f"📦 Заказов сегодня: {today_orders}\n"
        f"⏳ Активных заказов: {active_orders}\n"
        f"💰 Общая выручка: {total_revenue}₽",
        parse_mode="HTML"
    )


@router.message(F.text == "🚚 Мои доставки")
async def courier_deliveries_button(message: Message):
    """Courier deliveries button"""
    from database import get_courier_orders
    
    user = get_user(message.from_user.id)
    if not user or user['role'] not in ('courier', 'admin', 'director'):
        await message.answer("⛔ Доступ запрещён")
        return
    
    orders = get_courier_orders(message.from_user.id)
    
    if not orders:
        await message.answer(
            "🚚 <b>Ваши доставки</b>\n\n"
            "Нет активных доставок.\n"
            "Ожидайте назначения от администратора.",
            parse_mode="HTML"
        )
        return
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    orders_text = "🚚 <b>Ваши доставки:</b>\n\n"
    
    for order in orders:
        status_emoji = '📦' if order['status'] == 'ready' else '🚚'
        orders_text += (
            f"{status_emoji} #{order['id']} | {order['delivery_address'][:30]}...\n"
            f"    💰 {order['total_price']}₽\n\n"
        )
        builder.button(
            text=f"{status_emoji} #{order['id']} - {order['total_price']}₽",
            callback_data=f"courier:view:{order['id']}"
        )
    
    builder.adjust(1)
    
    await message.answer(
        orders_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.message(F.text == "📍 Активные заказы")
async def courier_active_orders_button(message: Message):
    """Redirect to courier deliveries"""
    await courier_deliveries_button(message)


@router.message(F.text == "✅ Завершённые")
async def courier_completed_button(message: Message):
    """Show completed deliveries for courier"""
    from database import get_connection
    
    user = get_user(message.from_user.id)
    if not user or user['role'] not in ('courier', 'admin', 'director'):
        await message.answer("⛔ Доступ запрещён")
        return
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.*, u.first_name
            FROM orders o
            JOIN users u ON o.user_id = u.telegram_id
            WHERE o.courier_id = ? AND o.status = 'delivered'
            ORDER BY o.updated_at DESC
            LIMIT 10
        """, (message.from_user.id,))
        orders = [dict(row) for row in cursor.fetchall()]
    
    if not orders:
        await message.answer(
            "✅ <b>Завершённые доставки</b>\n\n"
            "Пока нет завершённых доставок.",
            parse_mode="HTML"
        )
        return
    
    orders_text = "✅ <b>Завершённые доставки:</b>\n\n"
    
    for order in orders:
        orders_text += (
            f"✅ #{order['id']} | {order.get('first_name', 'Клиент')} | {order['total_price']}₽\n"
        )
    
    await message.answer(orders_text, parse_mode="HTML")
