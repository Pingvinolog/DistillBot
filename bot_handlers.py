import os
import json
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
from tables import get_liquid_table, get_vapor_table
from calculations import calculate_speed, calculate_fractions, calculate_alcohol_content, correct_for_temperature
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
        "/help — Инструкция по работе с ботом.\n"
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
@bot.message_handler(commands=['help'])
def help_command(message):
    """
    Обработчик команды /help.
    Отправляет сообщение с кнопкой, ведущей на страницу описания бота.
    """
    # Создаем клавиатуру с кнопкой
    keyboard = InlineKeyboardMarkup()
    help_button = InlineKeyboardButton("Открыть инструкцию", url="https://telegra.ph/Your-Bot-Guide")
    keyboard.add(help_button)

    # Отправляем сообщение с кнопкой
    bot.send_message(
        message.chat.id,
        "Нажмите на кнопку ниже, чтобы открыть инструкцию по использованию бота.",
        reply_markup=keyboard
    )

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