import logging

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