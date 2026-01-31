"""
Director handlers for Telegram Cafe Bot
Handles director-only functions: adding/removing admins and couriers
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import (
    get_user, create_user, update_user_role, get_users_by_role, DIRECTOR_ID,
    get_categories, get_menu_items, get_menu_item, add_menu_item,
    update_menu_item, delete_menu_item, get_connection
)
from keyboards import (
    get_director_panel_keyboard, get_role_list_keyboard,
    get_confirm_role_action_keyboard, get_director_staff_keyboard,
    get_director_menu_management_keyboard, get_dish_list_keyboard,
    get_dish_edit_keyboard, get_category_select_keyboard
)

router = Router()


class DirectorStates(StatesGroup):
    """Director conversation states"""
    waiting_admin_id = State()
    waiting_courier_id = State()
    # Dish management states
    waiting_dish_category = State()
    waiting_dish_name = State()
    waiting_dish_price = State()
    waiting_dish_description = State()
    waiting_dish_image = State()
    # Edit states
    waiting_edit_name = State()
    waiting_edit_price = State()
    waiting_edit_description = State()


def is_director(user_id: int) -> bool:
    """Check if user is director"""
    return user_id == DIRECTOR_ID


@router.message(Command("director"))
async def cmd_director(message: Message):
    """Handle /director command"""
    if not is_director(message.from_user.id):
        await message.answer("⛔ Эта команда доступна только директору")
        return
    
    await message.answer(
        "👑 <b>Панель директора</b>\n\n"
        f"🆔 Ваш ID: <code>{message.from_user.id}</code>\n\n"
        "Управление ролями персонала:",
        parse_mode="HTML",
        reply_markup=get_director_panel_keyboard()
    )


@router.callback_query(F.data == "director:add_admin")
async def director_add_admin_callback(callback: CallbackQuery, state: FSMContext):
    """Start adding admin process"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await state.set_state(DirectorStates.waiting_admin_id)
    
    await callback.message.edit_text(
        "➕ <b>Добавление администратора</b>\n\n"
        "Введите Telegram ID пользователя:\n\n"
        "<i>Пользователь может узнать свой ID, написав боту /start</i>\n\n"
        "Отправьте /cancel для отмены.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(DirectorStates.waiting_admin_id)
async def director_admin_id_handler(message: Message, state: FSMContext):
    """Handle admin ID input"""
    if not is_director(message.from_user.id):
        return
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Отменено",
            reply_markup=get_director_panel_keyboard()
        )
        return
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите корректный числовой ID:")
        return
    
    if user_id == DIRECTOR_ID:
        await message.answer("❌ Нельзя изменить роль директора")
        return
    
    # Check if user exists, if not - create
    user = get_user(user_id)
    if not user:
        create_user(user_id, welcome_bonus=0)
        user = get_user(user_id)
    
    # Update role
    update_user_role(user_id, 'admin')
    
    await state.clear()
    
    name = user.get('first_name') or user.get('username') or str(user_id)
    
    await message.answer(
        f"✅ <b>Администратор добавлен!</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Имя: {name}\n"
        f"👔 Роль: 🛠 Администратор\n\n"
        f"Теперь этот пользователь может использовать /admin",
        parse_mode="HTML",
        reply_markup=get_director_panel_keyboard()
    )


