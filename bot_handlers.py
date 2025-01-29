import os
import telebot
from flask import Flask, request
from calculations import calculate_alcohol_content, correct_for_temperature, calculate_fractions
from tables import get_liquid_table, get_vapor_table

# Токен бота из переменных среды
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Главное меню бота
def main_menu():
    """Возвращает главное меню бота."""
    return "Этот бот создан для расчета дробной дистилляции. Выберите функцию из списка:\n" \
           "/alcohol_calculation — Рассчитать спиртуозность дистиллята.\n" \
           "/fractions — Рассчитать объемы фракций."

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, main_menu())

# Обработчик команды /alcohol_calculation
@bot.message_handler(commands=['alcohol_calculation'])
def calculate_start(message):
    bot.send_message(message.chat.id, "Введите температуры куба, пара и дистиллята через пробел (например: 84.8 82.2 15):")

# Обработчик команды /fractions
@bot.message_handler(commands=['fractions'])
def fractions_start(message):
    bot.send_message(message.chat.id, "Введите объем спиртосодержащей смеси (л), её крепость (%) (например: 47 29):")

# Обработчик текстового ввода
@bot.message_handler(func=lambda m: True)
def handle_input(message):
    chat_id = message.chat.id

    # Проверяем состояние пользователя
    if chat_id in user_states and user_states[chat_id] == "awaiting_input":
        try:
            # Разбиваем ввод на значения
            cube_temp, vapor_temp, distillate_temp = map(float, message.text.replace(",", ".").split())

            # Получаем таблицы равновесия
            liquid_table = get_liquid_table()
            vapor_table = get_vapor_table()

            # Выполняем расчет спиртуозности
            alcohol_content = calculate_alcohol_content(cube_temp, vapor_temp, liquid_table, vapor_table)
            corrected_alcohol = correct_for_temperature(alcohol_content, distillate_temp)

            # Отправляем результат пользователю
            bot.send_message(chat_id, f"Спиртуозность при 20°C: {corrected_alcohol:.2f}%")

            # Сбрасываем состояние пользователя
            del user_states[chat_id]

        except ValueError:
            bot.send_message(chat_id, "Ошибка ввода: Введите три числа через пробел.")

        except Exception as e:
            bot.send_message(chat_id, f"Произошла ошибка: {e}")

    else:
        bot.send_message(chat_id, "Неизвестная команда. Воспользуйтесь /start для просмотра доступных

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "", 200