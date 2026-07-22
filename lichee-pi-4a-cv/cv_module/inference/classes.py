"""Константы целевых классов детекции."""

ALLOWED_CLASSES = frozenset({"person", "vehicle", "fire", "smoke", "water", "no_helmet"})

CLASS_LABELS = {
    "person": "Человек",
    "vehicle": "Транспорт",
    "fire": "Огонь",
    "smoke": "Дым",
    "water": "Вода",
    "no_helmet": "Без каски",
}

CLASS_COLORS = {
    "person": (0, 200, 0),
    "vehicle": (255, 180, 0),
    "fire": (0, 80, 255),
    "smoke": (180, 180, 180),
    "water": (255, 200, 0),
    "no_helmet": (0, 0, 255),
}
