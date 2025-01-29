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
    total_volume_ml = total_volume_liters * 1000  # Переводим литры в миллилитры
    absolute_alcohol = total_volume_ml * alcohol_content / 100

    heads_by_volume = total_volume_ml * 0.05  # 5% от объема СС
    heads_by_alcohol = absolute_alcohol * 0.15  # 15% от АС
    body = total_volume_ml * 0.20  # 20% от объема СС
    pre_tails = total_volume_ml * 0.02  # 2% от объема СС
    tails = total_volume_ml * 0.10  # 10% от объема СС

    return {
        "heads_by_volume": heads_by_volume / 1000,  # Переводим обратно в литры
        "heads_by_alcohol": heads_by_alcohol / 1000,
        "body": body / 1000,
        "pre_tails": pre_tails / 1000,
        "tails": tails / 1000,
        "absolute_alcohol": absolute_alcohol / 1000,
    }