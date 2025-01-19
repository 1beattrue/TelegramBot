import os
import sqlite3

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, \
    CallbackQueryHandler, ContextTypes

# Загрузка переменных из .env
load_dotenv()
api_key = os.getenv("API_KEY")

# Глобальные константы
SERVER_1_NAME = "Los Angeles (Tier-3)"
SERVER_2_NAME = "EUnetworks (Амстердам)"
SERVER_1_COST = 508
SERVER_2_COST = 444

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('vpn_manager.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        server_1 BOOLEAN DEFAULT 0,
        server_2 BOOLEAN DEFAULT 0
    )''')
    conn.commit()
    conn.close()

# Получение telegram_id
def get_telegram_id(update: Update) -> int:
    return update.effective_user.id

# Получение username
def get_username(update: Update) -> str:
    return update.effective_user.username or f"user_{get_telegram_id(update)}"

# Проверка наличия пользователя на первом сервере
def is_subscribed_server_1(telegram_id) -> bool:
    conn = sqlite3.connect('vpn_manager.db')
    cursor = conn.cursor()
    cursor.execute('SELECT server_1 FROM users WHERE telegram_id = ?', (telegram_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None and result[0] == 1

# Проверка наличия пользователя на втором сервере
def is_subscribed_server_2(telegram_id) -> bool:
    conn = sqlite3.connect('vpn_manager.db')
    cursor = conn.cursor()
    cursor.execute('SELECT server_2 FROM users WHERE telegram_id = ?', (telegram_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None and result[0] == 1

# Проверка наличия пользователя на обоих серверах
def is_subscribed_both_servers (telegram_id) -> bool:
    return is_subscribed_server_1(telegram_id) and is_subscribed_server_2(telegram_id)

# Функция расчета стоимости подписки
def calculate_cost(telegram_id: int) -> float:
    conn = sqlite3.connect('vpn_manager.db')
    cursor = conn.cursor()

    # Получаем информацию о подписке пользователя
    cursor.execute('SELECT server_1, server_2 FROM users WHERE telegram_id = ?', (telegram_id,))
    result = cursor.fetchone()
    conn.close()

    if result is None:
        return 0  # Если пользователя нет в базе

    server_1_subscribed, server_2_subscribed = result

    # Подсчитываем количество подписанных пользователей на каждом сервере
    conn = sqlite3.connect('vpn_manager.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE server_1 = 1')
    server_1_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM users WHERE server_2 = 1')
    server_2_count = cursor.fetchone()[0]
    conn.close()

    # Начальная стоимость
    total_cost = 0

    # Рассчитываем стоимость для каждого сервера
    if server_1_subscribed:
        total_cost += SERVER_1_COST / server_1_count if server_1_count > 0 else SERVER_1_COST
    if server_2_subscribed:
        total_cost += SERVER_2_COST / server_2_count if server_2_count > 0 else SERVER_2_COST

    return total_cost

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = get_telegram_id(update)
    username = get_username(update)

    conn = sqlite3.connect('vpn_manager.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)',
        (telegram_id, username))
    conn.commit()
    conn.close()

    keyboard = [
        [InlineKeyboardButton("Посмотреть список пользователей", callback_data="list_users")],
    ]

    if not is_subscribed_both_servers(telegram_id):
        keyboard.append([InlineKeyboardButton("Подписаться", callback_data="subscribe")])

    if is_subscribed_server_1(telegram_id) or is_subscribed_server_2(telegram_id):
        keyboard.append([InlineKeyboardButton("Отписаться", callback_data="unsubscribe")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(
            f'Привет! Я помогу управлять вашим VPN-сервисом.\n'
            f'Выберите одну из команд:',
            reply_markup=reply_markup
        )

# Обработчик команды /cost
async def cost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    cost = calculate_cost(telegram_id)

    if cost == 0:
        await update.message.reply_text("Вы не подписаны ни на один сервер.")
    else:
        await update.message.reply_text(f"Ваша текущая стоимость подписки: {cost:.2f} рублей.")


# Обработчик подписки
async def handle_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await subscribe(update, context)

# Обработчик отписки
async def handle_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await unsubscribe(update, context)

# Обработчик списка пользователей
async def handle_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await list_users(update, context)

# Добавление пользователя с выбором сервера
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    conn = sqlite3.connect('vpn_manager.db')
    cursor = conn.cursor()

    # Получаем информацию о подписке пользователя
    cursor.execute('SELECT server_1, server_2 FROM users WHERE telegram_id = ?', (telegram_id,))
    result = cursor.fetchone()
    conn.close()

    if result is None:
        # Если пользователя нет в базе, то создаем запись
        if update.message:
            await update.message.reply_text("Вы не зарегистрированы в системе. Пожалуйста, используйте команду /start для начала.")
        return

    server_1_subscribed, server_2_subscribed = result

    # Формируем список кнопок в зависимости от состояния подписок
    keyboard = []

    if not server_1_subscribed and not server_2_subscribed:
        keyboard.append([InlineKeyboardButton(f"Подписаться на оба сервера", callback_data="add_both_servers")])
    if not server_1_subscribed:
        keyboard.append([InlineKeyboardButton(f"Подписаться на {SERVER_1_NAME}", callback_data="add_server_1")])
    if not server_2_subscribed:
        keyboard.append([InlineKeyboardButton(f"Подписаться на {SERVER_2_NAME}", callback_data="add_server_2")])

    if not keyboard:
        if update.message:
            await update.message.reply_text(f"Вы уже подписаны на оба сервера.")
        return

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(f"Выберите сервер, на который хотите подписаться:", reply_markup=reply_markup)
    else:
        # Обрабатываем случай, если сообщения нет, например, при вызове через callback
        await update.callback_query.message.reply_text(f"Выберите сервер, на который хотите подписаться:", reply_markup=reply_markup)

# Обработчик выбора сервера для подписки
async def handle_server_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id
    username = query.from_user.username or f"user_{telegram_id}"
    conn = sqlite3.connect('vpn_manager.db')
    cursor = conn.cursor()

    # Проверка на количество участников на сервере
    cursor.execute('SELECT COUNT(*) FROM users WHERE server_1 = 1')
    server_1_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM users WHERE server_2 = 1')
    server_2_count = cursor.fetchone()[0]

    if query.data == "add_server_1" and server_1_count >= 8:
        await query.edit_message_text(f"{SERVER_1_NAME} уже полностью заполнен (8 участников). Пожалуйста, выберите другой сервер.")
        conn.close()
        return
    elif query.data == "add_server_2" and server_2_count >= 8:
        await query.edit_message_text(f"{SERVER_2_NAME} уже полностью заполнен (8 участников). Пожалуйста, выберите другой сервер.")
        conn.close()
        return

    if query.data == "add_server_1":
        cursor.execute('INSERT OR IGNORE INTO users (telegram_id, username, server_1) VALUES (?, ?, ?)',
                       (telegram_id, username, True))
        cursor.execute('UPDATE users SET server_1 = 1 WHERE telegram_id = ?', (telegram_id,))
        await query.edit_message_text(f"Вы подписались на {SERVER_1_NAME}.")
    elif query.data == "add_server_2":
        cursor.execute('INSERT OR IGNORE INTO users (telegram_id, username, server_2) VALUES (?, ?, ?)',
                       (telegram_id, username, True))
        cursor.execute('UPDATE users SET server_2 = 1 WHERE telegram_id = ?', (telegram_id,))
        await query.edit_message_text(f"Вы подписались на {SERVER_2_NAME}.")
    elif query.data == "add_both_servers":
        cursor.execute('INSERT OR IGNORE INTO users (telegram_id, username, server_1, server_2) VALUES (?, ?, ?, ?)',
                       (telegram_id, username, True, True))
        cursor.execute('UPDATE users SET server_1 = 1, server_2 = 1 WHERE telegram_id = ?', (telegram_id,))
        await query.edit_message_text(f"Вы подписались на оба сервера.")

    conn.commit()
    conn.close()

# Отписка от серверов
async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    conn = sqlite3.connect('vpn_manager.db')
    cursor = conn.cursor()

    cursor.execute('SELECT server_1, server_2 FROM users WHERE telegram_id = ?', (telegram_id,))
    result = cursor.fetchone()
    conn.close()

    if result is None:
        # Если пользователя нет в базе
        if update.message:
            await update.message.reply_text("Вы не зарегистрированы в системе. Пожалуйста, используйте команду /start для начала.")
        return

    server_1_subscribed, server_2_subscribed = result

    # Формируем список кнопок для отписки
    keyboard = []

    if server_1_subscribed and server_2_subscribed:
        keyboard.append([InlineKeyboardButton(f"Отписаться от обоих серверов", callback_data="remove_both_servers")])

    if server_1_subscribed:
        keyboard.append([InlineKeyboardButton(f"Отписаться от {SERVER_1_NAME}", callback_data="remove_server_1")])
    if server_2_subscribed:
        keyboard.append([InlineKeyboardButton(f"Отписаться от {SERVER_2_NAME}", callback_data="remove_server_2")])

    # Если не подписан на оба сервера
    if not keyboard:
        if update.message:
            await update.message.reply_text(f"Вы не подписаны ни на один сервер.")
        return

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(f"Выберите сервер, от которого хотите отписаться:", reply_markup=reply_markup)
    else:
        # Обрабатываем случай, если сообщения нет
        await update.callback_query.message.reply_text(f"Выберите сервер, от которого хотите отписаться:", reply_markup=reply_markup)

# Обработчик выбора сервера для отписки
async def handle_unsubscribe_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id
    conn = sqlite3.connect('vpn_manager.db')
    cursor = conn.cursor()

    if query.data == "remove_server_1":
        cursor.execute('UPDATE users SET server_1 = 0 WHERE telegram_id = ?', (telegram_id,))
        await query.edit_message_text(f"Вы отписались от {SERVER_1_NAME}.")
    elif query.data == "remove_server_2":
        cursor.execute('UPDATE users SET server_2 = 0 WHERE telegram_id = ?', (telegram_id,))
        await query.edit_message_text(f"Вы отписались от {SERVER_2_NAME}.")
    elif query.data == "remove_both_servers":
        cursor.execute('UPDATE users SET server_1 = 0, server_2 = 0 WHERE telegram_id = ?', (telegram_id,))
        await query.edit_message_text(f"Вы отписались от обоих серверов.")

    conn.commit()
    conn.close()

# Список пользователей с указанием заполняемости серверов
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = sqlite3.connect('vpn_manager.db')
    cursor = conn.cursor()

    cursor.execute('SELECT username FROM users WHERE server_1 = 1')
    server_1_users = [f"@{u[0]}" for u in cursor.fetchall()]

    cursor.execute('SELECT username FROM users WHERE server_2 = 1')
    server_2_users = [f"@{u[0]}" for u in cursor.fetchall()]

    cursor.execute('SELECT COUNT(*) FROM users WHERE server_1 = 1')
    server_1_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM users WHERE server_2 = 1')
    server_2_count = cursor.fetchone()[0]

    conn.close()

    # Шкала заполнения серверов с использованием смайликов
    server_1_fill = "🟩" * server_1_count + "⬜️" * (8 - server_1_count)
    server_2_fill = "🟩" * server_2_count + "⬜️" * (8 - server_2_count)

    response = f"Подписаны на {SERVER_1_NAME} ({server_1_count}/8): {server_1_fill}\n"
    response += "\n".join(server_1_users) if server_1_users else "Нет пользователей."
    response += f"\n\nПодписаны на {SERVER_2_NAME} ({server_2_count}/8): {server_2_fill}\n"
    response += "\n".join(server_2_users) if server_2_users else "Нет пользователей."

    if update.message:
        await update.message.reply_text(response)
    else:
        # Обрабатываем случай, если сообщения нет
        await update.callback_query.message.reply_text(response)

# Основной блок
def main():
    # Инициализация базы данных
    init_db()

    # Создание приложения
    app = ApplicationBuilder().token(api_key).build()

    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cost", cost))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("list", list_users))
    app.add_handler(CallbackQueryHandler(handle_subscribe, pattern="^subscribe$"))
    app.add_handler(CallbackQueryHandler(handle_unsubscribe, pattern="^unsubscribe$"))
    app.add_handler(CallbackQueryHandler(handle_list_users, pattern="^list_users$"))
    app.add_handler(CallbackQueryHandler(handle_server_choice, pattern="^add_"))
    app.add_handler(CallbackQueryHandler(handle_unsubscribe_choice, pattern="^remove_"))

    # Запуск бота
    app.run_polling()

if __name__ == '__main__':
    main()
