import os
import json
import telebot
from flask import Flask, request
from tables import get_liquid_table, get_vapor_table
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота из переменных среды
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Путь к файлу базы данных
DATABASE_FILE = os.path.join(os.getcwd(), "user_data.json")
logging.info(f"Путь к файлу: {os.path.abspath(DATABASE_FILE)}")

# Словарь для хранения состояния пользователей
user_states = {}

# Загрузка данных из базы
def load_from_database():
    if not os.path.exists(DATABASE_FILE):
        logging.info("Файл базы данных не найден. Возвращаю пустой словарь.")
        return {}
    try:
        with open(DATABASE_FILE, "r", encoding="utf-8") as file:
            data = file.read()
            if not data.strip():
                logging.info("Файл базы данных пуст. Возвращаю пустой словарь.")
                return {}
            return json.loads(data)
    except json.JSONDecodeError:
        logging.error("Ошибка декодирования JSON. Возвращаю пустой словарь.")
        return {}


def save_to_database(data):
    try:
        # Проверка данных на корректность
        json.dumps(data)
        with open(DATABASE_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        logging.info("Данные успешно сохранены в базу данных.")
    except Exception as e:
        logging.error(f"Ошибка при сохранении данных: {e}")

def print_database_content():
    """
    Выводит содержимое базы данных.
    """
    try:
        with open(DATABASE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            if not data:
                return "База данных пуста."
            # Формируем строку с содержимым базы данных
            content = "Вот что мы сохранили:\n"
            for user_id, constants in data.items():
                content += f"  Пользователь ID: {user_id}\n"
                content += f"  Объем куба: {constants.get('cube_volume')} л\n"
                content += f"  Процент голов: {constants.get('head_percentage')}%\n"
                content += f"  Процент тела: {constants.get('body_percentage')}%\n"
                content += f"  Процент предхвостьев: {constants.get('pre_tail_percentage')}%\n"
                content += f"  Процент хвостов: {constants.get('tail_percentage')}%\n"
                content += f"  Средняя крепость голов: {constants.get('average_head_strength')}%\n"
            return content
    except Exception as e:
        logging.error(f"Ошибка при чтении базы данных: {e}")
        return "Не удалось прочитать базу данных."

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
    try:
        logging.info(f"Расчет содержания спирта: cube_temp={cube_temp}, vapor_temp={vapor_temp}")

        # Интерполяция для жидкости
        cube_temps = list(liquid_table.keys())
        logging.debug(f"Температуры жидкости: {cube_temps}")
        cube_temp1, cube_temp2 = find_closest_values(cube_temp, cube_temps)
        logging.debug(f"Ближайшие температуры жидкости: {cube_temp1}, {cube_temp2}")

        liquid_alcohol1 = liquid_table[cube_temp1]
        liquid_alcohol2 = liquid_table[cube_temp2]
        logging.debug(f"Содержание спирта в жидкости: {liquid_alcohol1}, {liquid_alcohol2}")

        liquid_alcohol = linear_interpolation(cube_temp, cube_temp1, cube_temp2, liquid_alcohol1, liquid_alcohol2)
        logging.debug(f"Интерполированное содержание спирта в жидкости: {liquid_alcohol}")

        # Интерполяция для пара
        vapor_temps = list(vapor_table.keys())
        logging.debug(f"Температуры пара: {vapor_temps}")
        vapor_temp1, vapor_temp2 = find_closest_values(vapor_temp, vapor_temps)
        logging.debug(f"Ближайшие температуры пара: {vapor_temp1}, {vapor_temp2}")

        vapor_alcohol1 = vapor_table[vapor_temp1]
        vapor_alcohol2 = vapor_table[vapor_temp2]
        logging.debug(f"Содержание спирта в паре: {vapor_alcohol1}, {vapor_alcohol2}")

        vapor_alcohol = linear_interpolation(vapor_temp, vapor_temp1, vapor_temp2, vapor_alcohol1, vapor_alcohol2)
        logging.debug(f"Интерполированное содержание спирта в паре: {vapor_alcohol}")

        return vapor_alcohol
    except Exception as e:
        logging.error(f"Ошибка в calculate_alcohol_content: {e}")
        raise


def correct_for_temperature(alcohol_content, distillate_temp):
    """
    Корректирует спиртуозность для приведения её к температуре 20°C.
    :param alcohol_content: Спиртуозность при текущей температуре (%).
    :param distillate_temp: Температура дистиллята (°C).
    :return: Скорректированная спиртуозность при 20°C (%).
    """
    try:
        logging.info(
            f"Корректировка спиртуозности: alcohol_content={alcohol_content}, distillate_temp={distillate_temp}")

        correction_table = {
            10: 0.6,
            15: 0.4,
            20: 0.0,
            25: -0.3,
            30: -0.6
        }
        temp_values = list(correction_table.keys())
        logging.debug(f"Температуры для коррекции: {temp_values}")
        temp1, temp2 = find_closest_values(distillate_temp, temp_values)
        logging.debug(f"Ближайшие температуры для коррекции: {temp1}, {temp2}")

        correction1 = correction_table[temp1]
        correction2 = correction_table[temp2]
        logging.debug(f"Коэффициенты коррекции: {correction1}, {correction2}")

        correction = linear_interpolation(distillate_temp, temp1, temp2, correction1, correction2)
        logging.debug(f"Интерполированный коэффициент коррекции: {correction}")

        corrected_alcohol = alcohol_content + correction
        logging.debug(f"Скорректированная спиртуозность: {corrected_alcohol}")

        return corrected_alcohol
    except Exception as e:
        logging.error(f"Ошибка в correct_for_temperature: {e}")
        raise


def calculate_fractions(user_id, total_volume_liters, alcohol_content):
    """
    Рассчитывает объемы фракций дистиллята на основе констант пользователя или значений по умолчанию.
    :param user_id: ID пользователя (строка).
    :param total_volume_liters: Общий объем спиртосодержащей смеси (л).
    :param alcohol_content: Крепость спиртосодержащей смеси (%).
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


def calculate_speed(user_id, raw_spirit_liters, user_constants):
    """
    Рассчитывает скорость отбора на основе объема куба и количества залитого спирта-сырца.
    :param user_id: ID пользователя (строка).
    :param raw_spirit_liters: Количество залитого спирта-сырца (л).
    :return: Минимальная скорость (л/ч) и максимальная скорость (л/ч).
    """
    # Преобразуем user_id в строку для работы с JSON
    user_id = str(user_id)
    constants = user_constants.get(user_id, get_default_constants())
    cube_volume = constants.get("cube_volume", 50)
    if not (20 <= cube_volume <= 100):
        raise ValueError("Объем куба вне допустимого диапазона (20–100 литров).")
    speed_coefficient = 700 if 20 <= cube_volume <= 37 else 600 if 37 < cube_volume <= 50 else 500
    speed = (raw_spirit_liters * 0.35 / speed_coefficient) * 60
    max_speed = speed * 2
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


import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)


@bot.message_handler(commands=['alcohol_calculation'])
def calculate_start(message):
    chat_id = str(message.chat.id)  # Преобразуем ID в строку для JSON
    # Логируем начало процесса расчета спиртуозности
    logging.info(f"Пользователь {chat_id} начал расчет спиртуозности.")
    # Устанавливаем состояние пользователя
    user_states[chat_id] = "awaiting_alcohol_input"
    # Отправляем сообщение пользователю
    bot.send_message(chat_id,
                     "Введите температуры куба, пара и дистиллята через пробел (например: 84.8 82.2 15):")

@bot.message_handler(commands=['fractions'])
def fractions_start(message):
    chat_id = str(message.chat.id)  # Преобразуем ID в строку для JSON
    # Логируем начало процесса расчета раздела на фракции
    logging.info(f"Пользователь {chat_id} начал расчет фракций.")
    # Устанавливаем состояние пользователя
    user_states[chat_id] = "awaiting_fractions_input"
    bot.send_message(chat_id,
                     "Введите объем спиртосодержащей смеси (л), её крепость (%) через пробел (например: 47 29):")

@bot.message_handler(commands=['speed'])
def speed_start(message):
    chat_id = str(message.chat.id)  # Преобразуем ID в строку для JSON
    # Логируем начало процесса расчета скорости отбора
    logging.info(f"Пользователь {chat_id} начал расчет скорости отбора.")
    # Устанавливаем состояние пользователя
    user_states[chat_id] = "awaiting_speed_input"
    bot.send_message(chat_id,
                     "Введите количество залитого спирта-сырца (л) (например: 47):")

@bot.message_handler(commands=['constants'])
def show_constants(message):
    """
    Показывает текущие константы пользователя.
    Если константы не установлены, используются значения по умолчанию.
    """
    chat_id = str(message.chat.id)  # Преобразуем ID в строку для JSON

    # Пытаемся получить константы пользователя или используем значения по умолчанию
    constants = user_constants.get(chat_id)

    if not constants:
        bot.send_message(chat_id, "У вас пока нет сохраненных констант. Используются стандартные значения.")
        constants = get_default_constants()

    # Формируем сообщение с текущими константами
    response = (
        f"Текущие константы:\n"
        f"Объем куба: {constants.get('cube_volume', 'Не задано')} л\n"
        f"Процент голов: {constants.get('head_percentage', 'Не задано')}%\n"
        f"Процент тела: {constants.get('body_percentage', 'Не задано')}%\n"
        f"Процент предхвостьев: {constants.get('pre_tail_percentage', 'Не задано')}%\n"
        f"Процент хвостов: {constants.get('tail_percentage', 'Не задано')}%\n"
        f"Средняя крепость голов: {constants.get('average_head_strength', 'Не задано')}%\n"
    )
    bot.send_message(chat_id, response)

@bot.message_handler(commands=['set_constants'])
def set_constants(message):
    chat_id = str(message.chat.id)  # Преобразуем ID в строку для JSON

    # Проверяем, находится ли пользователь уже в каком-либо состоянии
    if chat_id in user_states:
        bot.send_message(chat_id, "Вы уже находитесь в процессе выполнения другой команды. Завершите её или начните заново.")
        return

    # Устанавливаем состояние пользователя
    user_states[chat_id] = "awaiting_set_constants_input"
    logging.info(f"Пользователь {chat_id} начал процесс установки новых констант.")

    bot.send_message(
        chat_id,
        "Введите новые значения через пробел в формате:\n"
        "объем_куба процент_голов процент_тела процент_предхвостьев процент_хвостов средняя_крепость_голов\n"
        "Пример: 50 5 20 2 10 81.5"
    )


@bot.message_handler(commands=['report'])
def generate_report(message):
    # ID чата пользователя
    chat_id = message.chat.id
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

    # Определяем объем спиртосодержащей смеси и крепость
    total_volume_liters = cube_volume  # Предполагаем, что объем смеси равен объему куба
    alcohol_content = 29  # Крепость по умолчанию (можно сделать настраиваемой)

    # Рассчитываем объемы фракций
    fractions = calculate_fractions(chat_id, total_volume_liters, alcohol_content, user_constants)
    head_volume = fractions["heads_by_volume"]
    body_volume = fractions["body"]
    pre_tail_volume = fractions["pre_tails"]
    tail_volume = fractions["tails"]

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
    chat_id = str(message.chat.id)
    if chat_id in user_states:
        state = user_states[chat_id]
        if state == "awaiting_alcohol_input":
            try:
                logging.info(f"Обработка ввода для расчета спиртуозности: {message.text}")
                # Разбиваем ввод на значения
                cube_temp, vapor_temp, distillate_temp = map(float, message.text.replace(",", ".").split())
                # Проверяем диапазоны температур
                if not (78.15 <= cube_temp <= 100):
                    raise ValueError("Температура в кубе должна быть в диапазоне 78.15–100°C.")
                if not (78.15 <= vapor_temp <= 100):
                    raise ValueError("Температура пара должна быть в диапазоне 78.15–100°C.")
                if not (10 <= distillate_temp <= 30):
                    raise ValueError("Температура дистиллята должна быть в диапазоне 10–30°C.")

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
                fractions = calculate_fractions(chat_id, total_volume_liters, alcohol_content)
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
                # Логируем обновленные константы
                logging.info(f"Обновленные константы для chat_id {chat_id}: "
                             f"cube_volume={cube_volume}, head={head}, body={body}, "
                             f"pre_tail={pre_tail}, tail={tail}, avg_head_strength={avg_head_strength}")
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

                # Выводим сообщение об успешном обновлении констант
                bot.send_message(chat_id, "Константы успешно обновлены!")

                # Выводим содержимое базы данных
                database_content = print_database_content()
                bot.send_message(chat_id, database_content)

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