@router.callback_query(F.data == "director:add_courier")
async def director_add_courier_callback(callback: CallbackQuery, state: FSMContext):
    """Start adding courier process"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await state.set_state(DirectorStates.waiting_courier_id)
    
    await callback.message.edit_text(
        "➕ <b>Добавление курьера</b>\n\n"
        "Введите Telegram ID пользователя:\n\n"
        "<i>Пользователь может узнать свой ID, написав боту /start</i>\n\n"
        "Отправьте /cancel для отмены.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(DirectorStates.waiting_courier_id)
async def director_courier_id_handler(message: Message, state: FSMContext):
    """Handle courier ID input"""
    if not is_director(message.from_user.id):
        return
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Отменено",
            reply_markup=get_director_panel_keyboard()
        )
        return
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите корректный числовой ID:")
        return
    
    if user_id == DIRECTOR_ID:
        await message.answer("❌ Нельзя изменить роль директора")
        return
    
    # Check if user exists, if not - create
    user = get_user(user_id)
    if not user:
        create_user(user_id, welcome_bonus=0)
        user = get_user(user_id)
    
    # Update role
    update_user_role(user_id, 'courier')
    
    await state.clear()
    
    name = user.get('first_name') or user.get('username') or str(user_id)
    
    await message.answer(
        f"✅ <b>Курьер добавлен!</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Имя: {name}\n"
        f"🚚 Роль: Курьер\n\n"
        f"Теперь этот пользователь может использовать /courier",
        parse_mode="HTML",
        reply_markup=get_director_panel_keyboard()
    )


@router.callback_query(F.data == "director:list_roles")
async def director_list_roles_callback(callback: CallbackQuery):
    """Show all users with roles"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    admins = get_users_by_role('admin')
    couriers = get_users_by_role('courier')
    
    text = "📋 <b>Список ролей</b>\n\n"
    
    text += "👑 <b>Директор:</b>\n"
    director = get_user(DIRECTOR_ID)
    director_name = director.get('first_name') if director else "Не в базе"
    text += f"  • {director_name} (ID: <code>{DIRECTOR_ID}</code>)\n\n"
    
    text += "🛠 <b>Администраторы:</b>\n"
    if admins:
        for admin in admins:
            name = admin.get('first_name') or admin.get('username') or 'Неизвестно'
            text += f"  • {name} (ID: <code>{admin['telegram_id']}</code>)\n"
    else:
        text += "  <i>Нет администраторов</i>\n"
    
    text += "\n🚚 <b>Курьеры:</b>\n"
    if couriers:
        for courier in couriers:
            name = courier.get('first_name') or courier.get('username') or 'Неизвестно'
            text += f"  • {name} (ID: <code>{courier['telegram_id']}</code>)\n"
    else:
        text += "  <i>Нет курьеров</i>\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_director_panel_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "director:remove_role")
async def director_remove_role_callback(callback: CallbackQuery):
    """Show users for role removal"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    admins = get_users_by_role('admin')
    couriers = get_users_by_role('courier')
    
    all_staff = admins + couriers
    
    if not all_staff:
        await callback.answer("Нет пользователей для удаления", show_alert=True)
        return
    
    await callback.message.edit_text(
        "❌ <b>Удаление роли</b>\n\n"
        "Выберите пользователя для удаления роли:",
        parse_mode="HTML",
        reply_markup=get_role_list_keyboard(all_staff, "remove")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("director:confirm_remove:"))
async def director_confirm_remove_callback(callback: CallbackQuery):
    """Confirm role removal"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split(":")[2])
    user = get_user(user_id)
    
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    
    if user_id == DIRECTOR_ID:
        await callback.answer("Нельзя удалить роль директора", show_alert=True)
        return
    
    role_name = {'admin': '🛠 Администратор', 'courier': '🚚 Курьер'}.get(user['role'], user['role'])
    name = user.get('first_name') or user.get('username') or str(user_id)
    
    await callback.message.edit_text(
        f"❌ <b>Подтверждение удаления роли</b>\n\n"
        f"👤 Пользователь: {name}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👔 Текущая роль: {role_name}\n\n"
        f"Подтвердите удаление роли (станет обычным пользователем):",
        parse_mode="HTML",
        reply_markup=get_confirm_role_action_keyboard(user_id, "remove")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("director:do_remove:"))
