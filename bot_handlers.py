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

user_constants = {}

def get_default_constants():
    """
    Возвращает константы по умолчанию для нового пользователя.
    """
    return {
        "cube_volume": 50,
        "head_percentage": 5,
        "body_percentage": 18,
        "pre_tail_percentage": 2,
        "tail_percentage": 10,
        "average_head_strength": 81.5,
    }

def main_menu():
    """
    Возвращает главное меню бота с доступными командами.
    """
    return (
        "Этот бот создан для расчета дробной дистилляции. Выберите функцию из списка:\n"
        "/alcohol_calculation — Рассчитать спиртуозность дистиллята.\n"
        "/fractions — Расчет объемов фракций (головы, тело, предхвостья, хвосты).\n"
        "/speed — Расчет скорости отбора.\n"
        "/constants — Просмотр текущих констант (объем куба, проценты фракций).\n"
        "/set_constants — Установка новых значений констант.\n"
        "/report — Генерация отчета по последним расчетам.\n"
    )

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
                     "Введите количество залитого спирта-сырца (л)(например: 47):")


@bot.message_handler(commands=['constants'])
def show_constants(message):
    # Устанавливаем состояние пользователя
    user_states[message.chat.id] = "awaiting_constants_input"
    constants = user_constants.get(message.chat.id, {})
    if not constants:
        bot.send_message(message.chat.id, "У вас пока нет сохраненных констант. Используются стандартные значения.")
        constants = user_constants.get(message.chat.id, get_default_constants())  # Получаем константы пользователя или значения по умолчанию
        response = (
            f"Текущие константы:\n"
            f"Объем куба: {constants['cube_volume']} л\n"
            f"Процент голов: {constants['head_percentage']}%\n"
            f"Процент тела: {constants['body_percentage']}%\n"
            f"Процент предхвостьев: {constants['pre_tail_percentage']}%\n"
            f"Процент хвостов: {constants['tail_percentage']}%\n"
            f"Средняя крепость голов: {constants['average_head_strength']}%\n"
        )
    bot.send_message(message.chat.id, response)


@bot.message_handler(commands=['set_constants'])
def set_constants(message, update_constants):
    # Устанавливаем состояние пользователя
    user_states[message.chat.id] = "awaiting_set_constants_input"
    bot.send_message(message.chat.id,
        "Введите новые значения через пробел в формате:\n"
        "объем_куба процент_голов процент_тела процент_предхвостьев процент_хвостов средняя_крепость_голов\n"
        "Пример: 50 5 20 2 10 81.5"
    )
    bot.register_next_step_handler(message.chat.id, update_constants)

@bot.message_handler(commands=['report'])
def generate_report(message):
    # Устанавливаем состояние пользователя
    constants = user_constants.get(message.chat.id, {})
    if not constants:
        bot.send_message(message.chat.id, "У вас пока нет сохраненных данных для отчета.")
        return

    cube_volume = constants["cube_volume"]
    head_percentage = constants["head_percentage"]
    body_percentage = constants["body_percentage"]
    pre_tail_percentage = constants["pre_tail_percentage"]
    tail_percentage = constants["tail_percentage"]
    average_head_strength = constants["average_head_strength"]

    # Рассчитываем объемы фракций
    head_volume, body_volume, pre_tail_volume, tail_volume = calculate_fractions(cube_volume, constants)

    response = (
        f"Отчет по последнему расчету:\n"
        f"Объем куба: {cube_volume} л\n"
        f"Объем спирта-сырца: {cube_volume * 0.8:.2f} л\n"
        f"Головы: {head_volume:.2f} л ({head_percentage}%)\n"
        f"Тело: {body_volume:.2f} л ({body_percentage}%)\n"
        f"Предхвостья: {pre_tail_volume:.2f} л ({pre_tail_percentage}%)\n"
        f"Хвосты: {tail_volume:.2f} л ({tail_percentage}%)\n"
        f"Средняя крепость голов: {average_head_strength}%\n"
    )
    bot.send_message(message.chat.id, response)

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
                raw_spirit_liters = map(float, message.text.replace(",", ".").split())

                # Выполняем расчет скорости отбора
                speed, max_speed = calculate_speed(chat_id, raw_spirit_liters)

                # Отправляем результат пользователю
                bot.send_message(chat_id,
                                 f"Минимальная скорость отбора: {speed:.2f} л/ч \n"
                                 f"Максимальная скорость отбора: {max_speed:.2f} л/ч")

                # Сбрасываем состояние пользователя
                del user_states[chat_id]

            except ValueError:
                bot.send_message(chat_id, "Ошибка ввода: Введите два числа через пробел.")

            except Exception as e:
                bot.send_message(chat_id, f"Произошла ошибка: {e}")

        elif state == "awaiting_set_constants_input":
            try:
                update_constants = message.text.replace(",", ".").split()
                if len(update_constants) != 6:
                    raise ValueError("Неверное количество значений. Введите ровно 6 чисел.")
                cube_volume, head, body, pre_tail, tail, avg_head_strength = map(float, update_constants)
                if not (20 <= cube_volume <= 100):
                    raise ValueError("Объем куба должен быть в диапазоне 20–100 литров.")
                if not all(0 <= x <= 100 for x in [head, body, pre_tail, tail]):
                    raise ValueError("Проценты фракций должны быть в диапазоне 0–100%.")
                if not (0 <= avg_head_strength <= 100):
                    raise ValueError("Средняя крепость голов должна быть в диапазоне 0–100%.")
                user_constants[chat_id] = {
                    "cube_volume": cube_volume,
                    "head_percentage": head,
                    "body_percentage": body,
                    "pre_tail_percentage": pre_tail,
                    "tail_percentage": tail,
                    "average_head_strength": avg_head_strength,
                }
                bot.send_message(chat_id, "Константы успешно обновлены!")

            except ValueError as e:
                bot.send_message(chat_id, f"Ошибка ввода: {e}")
            except Exception as e:
                bot.send_message(chat_id, "Произошла неизвестная ошибка. Попробуйте снова.")

                # Сбрасываем состояние пользователя
                del user_states[chat_id]

    else:
        bot.send_message(chat_id, "Неизвестная команда. Воспользуйтесь /start для просмотра доступных команд.")


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "", 200