import os
import telebot
from flask import Flask, request

# Импортируем таблицы равновесия из отдельного файла
from tables import get_liquid_table, get_vapor_table


# Линейная интерполяция
def linear_interpolation(x, x1, x2, y1, y2):
    """
    Выполняет линейную интерполяцию для заданных значений.
    :param x: Значение, для которого нужно интерполировать y.
    :param x1, x2: Границы интервала по x.
    :param y1, y2: Границы интервала по y.
    :return: Интерполированное значение y.
    """
    return y1 + (y2 - y1) * (x - x1) / (x2 - x1)


# Поиск двух ближайших значений в массиве
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


# Коррекция спиртуозности для приведения к температуре 20°C
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


# Расчет содержания спирта в дистилляте
def calculate_alcohol_content(cube_temp, vapor_temp, liquid_table, vapor_table):
    """
    Рассчитывает содержание спирта в дистилляте на основе температуры в кубе и паровой зоне.
    :param cube_temp: Температура в перегонном кубе (°C).
    :param vapor_temp: Температура в паровой зоне (°C).
    :param liquid_table: Таблица равновесия для жидкости.
    :param vapor_table: Таблица равновесия для пара.
    :return: Содержание спирта в дистилляте (%).
    """
    # Определяем спиртуозность жидкости через интерполяцию
    cube_temps = list(liquid_table.keys())
    cube_temp1, cube_temp2 = find_closest_values(cube_temp, cube_temps)
    liquid_alcohol1 = liquid_table[cube_temp1]
    liquid_alcohol2 = liquid_table[cube_temp2]
    liquid_alcohol = linear_interpolation(cube_temp, cube_temp1, cube_temp2, liquid_alcohol1, liquid_alcohol2)

    # Определяем спиртуозность пара через интерполяцию
    vapor_temps = list(vapor_table.keys())
    vapor_temp1, vapor_temp2 = find_closest_values(vapor_temp, vapor_temps)
    vapor_alcohol1 = vapor_table[vapor_temp1]
    vapor_alcohol2 = vapor_table[vapor_temp2]
    vapor_alcohol = linear_interpolation(vapor_temp, vapor_temp1, vapor_temp2, vapor_alcohol1, vapor_alcohol2)

    return vapor_alcohol


# Расчет скорости отбора
def calculate_collection_speed(total_volume, cube_volume):
    """
    Рассчитывает рекомендуемую скорость отбора для тела.
    :param total_volume: Общий объем спиртосодержащей смеси (мл).
    :param cube_volume: Объем куба (мл).
    :return: Минимальная и максимальная скорость отбора (л/ч).
    """
    min_speed = total_volume * 0.00036  # Коэффициент для мин. скорости
    max_speed = total_volume * 0.00072  # Коэффициент для макс. скорости
    return min_speed / 1000, max_speed / 1000  # Перевод в литры


# Токен бота из переменных среды
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)


# Главное меню бота
def main_menu():
    """Возвращает главное меню бота."""
    return "Этот бот создан для расчета дробной дистилляции. Выберите функцию из списка:\n" \
           "/alcohol_calculation — Рассчитать спиртуозность дистиллята.\n" \
           "/fractions — Рассчитать объемы фракций.\n" \
           "/speed — Рассчитать скорость отбора."


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, main_menu())


# Обработчик команды /alcohol_calculation
@bot.message_handler(commands=['alcohol_calculation'])
def calculate_start(message):
    bot.send_message(message.chat.id,
                     "Введите температуры куба, пара и дистиллята через пробел (например: 84.8 82.2 15):")


# Обработчик команды /fractions
@bot.message_handler(commands=['fractions'])
def fractions_start(message):
    bot.send_message(message.chat.id,
                     "Введите объем спиртосодержащей смеси (мл), её крепость (%) и объем куба (мл), например: 47000 29 600")


# Обработчик команды /speed
@bot.message_handler(commands=['speed'])
def speed_start(message):
    bot.send_message(message.chat.id,
                     "Введите объем спиртосодержащей смеси (мл) и объем куба (мл), например: 47000 600")


# Обработчик текстового ввода
@bot.message_handler(func=lambda m: True)
def handle_input(message):
    try:
        input_values = message.text.replace(",", ".").split()

        if len(input_values) == 3:  # Расчет спиртуозности
            cube_temp, vapor_temp, distillate_temp = map(float, input_values)
            liquid_table = get_liquid_table()
            vapor_table = get_vapor_table()
            alcohol_content = calculate_alcohol_content(cube_temp, vapor_temp, liquid_table, vapor_table)
            corrected_alcohol = correct_for_temperature(alcohol_content, distillate_temp)
            bot.send_message(message.chat.id, f"Спиртуозность при 20°C: {corrected_alcohol:.2f}%")

        elif len(input_values) == 3:  # Расчет фракций
            total_volume, alcohol_content, cube_volume = map(float, input_values)
            fractions = calculate_fractions(total_volume, alcohol_content)
            min_speed, max_speed = calculate_collection_speed(total_volume, cube_volume)
            response = (
                f"Объем абсолютного спирта: {fractions['absolute_alcohol']:.2f} мл\n"
                f"Головы (по объему): {fractions['heads_by_volume']:.2f} мл\n"
                f"Головы (по АС): {fractions['heads_by_alcohol']:.2f} мл\n"
                f"Тело: {fractions['body']:.2f} мл\n"
                f"Предхвостья: {fractions['pre_tails']:.2f} мл\n"
                f"Хвосты: {fractions['tails']:.2f} мл\n"
                f"Рекомендуемая скорость отбора: {min_speed:.2f}–{max_speed:.2f} л/ч"
            )
            bot.send_message(message.chat.id, response)

        elif len(input_values) == 2:  # Расчет скорости отбора
            total_volume, cube_volume = map(float, input_values)
            min_speed, max_speed = calculate_collection_speed(total_volume, cube_volume)
            bot.send_message(message.chat.id, f"Рекомендуемая скорость отбора: {min_speed:.2f}–{max_speed:.2f} л/ч")

        else:
            raise ValueError(
                "Введите либо три числа (температуры), либо три числа (объем, крепость, объем куба), либо два числа (объем, объем куба).")

    except ValueError as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла неизвестная ошибка. Попробуйте снова.")


# Обработчик вебхука
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "", 200


# Запуск сервера
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))