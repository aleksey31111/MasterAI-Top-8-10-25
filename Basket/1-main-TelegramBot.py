import telebot

# Токен вашего бота


# Создаем экземпляр класса TeleBot
bot = telebot.TeleBot(TOKEN)

# Обработчик команды '/start'
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Это простой Telegram-бот на Python.")

# Обработчик простых сообщений
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, message.text)

# Запуск бота
bot.polling(non_stop=True)

# Запуск бота
bot.polling(non_stop=True)