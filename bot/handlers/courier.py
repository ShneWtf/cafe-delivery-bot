"""
Courier handlers for Telegram Cafe Bot
Handles courier delivery management
"""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import os

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import (
    get_user, get_courier_orders, get_order, update_order_status, DIRECTOR_ID
)
from keyboards import (
    get_courier_panel_keyboard, get_courier_order_keyboard
)

router = Router()


# Status translations
STATUS_NAMES = {
    'pending': '⏳ Ожидает',
    'confirmed': '✅ Подтверждён',
    'cooking': '👨‍🍳 Готовится',
    'ready': '📦 Готов к доставке',
    'delivering': '🚚 Доставляется',
    'delivered': '✅ Доставлен',
    'cancelled': '❌ Отменён'
}


def is_courier_or_higher(user_id: int) -> bool:
    """Check if user is courier, admin or director"""
    if user_id == DIRECTOR_ID:
        return True
    user = get_user(user_id)
    return user and user['role'] in ('courier', 'admin', 'director')


@router.message(Command("courier"))
async def cmd_courier(message: Message):
    """Handle /courier command"""
    if not is_courier_or_higher(message.from_user.id):
        await message.answer("⛔ Эта команда доступна только курьерам")
        return
    
    orders = get_courier_orders(message.from_user.id)
    
    if not orders:
        await message.answer(
            "🚚 <b>Панель курьера</b>\n\n"
            "У вас пока нет назначенных доставок.\n"
            "Ожидайте новые заказы от администратора.",
            parse_mode="HTML"
        )
        return
    
    orders_text = "🚚 <b>Ваши доставки:</b>\n\n"
    
    for order in orders:
        orders_text += (
            f"📦 <b>Заказ #{order['id']}</b>\n"
            f"📍 {order['delivery_address']}\n"
            f"📊 {STATUS_NAMES.get(order['status'], order['status'])}\n"
            f"💰 {order['total_price']}₽\n\n"
        )
    
    await message.answer(
        orders_text,
        parse_mode="HTML",
        reply_markup=get_courier_panel_keyboard()
    )


