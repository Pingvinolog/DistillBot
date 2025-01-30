import os
import telebot
from flask import Flask, request
from calculations import calculate_alcohol_content, correct_for_temperature, calculate_fractions, calculate_speed
from tables import get_liquid_table, get_vapor_table

# Токен бота из переменных среды
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Словарь для хранения состояния пользователей
user_states = {}


def main_menu():
    """Возвращает главное меню бота."""
    return "Этот бот создан для расчета дробной дистилляции. Выберите функцию из списка:\n" \
           "/alcohol_calculation — Рассчитать спиртуозность дистиллята.\n" \
           "/fractions — Рассчитать объемы фракций.\n" \
           "/speed — Расчет скорости отбора."


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, main_menu())


@bot.message_handler(commands=['alcohol_calculation'])
def calculate_start(message):
    # Устанавливаем состояние пользователя
    user_states[message.chat.id] = "awaiting_alcohol_input"
    bot.send_message(message.chat.id,
                     "Введите температуры куба, пара и дистиллята через пробел (например: 84.8 82.2 15):")


@bot.message_handler(commands=['fractions'])
def fractions_start(message):
    # Устанавливаем состояние пользователя
    user_states[message.chat.id] = "awaiting_fractions_input"
    bot.send_message(message.chat.id,
                     "Введите объем спиртосодержащей смеси (л), её крепость (%) через пробел (например: 47 29):")

@bot.message_handler(commands=['speed'])
def speed_start(message):
    # Устанавливаем состояние пользователя
    user_states[message.chat.id] = "awaiting_speed_input"
    bot.send_message(message.chat.id,
                     "Введите объем куба (л) и количество залитого спирта-сырца (л) через пробел (например: 50 47):")

@bot.message_handler(func=lambda m: True)
def handle_input(message):
    chat_id = message.chat.id

    # Проверяем состояние пользователя
    if chat_id in user_states:
        state = user_states[chat_id]

        if state == "awaiting_alcohol_input":
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

        elif state == "awaiting_fractions_input":
            try:
                # Разбиваем ввод на значения
                total_volume_liters, alcohol_content = map(float, message.text.replace(",", ".").split())

                # Выполняем расчет фракций
                fractions = calculate_fractions(total_volume_liters, alcohol_content)
                response = (
                    f"Объем абсолютного спирта: {fractions['absolute_alcohol']:.2f} л\n"
                    f"Головы (по объему): {fractions['heads_by_volume']:.2f} л\n"
                    f"Головы (по АС): {fractions['heads_by_alcohol']:.2f} л\n"
                    f"Тело: {fractions['body']:.2f} л\n"
                    f"Предхвостья: {fractions['pre_tails']:.2f} л\n"
                    f"Хвосты: {fractions['tails']:.2f} л"
                )
                bot.send_message(chat_id, response)

                # Сбрасываем состояние пользователя
                del user_states[chat_id]

            except ValueError:
                bot.send_message(chat_id, "Ошибка ввода: Введите два числа через пробел.")

            except Exception as e:
                bot.send_message(chat_id, f"Произошла ошибка: {e}")

        elif state == "awaiting_speed_input":
            try:
                # Разбиваем ввод на значения
                cube_volume_liters, raw_spirit_liters = map(float, message.text.replace(",", ".").split())

                # Выполняем расчет скорости отбора
                speed = calculate_speed(cube_volume_liters, raw_spirit_liters)

                # Отправляем результат пользователю
                bot.send_message(chat_id, f"Скорость отбора: {speed:.2f} л/ч")

                # Сбрасываем состояние пользователя
                del user_states[chat_id]

            except ValueError:
                bot.send_message(chat_id, "Ошибка ввода: Введите два числа через пробел.")

            except Exception as e:
                bot.send_message(chat_id, f"Произошла ошибка: {e}")

    else:
        bot.send_message(chat_id, "Неизвестная команда. Воспользуйтесь /start для просмотра доступных команд.")


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "", 200