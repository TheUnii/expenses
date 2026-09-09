import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
 

load_dotenv('config.env')

BOT_TOKEN = os.getenv("BOT_TOKEN")

PASSWORD = os.getenv("PASSWORD")

ALLOWED_USER1 = int(os.getenv("ALLOWED_USER1"))
ALLOWED_USER2 = int(os.getenv("ALLOWED_USER2"))

ALLOWED_USERS = {
    int(user_id.strip())
    for user_id in os.getenv("ALLOWED_USERS", "").split(",")
    if user_id.strip()
}

CATEGORIES = [
    "🍔 Еда",
    "🚗 Транспорт",
    "🎉 Развлечения",
    "🏠 Быт",
    "💊 Здоровье",
    "👕 Одежда",
    "📦 Другое",
]

logging.basicConfig(level=logging.INFO)

router = Router()

class AddExpense(StatesGroup):
    waiting_for_category = State()
    waiting_for_custom_category = State()
    waiting_for_amount = State()

def main_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить трату", callback_data="add_expense")
    builder.button(text="📊 История трат", callback_data="history")
    builder.adjust(1)
    return builder.as_markup()


def categories_kb():
    builder = InlineKeyboardBuilder()
    for cat in CATEGORIES:
        builder.button(text=cat, callback_data=f"cat:{CATEGORIES.index(cat)}")
    builder.button(text="✍️ Своя категория", callback_data="cat_custom")
    builder.button(text="⬅️ Отмена", callback_data="cancel")
    builder.adjust(2)
    return builder.as_markup()


def history_period_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="За день", callback_data="hist:1")
    builder.button(text="За неделю", callback_data="hist:7")
    builder.button(text="🗑 Удалить последнюю трату", callback_data="del")
    builder.button(text="⬅️ В меню", callback_data="back_main")
    builder.adjust(2)
    return builder.as_markup()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    user_id = message.from_user.id

    if user_id not in ALLOWED_USERS:
        await message.answer("❌ У вас нет доступа к этому боту.")
        return

    await message.answer(
        "Привет! Я бот для учёта общего бюджета.",
        reply_markup=main_menu_kb()
    )


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Отменено.", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "add_expense")
async def add_expense_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddExpense.waiting_for_category)
    await callback.message.edit_text(
        "Выберите категорию траты или введите свою:",
        reply_markup=categories_kb(),
    )
    await callback.answer()


@router.callback_query(AddExpense.waiting_for_category, F.data.startswith("cat:"))
async def category_chosen(callback: CallbackQuery, state: FSMContext):
    index = int(callback.data.split(":", 1)[1])
    category = CATEGORIES[index]
    await state.update_data(category=category)
    await state.set_state(AddExpense.waiting_for_amount)
    await callback.message.edit_text(
        f"Категория: {category}\nВведите сумму:"
    )
    await callback.answer()


@router.callback_query(AddExpense.waiting_for_category, F.data == "cat_custom")
async def category_custom_request(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddExpense.waiting_for_custom_category)
    await callback.message.edit_text("Напишите название категории текстом:")
    await callback.answer()


@router.message(AddExpense.waiting_for_custom_category)
async def category_custom_entered(message: Message, state: FSMContext):
    category = message.text.strip()
    if not category:
        await message.answer("Название категории не может быть пустым. Попробуйте ещё раз:")
        return
    await state.update_data(category=category)
    await state.set_state(AddExpense.waiting_for_amount)
    await message.answer(
        f"Категория: {category}\nВведите сумму траты (например: 350 или 350.50):"
    )

@router.message(AddExpense.waiting_for_amount)
async def amount_entered(message: Message, state: FSMContext, bot: Bot):
    raw = message.text.strip().replace(",", ".")
    try:
        amount = float(raw)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Введите корректное положительное число, например: 250 или 99.90")
        return

    data = await state.get_data()
    category = data.get("category", "Без категории")

    user = message.from_user
    username = user.username or user.full_name

    db.add_expense(user_id=user.id, username=username, category=category, amount=amount)
    await state.clear()

    count, total = db.get_month_summary()

    user_id = message.from_user.id

    if user_id == ALLOWED_USER2 and amount > 1500:
        await message.answer("Сообщение от Вани:")
        await message.answer_sticker(sticker="CAACAgQAAxkBAAER4ERqodHZiVJbAhGXzYcIf2w7SHglxQACSxMAAuJz0VBRcPV9Q2figD0E")
        await bot.send_animation(chat_id=ALLOWED_USER1, animation="CgACAgIAAxkBAAMwaqHUZDpzW0bRCx0lmw10FZVU6v4AAnCqAALmHRBJEI32aDhoe_I9BA")
        text = f"Саша потратила {amount:.0f} рублей"
        await bot.send_message(chat_id=ALLOWED_USER1, text=text)

    await message.answer(
        "✅ Трата сохранена!\n"
        f"Категория: {category}\n"
        f"Сумма: {amount:.2f} ₽\n\n"
        f"📅 Итог за текущий месяц: {total:.2f}\n",
        reply_markup=main_menu_kb(),
    )



@router.callback_query(F.data == "history")
async def history_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "За какой период показать историю?",
        reply_markup=history_period_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("hist:"))
async def history_show(callback: CallbackQuery):
    days = int(callback.data.split(":", 1)[1])
    rows = db.get_expenses_period(days)
    period_name = "день" if days == 1 else "неделю"

    if not rows:
        text = f"За последний {period_name} трат не найдено."
    else:
        lines = [f"📊 История за последний {period_name} (все пользователи):\n"]
        total = 0.0
        for username, category, amount, created_at in rows:
            total += amount
            date_short = created_at[:16]
            lines.append(f"• {date_short} | {username} | {category} — {amount:.2f} ₽")
        lines.append(f"\n💰 Итого: {total:.2f} ₽ ({len(rows)} трат)")
        text = "\n".join(lines)

    if len(text) > 4000:
        text = text[:4000] + "\n\n... (список обрезан, слишком много записей)"

    await callback.message.edit_text(text, reply_markup=history_period_kb())
    await callback.answer()

@router.callback_query(F.data == "del")
async def delete_last_expense(callback: CallbackQuery):
    user_id = callback.from_user.id

    deleted = db.delete_last_expense(user_id)

    if deleted:
        await callback.message.answer("🗑 Последняя трата удалена.", reply_markup=main_menu_kb())
    else:
        await callback.message.answer("У вас нет трат.", reply_markup=main_menu_kb())

    await callback.answer()

async def main():
    db.init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
