"""
Admin handlers for Telegram Cafe Bot
Handles admin panel, order management, menu editing
"""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
import json

from ..database import (
    get_user, get_users_by_role, get_pending_orders, get_order,
    update_order_status, assign_courier, get_categories, get_menu_items,
    add_menu_item, delete_menu_item, export_menu_json, import_menu_json
)
from ..keyboards import (
    get_admin_panel_keyboard, get_order_manage_keyboard,
    get_menu_edit_keyboard, get_category_select_keyboard,
    get_menu_items_keyboard
)

router = Router()

DIRECTOR_ID = int(os.getenv("DIRECTOR_ID", "7592151419"))


class AdminStates(StatesGroup):
    """Admin conversation states"""
    waiting_menu_json = State()
    waiting_item_name = State()
    waiting_item_description = State()
    waiting_item_price = State()
    adding_item_category = State()


def is_admin_or_director(user_id: int) -> bool:
    """Check if user is admin or director"""
    if user_id == DIRECTOR_ID:
        return True
    user = get_user(user_id)
    return user and user['role'] in ('admin', 'director')


# Status translations
STATUS_NAMES = {
    'pending': '⏳ Ожидает',
    'confirmed': '✅ Подтверждён',
    'cooking': '👨‍🍳 Готовится',
    'ready': '📦 Готов',
    'delivering': '🚚 Доставляется',
    'delivered': '✅ Доставлен',
    'cancelled': '❌ Отменён'
}


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Handle /admin command"""
    if not is_admin_or_director(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к админ-панели")
        return
    
    await message.answer(
        "🛠 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_admin_panel_keyboard()
    )


@router.callback_query(F.data == "admin:orders")
async def admin_orders_callback(callback: CallbackQuery):
    """Show pending orders"""
    if not is_admin_or_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    orders = get_pending_orders()
    
    if not orders:
        await callback.message.edit_text(
            "📋 <b>Активные заказы</b>\n\n"
            "Нет активных заказов.",
            parse_mode="HTML",
            reply_markup=get_admin_panel_keyboard()
        )
        await callback.answer()
        return
    
    orders_text = "📋 <b>Активные заказы:</b>\n\n"
    
    for order in orders[:10]:
        items_count = len(order['items'])
        orders_text += (
            f"#{order['id']} | {STATUS_NAMES.get(order['status'], order['status'])}\n"
            f"👤 {order.get('first_name', 'Неизвестно')} | {items_count} поз. | {order['total_price']}₽\n"
            f"📍 {order['delivery_address'][:40]}...\n\n"
        )
    
    # Create keyboard with order buttons
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    for order in orders[:5]:
        builder.button(
            text=f"#{order['id']} - {order['total_price']}₽",
            callback_data=f"admin:view_order:{order['id']}"
        )
    
    builder.button(text="🔙 Назад", callback_data="admin:back")
    builder.adjust(1)
    
    await callback.message.edit_text(
        orders_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:view_order:"))
async def admin_view_order_callback(callback: CallbackQuery):
    """View single order details for admin"""
    if not is_admin_or_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split(":")[2])
    order = get_order(order_id)
    
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    # Get available couriers
    couriers = get_users_by_role('courier')
    
    # Format items
    items_text = "\n".join([
        f"  • {item['name']} × {item['quantity']} = {item['price'] * item['quantity']}₽"
        for item in order['items']
    ])
    
    order_text = (
        f"📦 <b>Заказ #{order['id']}</b>\n\n"
        f"👤 Клиент: {order.get('first_name', 'Неизвестно')}\n"
        f"📱 Телефон: {order.get('phone', 'Не указан')}\n"
        f"📍 Адрес: {order['delivery_address']}\n\n"
        f"📊 Статус: {STATUS_NAMES.get(order['status'], order['status'])}\n"
        f"💳 Оплата: {'✅ Оплачен' if order['payment_status'] == 'paid' else '⏳ Ожидает'}\n\n"
        f"🍽 <b>Состав:</b>\n{items_text}\n\n"
        f"💰 <b>Итого: {order['total_price']}₽</b>"
    )
    
    if order['courier_id']:
        courier = get_user(order['courier_id'])
        if courier:
            order_text += f"\n🚚 Курьер: {courier.get('first_name', courier['telegram_id'])}"
    
    await callback.message.edit_text(
        order_text,
        parse_mode="HTML",
        reply_markup=get_order_manage_keyboard(order_id, order['status'], couriers)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:order_status:"))
async def admin_change_status_callback(callback: CallbackQuery, bot: Bot):
    """Change order status"""
    if not is_admin_or_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    order_id = int(parts[2])
    new_status = parts[3]
    
    order = get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    update_order_status(order_id, new_status)
    
    # Notify user about status change
    try:
        await bot.send_message(
            order['user_id'],
            f"📦 Статус заказа #{order_id} изменён:\n"
            f"{STATUS_NAMES.get(new_status, new_status)}"
        )
    except Exception as e:
        print(f"Failed to notify user: {e}")
    
    await callback.answer(f"Статус изменён на: {STATUS_NAMES.get(new_status, new_status)}")
    
    # Refresh order view
    order = get_order(order_id)
    couriers = get_users_by_role('courier')
    
    items_text = "\n".join([
        f"  • {item['name']} × {item['quantity']} = {item['price'] * item['quantity']}₽"
        for item in order['items']
    ])
    
    order_text = (
        f"📦 <b>Заказ #{order['id']}</b>\n\n"
        f"👤 Клиент: {order.get('first_name', 'Неизвестно')}\n"
        f"📍 Адрес: {order['delivery_address']}\n\n"
        f"📊 Статус: {STATUS_NAMES.get(order['status'], order['status'])}\n\n"
        f"🍽 <b>Состав:</b>\n{items_text}\n\n"
        f"💰 <b>Итого: {order['total_price']}₽</b>"
    )
    
    await callback.message.edit_text(
        order_text,
        parse_mode="HTML",
        reply_markup=get_order_manage_keyboard(order_id, order['status'], couriers)
    )


@router.callback_query(F.data.startswith("admin:assign_courier:"))
async def admin_assign_courier_callback(callback: CallbackQuery, bot: Bot):
    """Assign courier to order"""
    if not is_admin_or_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    order_id = int(parts[2])
    courier_id = int(parts[3])
    
    assign_courier(order_id, courier_id)
    
    order = get_order(order_id)
    
    # Notify courier
    try:
        items_text = "\n".join([
            f"  • {item['name']} × {item['quantity']}"
            for item in order['items']
        ])
        
        await bot.send_message(
            courier_id,
            f"🚚 <b>Новый заказ для доставки!</b>\n\n"
            f"📦 Заказ #{order_id}\n"
            f"📍 Адрес: {order['delivery_address']}\n"
            f"📱 Телефон: {order.get('phone', 'Не указан')}\n\n"
            f"🍽 Состав:\n{items_text}\n\n"
            f"💰 Сумма: {order['total_price']}₽\n\n"
            f"Используйте /courier для управления доставками.",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Failed to notify courier: {e}")
    
    await callback.answer("Курьер назначен ✅")
    
    # Go back to orders list
    await admin_orders_callback(callback)


@router.callback_query(F.data == "admin:menu")
async def admin_menu_callback(callback: CallbackQuery):
    """Show menu editing options"""
    if not is_admin_or_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🍽 <b>Редактирование меню</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_menu_edit_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:export_menu")
async def admin_export_menu_callback(callback: CallbackQuery):
    """Export menu as JSON"""
    if not is_admin_or_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    menu_json = export_menu_json()
    
    # Send as file
    from aiogram.types import BufferedInputFile
    file = BufferedInputFile(menu_json.encode('utf-8'), filename="menu.json")
    
    await callback.message.answer_document(
        file,
        caption="📥 Меню экспортировано.\n\n"
                "Отредактируйте JSON и отправьте обратно для импорта."
    )
    await callback.answer("Меню экспортировано")


@router.callback_query(F.data == "admin:import_menu")
async def admin_import_menu_callback(callback: CallbackQuery, state: FSMContext):
    """Start menu import process"""
    if not is_admin_or_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_menu_json)
    
    await callback.message.edit_text(
        "📤 <b>Импорт меню</b>\n\n"
        "Отправьте JSON файл с меню или текст в формате JSON.\n\n"
        "Отправьте /cancel для отмены.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_menu_json, F.document)
async def admin_import_menu_file(message: Message, state: FSMContext, bot: Bot):
    """Handle menu JSON file upload"""
    if not is_admin_or_director(message.from_user.id):
        return
    
    file = await bot.get_file(message.document.file_id)
    file_content = await bot.download_file(file.file_path)
    
    try:
        json_str = file_content.read().decode('utf-8')
        if import_menu_json(json_str):
            await message.answer("✅ Меню успешно импортировано!")
        else:
            await message.answer("❌ Ошибка импорта. Проверьте формат JSON.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    
    await state.clear()


@router.message(AdminStates.waiting_menu_json, F.text)
async def admin_import_menu_text(message: Message, state: FSMContext):
    """Handle menu JSON text"""
    if not is_admin_or_director(message.from_user.id):
        return
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Импорт отменён", reply_markup=get_admin_panel_keyboard())
        return
    
    if import_menu_json(message.text):
        await message.answer("✅ Меню успешно импортировано!")
    else:
        await message.answer("❌ Ошибка импорта. Проверьте формат JSON.")
    
    await state.clear()


@router.callback_query(F.data == "admin:add_item")
async def admin_add_item_callback(callback: CallbackQuery, state: FSMContext):
    """Start adding new menu item"""
    if not is_admin_or_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    categories = get_categories()
    
    await callback.message.edit_text(
        "➕ <b>Добавление блюда</b>\n\n"
        "Выберите категорию:",
        parse_mode="HTML",
        reply_markup=get_category_select_keyboard(categories, "add")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:add_category:"))
async def admin_add_category_callback(callback: CallbackQuery, state: FSMContext):
    """Set category for new item"""
    if not is_admin_or_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    category_id = int(callback.data.split(":")[2])
    await state.update_data(category_id=category_id)
    await state.set_state(AdminStates.waiting_item_name)
    
    await callback.message.edit_text(
        "➕ <b>Добавление блюда</b>\n\n"
        "Введите название блюда:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_item_name)
async def admin_item_name_handler(message: Message, state: FSMContext):
    """Handle item name input"""
    if not is_admin_or_director(message.from_user.id):
        return
    
    await state.update_data(item_name=message.text)
    await state.set_state(AdminStates.waiting_item_description)
    
    await message.answer("Введите описание блюда:")


@router.message(AdminStates.waiting_item_description)
async def admin_item_description_handler(message: Message, state: FSMContext):
    """Handle item description input"""
    if not is_admin_or_director(message.from_user.id):
        return
    
    await state.update_data(item_description=message.text)
    await state.set_state(AdminStates.waiting_item_price)
    
    await message.answer("Введите цену блюда (число):")


@router.message(AdminStates.waiting_item_price)
async def admin_item_price_handler(message: Message, state: FSMContext):
    """Handle item price input and create item"""
    if not is_admin_or_director(message.from_user.id):
        return
    
    try:
        price = int(message.text)
    except ValueError:
        await message.answer("❌ Введите числовое значение цены:")
        return
    
    data = await state.get_data()
    
    item_id = add_menu_item(
        category_id=data['category_id'],
        name=data['item_name'],
        description=data['item_description'],
        price=price
    )
    
    await state.clear()
    
    await message.answer(
        f"✅ Блюдо добавлено!\n\n"
        f"🆔 ID: {item_id}\n"
        f"📛 Название: {data['item_name']}\n"
        f"💰 Цена: {price}₽",
        reply_markup=get_admin_panel_keyboard()
    )


@router.callback_query(F.data == "admin:delete_item")
async def admin_delete_item_callback(callback: CallbackQuery):
    """Show items for deletion"""
    if not is_admin_or_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    items = get_menu_items()
    
    await callback.message.edit_text(
        "❌ <b>Удаление блюда</b>\n\n"
        "Выберите блюдо для удаления:",
        parse_mode="HTML",
        reply_markup=get_menu_items_keyboard(items, "delete")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:delete_item:"))
async def admin_delete_item_confirm_callback(callback: CallbackQuery):
    """Delete menu item"""
    if not is_admin_or_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    item_id = int(callback.data.split(":")[2])
    
    if delete_menu_item(item_id):
        await callback.answer("✅ Блюдо удалено")
    else:
        await callback.answer("❌ Ошибка удаления", show_alert=True)
    
    # Refresh list
    items = get_menu_items()
    await callback.message.edit_text(
        "❌ <b>Удаление блюда</b>\n\n"
        "Выберите блюдо для удаления:",
        parse_mode="HTML",
        reply_markup=get_menu_items_keyboard(items, "delete")
    )


@router.callback_query(F.data == "admin:stats")
async def admin_stats_callback(callback: CallbackQuery):
    """Show statistics"""
    if not is_admin_or_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    from ..database import get_connection
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Total orders
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]
        
        # Today orders
        cursor.execute("SELECT COUNT(*) FROM orders WHERE date(created_at) = date('now')")
        today_orders = cursor.fetchone()[0]
        
        # Total revenue
        cursor.execute("SELECT COALESCE(SUM(total_price), 0) FROM orders WHERE status = 'delivered'")
        total_revenue = cursor.fetchone()[0]
        
        # Total users
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        # Active orders
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status NOT IN ('delivered', 'cancelled')")
        active_orders = cursor.fetchone()[0]
    
    await callback.message.edit_text(
        "📊 <b>Статистика</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📦 Всего заказов: {total_orders}\n"
        f"📦 Заказов сегодня: {today_orders}\n"
        f"⏳ Активных заказов: {active_orders}\n"
        f"💰 Общая выручка: {total_revenue}₽",
        parse_mode="HTML",
        reply_markup=get_admin_panel_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.in_({"admin:back", "admin:close"}))
async def admin_back_callback(callback: CallbackQuery, state: FSMContext):
    """Back to admin panel or close"""
    await state.clear()
    
    if callback.data == "admin:close":
        await callback.message.delete()
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "🛠 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_admin_panel_keyboard()
    )
    await callback.answer()
