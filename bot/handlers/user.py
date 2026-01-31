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

from ..database import (
    get_user, create_user, update_user_address, update_user_phone,
    get_user_orders, get_order, update_order_status
)
from ..keyboards import (
    get_main_menu_keyboard, get_share_phone_keyboard,
    get_order_status_keyboard, get_user_orders_keyboard
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
    """Handle /start command - register user and show welcome"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Check if user exists
    existing_user = get_user(user_id)
    
    if existing_user:
        # Returning user
        await message.answer(
            f"👋 С возвращением, {first_name}!\n\n"
            f"💰 Ваш баланс:\n"
            f"🎁 Бонусы: {existing_user['balance_bonus']}₽\n"
            f"💵 Кешбэк: {existing_user['balance_cashback']}₽\n\n"
            f"Нажмите «Открыть меню» чтобы сделать заказ!",
            reply_markup=get_main_menu_keyboard()
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
    try:
        data = json.loads(message.web_app_data.data)
        
        if data.get('action') == 'order_created':
            order_id = data.get('order_id')
            total = data.get('total')
            
            await message.answer(
                f"✅ <b>Заказ #{order_id} создан!</b>\n\n"
                f"💰 Сумма: {total}₽\n\n"
                f"Ожидайте подтверждения от оператора.",
                parse_mode="HTML"
            )
        
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
    await message.answer(
        f"✅ Номер телефона сохранён: {phone}",
        reply_markup=get_main_menu_keyboard()
    )
