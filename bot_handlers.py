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
    try:
        # Определяем, какую команду выполнять
        if "/alcohol_calculation" in message.text:
            input_values = message.text.replace(",", ".").split()
            value1, value2, value3 = map(float, input_values)
            cube_temp, vapor_temp, distillate_temp = value1, value2, value3
            liquid_table = get_liquid_table()
            vapor_table = get_vapor_table()
            alcohol_content = calculate_alcohol_content(cube_temp, vapor_temp, liquid_table, vapor_table)
            corrected_alcohol = correct_for_temperature(alcohol_content, distillate_temp)
            bot.send_message(message.chat.id, f"Спиртуозность при 20°C: {corrected_alcohol:.2f}%")

        elif "/fractions" in message.text:
            input_values = message.text.replace(",", ".").split()
            value1, value2 = map(float, input_values)
            total_volume_liters, alcohol_content = value1, value2
            fractions = calculate_fractions(total_volume_liters, alcohol_content)
            response = (
                f"Объем абсолютного спирта: {fractions['absolute_alcohol']:.2f} л\n"
                f"Головы (по объему): {fractions['heads_by_volume']:.2f} л\n"
                f"Головы (по АС): {fractions['heads_by_alcohol']:.2f} л\n"
                f"Тело: {fractions['body']:.2f} л\n"
                f"Предхвостья: {fractions['pre_tails']:.2f} л\n"
                f"Хвосты: {fractions['tails']:.2f} л"
            )
            bot.send_message(message.chat.id, response)

    except ValueError as ve:
        # Обработка ошибок ввода
        bot.send_message(message.chat.id, f"Ошибка ввода: {ve}")

    except Exception as e:
        # Обработка всех остальных ошибок
        bot.send_message(message.chat.id, f"Произошла ошибка: {e}")


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "", 200