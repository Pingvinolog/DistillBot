import os
import telebot
from flask import Flask, request


# Функция для получения таблицы равновесия жидкости
def get_liquid_table():
    """
    Таблица равновесия для жидкости: температура (°C) -> содержание спирта в жидкости (%).
    """
    return {
        78.15: 97.17,
        78.5: 93.70,
        79: 89.06,
        79.5: 83.78,
        80: 77.48,
        80.5: 72.17,
        81: 67.27,
        81.5: 61.96,
        82: 55.75,
        82.5: 50.07,
        83: 45.50,
        83.5: 42.09,
        84: 39.07,
        84.5: 35.81,
        85: 33.02,
        85.5: 30.39,
        86: 28.02,
        86.5: 25.79,
        87: 23.95,
        87.5: 22.17,
        88: 20.35,
        88.5: 18.63,
        89: 17.16,
        89.5: 15.89,
        90: 14.49,
        90.5: 13.27,
        91: 12.11,
        91.5: 11.21,
        92: 10.39,
        92.5: 9.70,
        93: 9.06,
        93.5: 8.49,
        94: 7.94,
        94.5: 7.34,
        95: 6.79,
        95.5: 6.21,
        96: 5.64,
        96.5: 5.08,
        97: 4.45,
        97.5: 3.88,
        98: 3.31,
        98.5: 2.52,
        99: 1.69,
        99.5: 0.84,
        100: 0,
    }


# Функция для получения таблицы равновесия пара
def get_vapor_table():
    """
    Таблица равновесия для пара: температура (°C) -> содержание спирта в паре (%).
    """
    return {
        78.15: 97.17,
        78.5: 94.35,
        79: 91.81,
        79.5: 89.37,
        80: 87.16,
        80.5: 85.83,
        81: 84.79,
        81.5: 83.69,
        82: 82.36,
        82.5: 81.28,
        83: 80.37,
        83.5: 79.63,
        84: 78.87,
        84.5: 77.97,
        85: 76.94,
        85.5: 75.68,
        86: 74.34,
        86.5: 72.97,
        87: 71.68,
        87.5: 70.35,
        88: 68.88,
        88.5: 67.37,
        89: 65.98,
        89.5: 64.49,
        90: 62.67,
        90.5: 60.97,
        91: 59.22,
        91.5: 57.58,
        92: 55.95,
        92.5: 54.31,
        93: 52.65,
        93.5: 51.06,
        94: 49.21,
        94.5: 46.32,
        95: 45.27,
        95.5: 42.96,
        96: 40.52,
        96.5: 37.96,
        97: 35.07,
        97.5: 31.96,
        98: 28.69,
        98.5: 23.54,
        99: 16.47,
        99.5: 8.78,
        100: 0,
    }


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
    Рассчитывает содержание спирта в дистилляте.
    Учитывает зависимость пара от температуры жидкости.
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


# Расчет объемов фракций
def calculate_fractions(total_volume, alcohol_content):
    """
    Рассчитывает объемы фракций дистиллята.
    :param total_volume: Общий объем спиртосодержащей смеси (мл).
    :param alcohol_content: Крепость спиртосодержащей смеси (%).
    :return: Словарь с объемами фракций.
    """
    absolute_alcohol = total_volume * alcohol_content / 100

    heads_by_volume = total_volume * 0.05  # 5% от объема СС
    heads_by_alcohol = absolute_alcohol * 0.15  # 15% от АС
    body = total_volume * 0.20  # 20% от объема СС
    pre_tails = total_volume * 0.02  # 2% от объема СС
    tails = total_volume * 0.10  # 10% от объема СС

    return {
        "heads_by_volume": heads_by_volume,
        "heads_by_alcohol": heads_by_alcohol,
        "body": body,
        "pre_tails": pre_tails,
        "tails": tails,
        "absolute_alcohol": absolute_alcohol,
    }


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
    bot.send_message(message.chat.id,
                     "Введите температуры куба, пара и дистиллята через пробел (например: 84.8 82.2 15):")


# Обработчик команды /fractions
@bot.message_handler(commands=['fractions'])
def fractions_start(message):
    bot.send_message(message.chat.id, "Введите объем спиртосодержащей смеси (мл) и её крепость (%), например: 47000 29")


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

        elif len(input_values) == 2:  # Расчет фракций
            total_volume, alcohol_content = map(float, input_values)
            fractions = calculate_fractions(total_volume, alcohol_content)
            response = (
                f"Объем абсолютного спирта: {fractions['absolute_alcohol']:.2f} мл\n"
                f"Головы (по объему): {fractions['heads_by_volume']:.2f} мл\n"
                f"Головы (по АС): {fractions['heads_by_alcohol']:.2f} мл\n"
                f"Тело: {fractions['body']:.2f} мл\n"
                f"Предхвостья: {fractions['pre_tails']:.2f} мл\n"
                f"Хвосты: {fractions['tails']:.2f} мл"
            )
            bot.send_message(message.chat.id, response)

        else:
            raise ValueError("Введите либо три числа (температуры), либо два числа (объем и крепость).")

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