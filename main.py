import os
import requests
import json
import logging
from tqdm import tqdm
from dotenv import load_dotenv
from yadisk import YaDisk

dog_api_url = 'https://dog.ceo/api'
images = "images"
json_file = "result.json"


load_dotenv() # получаем переменную окружения 
yandex_disk_token = os.getenv("yandex_disk_token")

# настройка вывода логов
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_breeds() -> dict[str, list[str]]:
    """ Получаем список пород/под-пород с dog.ceo.

    Возвращает словарь, где ключами являются названия пород, а значениями - списки под-пород.
    Если не получилось сделать запрос, возвращает пустой словарь.

    Returns: Dict 
    Raises: Exception
    """ 
    response = requests.get(f"{dog_api_url}/breeds/list/all")
    if response.status_code != 200 or response.json().get("status") != "success":
        logging.error("Возникла ошибка при получении списка пород.")
        return {}
    return response.json().get("message", {})