@router.callback_query(F.data == "courier:orders")
async def courier_orders_callback(callback: CallbackQuery):
    """Show courier orders"""
    if not is_courier_or_higher(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    orders = get_courier_orders(callback.from_user.id)
    
    if not orders:
        await callback.message.edit_text(
            "🚚 <b>Ваши доставки</b>\n\n"
            "Нет активных доставок.",
            parse_mode="HTML",
            reply_markup=get_courier_panel_keyboard()
        )
        await callback.answer()
        return
    
    # Create inline keyboard with orders
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    for order in orders:
        status_emoji = '📦' if order['status'] == 'ready' else '🚚'
        builder.button(
            text=f"{status_emoji} #{order['id']} - {order['total_price']}₽",
            callback_data=f"courier:view:{order['id']}"
        )
    
    builder.button(text="🔙 Закрыть", callback_data="courier:close")
    builder.adjust(1)
    
    orders_text = "🚚 <b>Ваши доставки:</b>\n\n"
    
    for order in orders:
        orders_text += (
            f"📦 Заказ #{order['id']} | {STATUS_NAMES.get(order['status'], order['status'])}\n"
            f"📍 {order['delivery_address'][:40]}...\n\n"
        )
    
    await callback.message.edit_text(
        orders_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("courier:view:"))
async def courier_view_order_callback(callback: CallbackQuery):
    """View order details for courier"""
    if not is_courier_or_higher(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split(":")[2])
    order = get_order(order_id)
    
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    # Format items
    items_text = "\n".join([
        f"  • {item['name']} × {item['quantity']}"
        for item in order['items']
    ])
    
    order_text = (
        f"📦 <b>Заказ #{order['id']}</b>\n\n"
        f"👤 Клиент: {order.get('first_name', 'Неизвестно')}\n"
        f"📱 Телефон: {order.get('phone', 'Не указан')}\n"
        f"📍 Адрес: {order['delivery_address']}\n\n"
        f"📊 Статус: {STATUS_NAMES.get(order['status'], order['status'])}\n\n"
        f"🍽 <b>Состав:</b>\n{items_text}\n\n"
        f"💰 <b>Сумма: {order['total_price']}₽</b>\n"
        f"💳 Оплата: {'✅ Оплачен' if order['payment_status'] == 'paid' else '💵 При получении'}"
    )
    
    await callback.message.edit_text(
        order_text,
        parse_mode="HTML",
        reply_markup=get_courier_order_keyboard(order_id, order['status'])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("courier:pickup:"))
async def courier_pickup_callback(callback: CallbackQuery, bot: Bot):
    """Mark order as picked up (delivering)"""
    if not is_courier_or_higher(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split(":")[2])
    order = get_order(order_id)
    
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    update_order_status(order_id, 'delivering')
    
    # Notify customer
    try:
        await bot.send_message(
            order['user_id'],
            f"🚚 <b>Заказ #{order_id} в пути!</b>\n\n"
            f"Курьер забрал ваш заказ и направляется к вам.\n"
            f"📍 Адрес доставки: {order['delivery_address']}",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Failed to notify customer: {e}")
    
    await callback.answer("✅ Заказ отмечен как забран")
    
    # Refresh order view
    order = get_order(order_id)
    
    items_text = "\n".join([
        f"  • {item['name']} × {item['quantity']}"
        for item in order['items']
    ])
    
    order_text = (
        f"📦 <b>Заказ #{order['id']}</b>\n\n"
        f"👤 Клиент: {order.get('first_name', 'Неизвестно')}\n"
        f"📱 Телефон: {order.get('phone', 'Не указан')}\n"
        f"📍 Адрес: {order['delivery_address']}\n\n"
        f"📊 Статус: {STATUS_NAMES.get(order['status'], order['status'])}\n\n"
        f"🍽 <b>Состав:</b>\n{items_text}\n\n"
        f"💰 <b>Сумма: {order['total_price']}₽</b>"
    )
    
    await callback.message.edit_text(
        order_text,
        parse_mode="HTML",
        reply_markup=get_courier_order_keyboard(order_id, order['status'])
    )


@router.callback_query(F.data.startswith("courier:delivered:"))
async def courier_delivered_callback(callback: CallbackQuery, bot: Bot):
    """Mark order as delivered"""
    if not is_courier_or_higher(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split(":")[2])
    order = get_order(order_id)
    
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    update_order_status(order_id, 'delivered')
    
    # Add cashback to user (5% of order)
    from database import add_user_cashback
    cashback = int(order['total_price'] * 0.05)
    add_user_cashback(order['user_id'], cashback)
    
    # Notify customer
    try:
        await bot.send_message(
            order['user_id'],
            f"✅ <b>Заказ #{order_id} доставлен!</b>\n\n"
            f"Спасибо за заказ! 🙏\n\n"
            f"💰 Вам начислено {cashback}₽ кешбэка!\n\n"
            f"Будем рады видеть вас снова! 🍽",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Failed to notify customer: {e}")
    
    await callback.answer("✅ Заказ доставлен! Отличная работа!")
    
    # Go back to orders list
    await courier_orders_callback(callback)


@router.callback_query(F.data.startswith("courier:address:"))
async def courier_address_callback(callback: CallbackQuery):
    """Show full address"""
    if not is_courier_or_higher(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split(":")[2])
    order = get_order(order_id)
    
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    await callback.answer(
        f"📍 {order['delivery_address']}",
        show_alert=True
    )


@router.callback_query(F.data.startswith("courier:call:"))
async def courier_call_callback(callback: CallbackQuery):
    """Show customer phone"""
    if not is_courier_or_higher(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split(":")[2])
    order = get_order(order_id)
    
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    phone = order.get('phone', 'Не указан')
    await callback.answer(
        f"📞 {phone}",
        show_alert=True
    )


@router.callback_query(F.data == "courier:close")
async def courier_close_callback(callback: CallbackQuery):
    """Close courier panel"""
    await callback.message.delete()
    await callback.answer()
