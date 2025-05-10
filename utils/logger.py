import logging 

yadisk_logger = logging.getLogger("yadisk")
yadisk_logger.setLevel(logging.WARNING)

def setup_log():
    """ Настройка вывода логов"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_log(name):
    """ Возвращает лог"""
    return logging.getLogger(name)
