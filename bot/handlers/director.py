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

from ..database import (
    get_user, create_user, update_user_role, get_users_by_role, DIRECTOR_ID
)
from ..keyboards import (
    get_director_panel_keyboard, get_role_list_keyboard,
    get_confirm_role_action_keyboard
)

router = Router()


class DirectorStates(StatesGroup):
    """Director conversation states"""
    waiting_admin_id = State()
    waiting_courier_id = State()


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
