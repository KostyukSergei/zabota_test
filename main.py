import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
import requests

# Load environment variables
load_dotenv()
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for conversation history: {user_id: list of {"role": "user"|"assistant", "content": str}}
conversations = {}

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    # Reset conversation history
    conversations[user_id] = []
    
    keyboard = [[InlineKeyboardButton("Новый запрос", callback_data='new_query')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        'Привет! Я разработан для тестового задания на вакансию "Python Backend Engineer / Platform & AI".\n'
        'Для генерации используется gpt-oss:120b. Время ответа как правило до 20 секунд.\nАвтор: Костюк Сергей Олегович',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'Команды:\n/start - Начать заново и сбросить контекст.\n/help - Показать эту помощь.\n'
        'Нажми "Новый запрос" для сброса контекста.'
    )

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    message_text = update.message.text
    
    if user_id not in conversations:
        conversations[user_id] = []
    
    # Add user message to history
    conversations[user_id].append({"role": "user", "content": message_text})
    
    # Prepare data for webhook (assuming it expects {"message": str, "history": list})
    data = {
        "message": message_text,
        "history": conversations[user_id][:-1]  # Send previous history, exclude current message if needed
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=data)
        response.raise_for_status()
        bot_response = response.json().get('response', 'Ошибка: нет ответа от сервера.')
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        bot_response = 'Извини, произошла ошибка при обращении к серверу.'
    
    # Add bot response to history
    conversations[user_id].append({"role": "assistant", "content": bot_response})
    
    # Prepare inline keyboard for reset
    keyboard = [[InlineKeyboardButton("Новый запрос", callback_data='new_query')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(bot_response, reply_markup=reply_markup)

async def handle_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    
    if query.data == 'new_query':
        # Reset conversation history
        conversations[user_id] = []
        await query.answer('Контекст сброшен! Отправь новое сообщение.')
        await query.edit_message_text(text='Контекст сброшен. Начни новый запрос.')

def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()