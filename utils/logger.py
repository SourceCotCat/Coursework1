import logging 
from colorlog import ColoredFormatter
from colorama import init

init()

yadisk_logger = logging.getLogger("yadisk")
yadisk_logger.setLevel(logging.WARNING)

def setup_log():
    """ Настройка вывода логов"""

    # Очищаем старые хендлеры, чтобы не было дублей
    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.handlers = []

    # Цветной формат
    formatter = ColoredFormatter(
        fmt="%(log_color)s%(asctime)s - %(levelname)s%(reset)s - %(message)s",
        log_colors={
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red'
        },
        reset=True
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO) 

    # Настройка
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # Отключаем логи модуля yandex 
    for name in ['yandex']:
        logging.getLogger(name).setLevel(logging.WARNING)


def get_log(name):
    """ Возвращает лог"""
    return logging.getLogger(name)