async def director_do_remove_callback(callback: CallbackQuery):
    """Execute role removal"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split(":")[2])
    
    if user_id == DIRECTOR_ID:
        await callback.answer("Нельзя удалить роль директора", show_alert=True)
        return
    
    user = get_user(user_id)
    name = user.get('first_name') if user else str(user_id)
    
    update_user_role(user_id, 'user')
    
    await callback.message.edit_text(
        f"✅ <b>Роль удалена!</b>\n\n"
        f"👤 Пользователь: {name}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👔 Новая роль: 👤 Пользователь",
        parse_mode="HTML",
        reply_markup=get_director_panel_keyboard()
    )
    await callback.answer("Роль удалена")


@router.callback_query(F.data == "director:back")
async def director_back_callback(callback: CallbackQuery, state: FSMContext):
    """Back to director panel"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await state.clear()
    
    await callback.message.edit_text(
        "👑 <b>Панель директора</b>\n\n"
        f"🆔 Ваш ID: <code>{callback.from_user.id}</code>\n\n"
        "Управление ролями персонала:",
        parse_mode="HTML",
        reply_markup=get_director_panel_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "director:close")
async def director_close_callback(callback: CallbackQuery, state: FSMContext):
    """Close director panel"""
    await state.clear()
    await callback.message.delete()
    await callback.answer()


# ============ STAFF MANAGEMENT SUBMENU ============

@router.callback_query(F.data == "director:staff_menu")
async def director_staff_menu_callback(callback: CallbackQuery):
    """Show staff management submenu"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "👥 <b>Управление персоналом</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_director_staff_keyboard()
    )
    await callback.answer()


# ============ MENU MANAGEMENT ============

@router.callback_query(F.data == "director:menu_management")
async def director_menu_management_callback(callback: CallbackQuery):
    """Show menu management submenu"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🍽 <b>Управление меню</b>\n\n"
        "Все изменения автоматически отображаются в Mini App.\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_director_menu_management_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "director:list_dishes")
