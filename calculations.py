from bot_handlers import user_constants

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

def calculate_fractions(total_volume_liters, alcohol_content):
    """
    Рассчитывает объемы фракций дистиллята.
    :param total_volume_liters: Общий объем спиртосодержащей смеси (л).
    :param alcohol_content: Крепость спиртосодержащей смеси (%).
    :return: Словарь с объемами фракций.
    """
    # Переводим литры в миллилитры
    total_volume_ml = total_volume_liters * 1000
    absolute_alcohol_ml = total_volume_ml * alcohol_content / 96.6

    # Учитываем реальную крепость спирта при отборе фракций
    average_head_strength = 81.5  # Средняя крепость голов (в процентах)

    # Расчет объемов фракций
    heads_by_volume_ml = (total_volume_ml * 0.05 / average_head_strength) * 100  # 5% от объема СС
    heads_by_alcohol_ml = absolute_alcohol_ml * 0.15  # 15% от АС
    body_ml = total_volume_ml * 0.18  # 18% от объема СС
    pre_tails_ml = total_volume_ml * 0.02  # 2% от объема СС
    tails_ml = total_volume_ml * 0.10  # 10% от объема СС

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
    :param user_id: ID пользователя.
    :param raw_spirit_liters: Количество залитого спирта-сырца (л).
    :return: Минимальная скорость (л/ч) и максимальная скорость (л/ч).
    """
    # Получаем объем куба из констант пользователя
    constants = user_constants.get(user_id, {})
    cube_volume_liters = constants.get("cube_volume", 50)  # Стандартное значение: 50 л

    # Определяем коэффициент скорости от объема
    if 20 <= cube_volume_liters <= 37:
        speed_coefficient = 700
    elif 50 <= cube_volume_liters <= 70:
        speed_coefficient = 600
    elif 70 < cube_volume_liters <= 100:
        speed_coefficient = 500
    else:
        raise ValueError("Объем куба вне допустимого диапазона (20–100 литров).")

    # Корректируем скорость отбора с учетом количества залитого спирта-сырца
    spirit_ratio = raw_spirit_liters / cube_volume_liters  # Соотношение спирта к объему куба
    if spirit_ratio < 0.5:
        speed_coefficient *= 0.8  # Уменьшаем скорость, если спирта мало
    elif spirit_ratio > 1.0:
        speed_coefficient *= 1.2  # Увеличиваем скорость, если спирта много

    # Выполняем расчет скорости отбора по формуле:
    speed = (raw_spirit_liters * 0.35 / speed_coefficient) * 60
    max_speed = speed * 2  # Максимальная скорость в два раза больше минимальной

    return speed, max_speed