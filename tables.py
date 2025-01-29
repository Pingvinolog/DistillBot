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