async def director_list_dishes_callback(callback: CallbackQuery):
    """Show all dishes"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    items = get_menu_items()
    
    if not items:
        await callback.answer("Меню пусто", show_alert=True)
        return
    
    text = "📋 <b>Список блюд:</b>\n\n"
    categories = get_categories()
    
    for cat in categories:
        cat_items = [i for i in items if i['category_id'] == cat['id']]
        if cat_items:
            text += f"\n<b>{cat['emoji']} {cat['name']}:</b>\n"
            for item in cat_items:
                status = "✅" if item.get('is_available', 1) else "❌"
                text += f"  {status} {item['name']} — {item['price']}₽\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_director_menu_management_keyboard()
    )
    await callback.answer()


# ============ ADD DISH ============

@router.callback_query(F.data == "director:add_dish")
async def director_add_dish_callback(callback: CallbackQuery, state: FSMContext):
    """Start adding dish - select category"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    categories = get_categories()
    
    await callback.message.edit_text(
        "➕ <b>Добавление блюда</b>\n\n"
        "Шаг 1/5: Выберите категорию:",
        parse_mode="HTML",
        reply_markup=get_category_select_keyboard(categories, "director_add")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:director_add_category:"))
async def director_select_category_callback(callback: CallbackQuery, state: FSMContext):
    """Category selected for new dish"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    category_id = int(callback.data.split(":")[2])
    await state.update_data(new_dish_category=category_id)
    await state.set_state(DirectorStates.waiting_dish_name)
    
    await callback.message.edit_text(
        "➕ <b>Добавление блюда</b>\n\n"
        "Шаг 2/5: Введите название блюда:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(DirectorStates.waiting_dish_name)
async def director_dish_name_handler(message: Message, state: FSMContext):
    """Handle dish name input"""
    if not is_director(message.from_user.id):
        return
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=get_director_menu_management_keyboard())
        return
    
    await state.update_data(new_dish_name=message.text)
    await state.set_state(DirectorStates.waiting_dish_price)
    
    await message.answer(
        "➕ <b>Добавление блюда</b>\n\n"
        "Шаг 3/5: Введите цену (число в рублях):",
        parse_mode="HTML"
    )


@router.message(DirectorStates.waiting_dish_price)
async def director_dish_price_handler(message: Message, state: FSMContext):
    """Handle dish price input"""
    if not is_director(message.from_user.id):
        return
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    try:
        price = int(message.text.strip())
        if price <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректную цену (положительное число):")
        return
    
    await state.update_data(new_dish_price=price)
    await state.set_state(DirectorStates.waiting_dish_description)
    
    await message.answer(
        "➕ <b>Добавление блюда</b>\n\n"
        "Шаг 4/5: Введите описание блюда\n"
        "(или отправьте <code>-</code> чтобы пропустить):",
        parse_mode="HTML"
    )


@router.message(DirectorStates.waiting_dish_description)
async def director_dish_description_handler(message: Message, state: FSMContext):
    """Handle dish description input"""
    if not is_director(message.from_user.id):
        return
    
    description = message.text if message.text != "-" else ""
    await state.update_data(new_dish_description=description)
    await state.set_state(DirectorStates.waiting_dish_image)
    
    await message.answer(
        "➕ <b>Добавление блюда</b>\n\n"
        "Шаг 5/5: Отправьте ссылку на изображение\n"
        "(или отправьте <code>-</code> чтобы пропустить):",
        parse_mode="HTML"
    )


@router.message(DirectorStates.waiting_dish_image)
async def director_dish_image_handler(message: Message, state: FSMContext):
    """Handle dish image URL and create dish"""
    if not is_director(message.from_user.id):
        return
    
    image_url = message.text if message.text != "-" else None
    
    data = await state.get_data()
    
    # Create dish in database
    item_id = add_menu_item(
        category_id=data['new_dish_category'],
        name=data['new_dish_name'],
        description=data.get('new_dish_description', ''),
        price=data['new_dish_price'],
        image_url=image_url,
        is_new=1
    )
    
    await state.clear()
    
    await message.answer(
        f"✅ <b>Блюдо добавлено!</b>\n\n"
        f"🆔 ID: {item_id}\n"
        f"📛 Название: {data['new_dish_name']}\n"
        f"💰 Цена: {data['new_dish_price']}₽\n"
        f"📄 Описание: {data.get('new_dish_description') or 'Нет'}\n\n"
        f"Блюдо уже доступно в Mini App!",
        parse_mode="HTML",
        reply_markup=get_director_menu_management_keyboard()
    )


# ============ EDIT DISH ============

@router.callback_query(F.data == "director:edit_dish")
async def director_edit_dish_callback(callback: CallbackQuery):
    """Show dishes for editing"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    items = get_menu_items()
    
    if not items:
        await callback.answer("Меню пусто", show_alert=True)
        return
    
    await callback.message.edit_text(
        "✏️ <b>Изменение блюда</b>\n\n"
        "Выберите блюдо для редактирования:",
        parse_mode="HTML",
        reply_markup=get_dish_list_keyboard(items, "edit")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("director:edit_dish_id:"))
async def director_edit_dish_id_callback(callback: CallbackQuery):
    """Show edit options for selected dish"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    item_id = int(callback.data.split(":")[2])
    item = get_menu_item(item_id)
    
    if not item:
        await callback.answer("Блюдо не найдено", show_alert=True)
        return
    
    status = "✅ Доступно" if item.get('is_available', 1) else "❌ Недоступно"
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование блюда</b>\n\n"
        f"🆔 ID: {item['id']}\n"
        f"📛 Название: {item['name']}\n"
        f"💰 Цена: {item['price']}₽\n"
        f"📄 Описание: {item.get('description') or 'Нет'}\n"
        f"📊 Статус: {status}\n\n"
        f"Выберите что изменить:",
        parse_mode="HTML",
        reply_markup=get_dish_edit_keyboard(item_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("director:edit_name:"))
async def director_edit_name_callback(callback: CallbackQuery, state: FSMContext):
    """Start editing dish name"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    item_id = int(callback.data.split(":")[2])
    await state.update_data(editing_dish_id=item_id)
    await state.set_state(DirectorStates.waiting_edit_name)
    
    await callback.message.edit_text(
        "📝 Введите новое название блюда:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(DirectorStates.waiting_edit_name)
async def director_edit_name_handler(message: Message, state: FSMContext):
    """Handle new dish name"""
    if not is_director(message.from_user.id):
        return
    
    data = await state.get_data()
    item_id = data['editing_dish_id']
    
    update_menu_item(item_id, name=message.text)
    await state.clear()
    
    await message.answer(
        f"✅ Название изменено на: <b>{message.text}</b>",
        parse_mode="HTML",
        reply_markup=get_director_menu_management_keyboard()
    )


@router.callback_query(F.data.startswith("director:edit_price:"))
async def director_edit_price_callback(callback: CallbackQuery, state: FSMContext):
    """Start editing dish price"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    item_id = int(callback.data.split(":")[2])
    await state.update_data(editing_dish_id=item_id)
    await state.set_state(DirectorStates.waiting_edit_price)
    
    await callback.message.edit_text(
        "💰 Введите новую цену (число в рублях):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(DirectorStates.waiting_edit_price)
async def director_edit_price_handler(message: Message, state: FSMContext):
    """Handle new dish price"""
    if not is_director(message.from_user.id):
        return
    
    try:
        price = int(message.text.strip())
        if price <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректную цену:")
        return
    
    data = await state.get_data()
    item_id = data['editing_dish_id']
    
    update_menu_item(item_id, price=price)
    await state.clear()
    
    await message.answer(
        f"✅ Цена изменена на: <b>{price}₽</b>",
        parse_mode="HTML",
        reply_markup=get_director_menu_management_keyboard()
    )


@router.callback_query(F.data.startswith("director:edit_desc:"))
async def director_edit_desc_callback(callback: CallbackQuery, state: FSMContext):
    """Start editing dish description"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    item_id = int(callback.data.split(":")[2])
    await state.update_data(editing_dish_id=item_id)
    await state.set_state(DirectorStates.waiting_edit_description)
    
    await callback.message.edit_text(
        "📄 Введите новое описание блюда:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(DirectorStates.waiting_edit_description)
async def director_edit_desc_handler(message: Message, state: FSMContext):
    """Handle new dish description"""
    if not is_director(message.from_user.id):
        return
    
    data = await state.get_data()
    item_id = data['editing_dish_id']
    
    update_menu_item(item_id, description=message.text)
    await state.clear()
    
    await message.answer(
        "✅ Описание обновлено!",
        parse_mode="HTML",
        reply_markup=get_director_menu_management_keyboard()
    )


@router.callback_query(F.data.startswith("director:toggle_avail:"))
async def director_toggle_avail_callback(callback: CallbackQuery):
    """Toggle dish availability"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    item_id = int(callback.data.split(":")[2])
    item = get_menu_item(item_id)
    
    if not item:
        await callback.answer("Блюдо не найдено", show_alert=True)
        return
    
    new_status = 0 if item.get('is_available', 1) else 1
    update_menu_item(item_id, is_available=new_status)
    
    status_text = "✅ Блюдо включено" if new_status else "❌ Блюдо отключено"
    await callback.answer(status_text)
    
    # Refresh view
    item = get_menu_item(item_id)
    status = "✅ Доступно" if item.get('is_available', 1) else "❌ Недоступно"
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование блюда</b>\n\n"
        f"🆔 ID: {item['id']}\n"
        f"📛 Название: {item['name']}\n"
        f"💰 Цена: {item['price']}₽\n"
        f"📄 Описание: {item.get('description') or 'Нет'}\n"
        f"📊 Статус: {status}\n\n"
        f"Выберите что изменить:",
        parse_mode="HTML",
        reply_markup=get_dish_edit_keyboard(item_id)
    )


# ============ DELETE DISH ============

@router.callback_query(F.data == "director:delete_dish")
async def director_delete_dish_callback(callback: CallbackQuery):
    """Show dishes for deletion"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    items = get_menu_items()
    
    if not items:
        await callback.answer("Меню пусто", show_alert=True)
        return
    
    await callback.message.edit_text(
        "❌ <b>Удаление блюда</b>\n\n"
        "Выберите блюдо для удаления:",
        parse_mode="HTML",
        reply_markup=get_dish_list_keyboard(items, "confirm_delete")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("director:confirm_delete_dish_id:"))
async def director_confirm_delete_callback(callback: CallbackQuery):
    """Confirm dish deletion"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    item_id = int(callback.data.split(":")[2])
    item = get_menu_item(item_id)
    
    if not item:
        await callback.answer("Блюдо не найдено", show_alert=True)
        return
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"director:do_delete_dish:{item_id}")
    builder.button(text="❌ Отмена", callback_data="director:delete_dish")
    builder.adjust(2)
    
    await callback.message.edit_text(
        f"❌ <b>Подтверждение удаления</b>\n\n"
        f"Вы уверены, что хотите удалить:\n"
        f"📛 {item['name']} — {item['price']}₽?",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("director:do_delete_dish:"))
async def director_do_delete_callback(callback: CallbackQuery):
    """Execute dish deletion"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    item_id = int(callback.data.split(":")[2])
    item = get_menu_item(item_id)
    name = item['name'] if item else "Блюдо"
    
    delete_menu_item(item_id)
    
    await callback.message.edit_text(
        f"✅ Блюдо <b>{name}</b> удалено!",
        parse_mode="HTML",
        reply_markup=get_director_menu_management_keyboard()
    )
    await callback.answer("Блюдо удалено")


# ============ ORDERS & STATS FOR DIRECTOR ============

@router.callback_query(F.data == "director:all_orders")
async def director_all_orders_callback(callback: CallbackQuery):
    """Show all orders for director"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    from database import get_pending_orders
    orders = get_pending_orders()
    
    if not orders:
        await callback.message.edit_text(
            "📋 <b>Заказы</b>\n\n"
            "Нет активных заказов.",
            parse_mode="HTML",
            reply_markup=get_director_panel_keyboard()
        )
        await callback.answer()
        return
    
    STATUS_NAMES = {
        'pending': '⏳ Ожидает',
        'confirmed': '✅ Подтверждён',
        'cooking': '👨‍🍳 Готовится',
        'ready': '📦 Готов',
        'delivering': '🚚 Доставляется',
    }
    
    text = "📋 <b>Активные заказы:</b>\n\n"
    for order in orders[:15]:
        text += (
            f"#{order['id']} | {STATUS_NAMES.get(order['status'], order['status'])}\n"
            f"👤 {order.get('first_name', 'Клиент')} | {order['total_price']}₽\n\n"
        )
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_director_panel_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "director:stats")
async def director_stats_callback(callback: CallbackQuery):
    """Show statistics for director"""
    if not is_director(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE date(created_at) = date('now')")
        today_orders = cursor.fetchone()[0]
        
        cursor.execute("SELECT COALESCE(SUM(total_price), 0) FROM orders WHERE status = 'delivered'")
        total_revenue = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'user'")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM menu_items WHERE is_available = 1")
        active_dishes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status NOT IN ('delivered', 'cancelled')")
        active_orders = cursor.fetchone()[0]
    
    await callback.message.edit_text(
        "📊 <b>Статистика кафе</b>\n\n"
        f"👥 Клиентов: {total_users}\n"
        f"🍽 Активных блюд: {active_dishes}\n\n"
        f"📦 Всего заказов: {total_orders}\n"
        f"📦 Заказов сегодня: {today_orders}\n"
        f"⏳ Активных заказов: {active_orders}\n\n"
        f"💰 Общая выручка: {total_revenue}₽",
        parse_mode="HTML",
        reply_markup=get_director_panel_keyboard()
    )
    await callback.answer()
