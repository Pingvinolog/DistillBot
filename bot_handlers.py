import os
import json
import telebot
from flask import Flask, request
from tables import get_liquid_table, get_vapor_table

# Токен бота из переменных среды
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Файл базы данных
DATABASE_FILE = "user_data.json"

# Словарь для хранения состояния пользователей
user_states = {}

# Загрузка данных из базы
def load_from_database():
    if not os.path.exists(DATABASE_FILE):
        return {}
    with open(DATABASE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

# Сохранение данных в базу
def save_to_database(data):
    with open(DATABASE_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# Глобальная переменная для хранения данных пользователей
user_constants = load_from_database()

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

# Расчеты
def linear_interpolation(x, x1, x2, y1, y2):
    """
    Выполняет линейную интерполяцию для заданных значений.
    :param x: Значение, для которого нужно интерполировать y.
    :param x1, x2: Границы интервала по x.
    :param y1, y2: Границы интервала по y.
    :return: Интерполированное значение y.
    """
    return y1 + (y2 - y1) * (x - x1) / (x2 - x1)

def find_closest_values(value, data):
    """
    Находит два ближайших значения в массиве.
    :param value: Искомое значение.
    :param data: Отсортированный массив данных.
    :return: Два ближайших значения из массива.
    """
    data = sorted(data)
    for i in range(len(data) - 1):
        if data[i] <= value <= data[i + 1]:
            return data[i], data[i + 1]
    raise ValueError("Значение вне диапазона данных.")

def calculate_alcohol_content(cube_temp, vapor_temp, liquid_table, vapor_table):
    """
    Рассчитывает содержание спирта в дистилляте.
    Учитывает зависимость пара от температуры жидкости.
    """
    cube_temps = list(liquid_table.keys())
    cube_temp1, cube_temp2 = find_closest_values(cube_temp, cube_temps)
    liquid_alcohol1 = liquid_table[cube_temp1]
    liquid_alcohol2 = liquid_table[cube_temp2]
    liquid_alcohol = linear_interpolation(cube_temp, cube_temp1, cube_temp2, liquid_alcohol1, liquid_alcohol2)

    vapor_temps = list(vapor_table.keys())
    vapor_temp1, vapor_temp2 = find_closest_values(vapor_temp, vapor_temps)
    vapor_alcohol1 = vapor_table[vapor_temp1]
    vapor_alcohol2 = vapor_table[vapor_temp2]
    vapor_alcohol = linear_interpolation(vapor_temp, vapor_temp1, vapor_temp2, vapor_alcohol1, vapor_alcohol2)

    return vapor_alcohol

def correct_for_temperature(alcohol_content, distillate_temp):
    """
    Корректирует спиртуозность для приведения её к температуре 20°C.
    :param alcohol_content: Спиртуозность при текущей температуре (%).
    :param distillate_temp: Температура дистиллята (°C).
    :return: Скорректированная спиртуозность при 20°C (%).
    """
    correction_table = {
        10: 0.6,
        15: 0.4,
        20: 0.0,
        25: -0.3,
        30: -0.6
    }
    temp_values = list(correction_table.keys())
    temp1, temp2 = find_closest_values(distillate_temp, temp_values)
    correction1 = correction_table[temp1]
    correction2 = correction_table[temp2]
    correction = linear_interpolation(distillate_temp, temp1, temp2, correction1, correction2)
    return alcohol_content + correction

def calculate_fractions(user_id, total_volume_liters, alcohol_content, user_constants):
    """
    Рассчитывает объемы фракций дистиллята на основе констант пользователя или значений по умолчанию.
    :param user_id: ID пользователя (строка).
    :param total_volume_liters: Общий объем спиртосодержащей смеси (л).
    :param alcohol_content: Крепость спиртосодержащей смеси (%).
    :param user_constants: Словарь с константами всех пользователей.
    :return: Словарь с объемами фракций.
    """
    # Преобразуем user_id в строку для работы с JSON
    user_id = str(user_id)

    # Получаем константы пользователя или используем значения по умолчанию
    constants = user_constants.get(user_id, get_default_constants())

    # Извлекаем константы
    cube_volume = constants["cube_volume"]
    head_percentage = constants["head_percentage"]
    body_percentage = constants["body_percentage"]
    pre_tail_percentage = constants["pre_tail_percentage"]
    tail_percentage = constants["tail_percentage"]
    average_head_strength = constants["average_head_strength"]

    # Переводим литры в миллилитры
    total_volume_ml = total_volume_liters * 1000
    absolute_alcohol_ml = total_volume_ml * alcohol_content / 96.6

    # Расчет объемов фракций
    heads_by_volume_ml = (total_volume_ml * head_percentage / 100)  # Процент голов от объема СС
    heads_by_alcohol_ml = absolute_alcohol_ml * (head_percentage / 100)  # Процент голов от АС
    body_ml = total_volume_ml * (body_percentage / 100)  # Процент тела от объема СС
    pre_tails_ml = total_volume_ml * (pre_tail_percentage / 100)  # Процент предхвостьев от объема СС
    tails_ml = total_volume_ml * (tail_percentage / 100)  # Процент хвостов от объема СС

    # Переводим обратно в литры
    return {
        "absolute_alcohol": absolute_alcohol_ml / 1000,
        "heads_by_volume": heads_by_volume_ml / 1000,
        "heads_by_alcohol": heads_by_alcohol_ml / 1000,
        "body": body_ml / 1000,
        "pre_tails": pre_tails_ml / 1000,
        "tails": tails_ml / 1000,
    }


def calculate_speed(user_id, raw_spirit_liters):
    """
    Рассчитывает скорость отбора на основе объема куба и количества залитого спирта-сырца.
    :param user_id: ID пользователя (строка).
    :param raw_spirit_liters: Количество залитого спирта-сырца (л).
    :return: Минимальная скорость (л/ч) и максимальная скорость (л/ч).
    """
    # Преобразуем user_id в строку для работы с JSON
    user_id = str(user_id)

    # Получаем константы пользователя или используем значения по умолчанию
    constants = user_constants.get(user_id, get_default_constants())
    cube_volume = constants.get("cube_volume", 50)  # Объем куба (по умолчанию 50 л)

    # Определяем коэффициент скорости от объема
    if 20 <= cube_volume <= 37:
        speed_coefficient = 700
    elif 37 < cube_volume <= 50:
        speed_coefficient = 600
    elif 50 < cube_volume <= 100:
        speed_coefficient = 500
    else:
        raise ValueError("Объем куба вне допустимого диапазона (20–100 литров).")

    # Выполняем расчет скорости отбора по формуле:
    speed = (raw_spirit_liters * 0.35 / speed_coefficient) * 60
    max_speed = speed * 2  # Максимальная скорость в два раза больше минимальной

    return speed, max_speed
# Расчеты

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
                     "Введите количество залитого спирта-сырца (л) (например: 47):")


@bot.message_handler(commands=['constants'])
def show_constants(message):
    chat_id = str(message.chat.id)  # Преобразуем ID в строку для JSON
    # Устанавливаем состояние пользователя
    chat_id = message.chat.id  # ID чата пользователя

    # Пытаемся получить константы пользователя или используем значения по умолчанию
    constants = user_constants.get(chat_id)
    if not constants:
        bot.send_message(chat_id, "У вас пока нет сохраненных констант. Используются стандартные значения.")
        constants = get_default_constants()
    # Формируем сообщение с текущими константами
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
def set_constants(message):
    chat_id = str(message.chat.id)  # Преобразуем ID в строку для JSON
    # Устанавливаем состояние пользователя
    user_states[message.chat.id] = "awaiting_set_constants_input"
    bot.send_message(message.chat.id,
        "Введите новые значения через пробел в формате:\n"
        "объем_куба процент_голов процент_тела процент_предхвостьев процент_хвостов средняя_крепость_голов\n"
        "Пример: 50 5 20 2 10 81.5"
    )

@bot.message_handler(commands=['report'])
def generate_report(message):
    chat_id = message.chat.id  # ID чата пользователя

    # Проверяем наличие сохраненных данных
    constants = user_constants.get(chat_id, {})
    if not constants:
        bot.send_message(chat_id, "У вас пока нет сохраненных данных для отчета.")
        return

    # Извлекаем константы
    cube_volume = constants["cube_volume"]
    head_percentage = constants["head_percentage"]
    body_percentage = constants["body_percentage"]
    pre_tail_percentage = constants["pre_tail_percentage"]
    tail_percentage = constants["tail_percentage"]
    average_head_strength = constants["average_head_strength"]

    # Рассчитываем объемы фракций
    head_volume, body_volume, pre_tail_volume, tail_volume = calculate_fractions(cube_volume, constants)

    # Рассчитываем скорость отбора
    raw_spirit_volume = cube_volume * 0.85  # Объем спирта-сырца (85% от объема куба)
    speed, max_speed = calculate_speed(chat_id, raw_spirit_volume)

    # Формируем отчет
    response = (
        f"Отчет по последнему расчету:\n"
        f"Объем куба: {cube_volume} л\n"
        f"Объем спирта-сырца: {raw_spirit_volume:.2f} л\n"
        f"Головы: {head_volume:.2f} л ({head_percentage}%)\n"
        f"Тело: {body_volume:.2f} л ({body_percentage}%)\n"
        f"Предхвостья: {pre_tail_volume:.2f} л ({pre_tail_percentage}%)\n"
        f"Хвосты: {tail_volume:.2f} л ({tail_percentage}%)\n"
        f"Средняя крепость голов: {average_head_strength}%\n"
        f"Минимальная скорость отбора: {speed:.2f} л/ч\n"
        f"Максимальная скорость отбора: {max_speed:.2f} л/ч\n"
    )

    # Отправляем отчет пользователю
    bot.send_message(chat_id, response)

@bot.message_handler(func=lambda m: True)
def handle_input(message):
    # Преобразуем ID в строку для JSON
    chat_id = str(message.chat.id)

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
                raw_spirit_liters = float(message.text.replace(",", "."))

                # Выполняем расчет скорости отбора
                speed, max_speed = calculate_speed(chat_id, raw_spirit_liters, user_constants)

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
                if not (76 <= avg_head_strength <= 95):
                    raise ValueError("Средняя крепость голов должна быть в диапазоне 76–95%.")
                user_constants[chat_id] = {
                    "cube_volume": cube_volume,
                    "head_percentage": head,
                    "body_percentage": body,
                    "pre_tail_percentage": pre_tail,
                    "tail_percentage": tail,
                    "average_head_strength": avg_head_strength,
                }
                # Сохраняем данные в файл
                save_to_database(user_constants)
                bot.send_message(chat_id, "Константы успешно обновлены!")
                # Сбрасываем состояние пользователя
                del user_states[chat_id]

            except ValueError as e:
                bot.send_message(chat_id, f"Ошибка ввода: {e}")
            except Exception as e:
                bot.send_message(chat_id, "Произошла неизвестная ошибка. Попробуйте снова.")

    else:
        bot.send_message(chat_id, "Неизвестная команда. Воспользуйтесь /start для просмотра доступных команд.")


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "", 200