from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import sqlite3

api_key = "7699101860:AAFG2U-5n4BnCJzvuOPs1ysd0MwGefe72us"

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

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Подписаться на Server 1", callback_data="add_server_1")],
        [InlineKeyboardButton("Подписаться на Server 2", callback_data="add_server_2")],
        [InlineKeyboardButton("Подписаться на оба сервера", callback_data="add_both_servers")],
        [InlineKeyboardButton("Отписаться от серверов", callback_data="unsubscribe")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        'Привет! Я помогу управлять вашим VPN-сервисом.\n'
        'Выберите одну из команд, чтобы подписаться или отписаться от серверов.',
        reply_markup=reply_markup
    )

# Добавление пользователя с выбором сервера
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Server 1", callback_data="add_server_1")],
        [InlineKeyboardButton("Server 2", callback_data="add_server_2")],
        [InlineKeyboardButton("Both Servers", callback_data="add_both_servers")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите сервер для подписки:", reply_markup=reply_markup)

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
        await query.edit_message_text("Server 1 уже полностью заполнен (8 участников). Пожалуйста, выберите другой сервер.")
        conn.close()
        return
    elif query.data == "add_server_2" and server_2_count >= 8:
        await query.edit_message_text("Server 2 уже полностью заполнен (8 участников). Пожалуйста, выберите другой сервер.")
        conn.close()
        return

    if query.data == "add_server_1":
        cursor.execute('INSERT OR IGNORE INTO users (telegram_id, username, server_1) VALUES (?, ?, ?)',
                       (telegram_id, username, True))
        cursor.execute('UPDATE users SET server_1 = 1 WHERE telegram_id = ?', (telegram_id,))
        await query.edit_message_text("Вы подписались на Server 1.")
    elif query.data == "add_server_2":
        cursor.execute('INSERT OR IGNORE INTO users (telegram_id, username, server_2) VALUES (?, ?, ?)',
                       (telegram_id, username, True))
        cursor.execute('UPDATE users SET server_2 = 1 WHERE telegram_id = ?', (telegram_id,))
        await query.edit_message_text("Вы подписались на Server 2.")
    elif query.data == "add_both_servers":
        cursor.execute('INSERT OR IGNORE INTO users (telegram_id, username, server_1, server_2) VALUES (?, ?, ?, ?)',
                       (telegram_id, username, True, True))
        cursor.execute('UPDATE users SET server_1 = 1, server_2 = 1 WHERE telegram_id = ?', (telegram_id,))
        await query.edit_message_text("Вы подписались на оба сервера.")

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

    if not result or (not result[0] and not result[1]):
        if update.message:
            await update.message.reply_text("Вы не подписаны ни на один сервер.")
        else:
            await update.callback_query.edit_message_text("Вы не подписаны ни на один сервер.")
        return

    # Определяем доступные для отписки серверы
    keyboard = []
    if result[0]:  # Подписан на Server 1
        keyboard.append([InlineKeyboardButton("Отписаться от Server 1", callback_data="remove_server_1")])
    if result[1]:  # Подписан на Server 2
        keyboard.append([InlineKeyboardButton("Отписаться от Server 2", callback_data="remove_server_2")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("Выберите сервер, от которого хотите отписаться:", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text("Выберите сервер, от которого хотите отписаться:", reply_markup=reply_markup)

# Обработчик выбора сервера для отписки
async def handle_unsubscribe_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id
    conn = sqlite3.connect('vpn_manager.db')
    cursor = conn.cursor()

    if query.data == "remove_server_1":
        cursor.execute('UPDATE users SET server_1 = 0 WHERE telegram_id = ?', (telegram_id,))
        await query.edit_message_text("Вы отписались от Server 1.")
    elif query.data == "remove_server_2":
        cursor.execute('UPDATE users SET server_2 = 0 WHERE telegram_id = ?', (telegram_id,))
        await query.edit_message_text("Вы отписались от Server 2.")

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

    response = f"Server 1 users ({server_1_count}/8):\n"
    response += "\n".join(server_1_users) if server_1_users else "Нет пользователей."
    response += f"\n\nServer 2 users ({server_2_count}/8):\n"
    response += "\n".join(server_2_users) if server_2_users else "Нет пользователей."

    await update.message.reply_text(response)

# Основной блок
def main():
    # Инициализация базы данных
    init_db()

    # Создание приложения
    app = ApplicationBuilder().token(api_key).build()

    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("list", list_users))
    app.add_handler(CallbackQueryHandler(handle_server_choice, pattern="^add_"))
    app.add_handler(CallbackQueryHandler(handle_unsubscribe_choice, pattern="^remove_"))
    app.add_handler(CallbackQueryHandler(unsubscribe, pattern="^unsubscribe$"))

    # Запуск бота
    app.run_polling()

if __name__ == '__main__':
    main()
