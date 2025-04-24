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


def get_image(breed: str, subbreed: str | None = None) -> list[str]:
    """ Получаем список изображений для пород/под-пород с dog.ceo.

    param:
        breed (str): Название породы собак.
        subbreed: str | None = None
    Returns: 
        list[str]
    """ 
    images = []
    breeds_d = get_breeds()

    if subbreed is None:
        response1 = requests.get(f"{dog_api_url}/breed/{breed}/images")
        if response1.status_code == 200 or response1.json().get("status") == "success":
            images.extend(response1.json().get("message", []))

        if breed in breeds_d:
            subbreeds = breeds_d.get(breed, [])
            for sub in subbreeds:
                response_sub = requests.get(f"{dog_api_url}/breed/{breed}/{sub}/images")
                if response_sub.status_code == 200 or response_sub.json().get("status") == "success":
                    images.extend(response_sub.json().get("message", []))

    else:
        br = f"{breed}/{subbreed}"
        response2 = requests.get(f"{dog_api_url}/breed/{br}/images")
        if response2.status_code == 200 or response2.json().get("status") == "success":
            images.extend(response2.json().get("message", []))
    
    return images


def download_image(url: str, breed: str, folder: str) -> str | None:
    """ Скачиваем изображение по url и сохраняем локально.

    param:
        url (str): url-адрес изображения.
        breed(str): Название породы.
        folder(str): Путь к папке, в которую будет сохранено изображение.
    Returns: 
        str | None: имя файла при успешном сохранении, иначе None.
    """ 
    try:
        response = requests.get(url)
        response.raise_for_status()
        file_name = f"{breed}_{url.split('/')[-1]}"
        file_p = os.path.join(folder, file_name)
        with open(file_p, "wb") as file:
            file.write(response.content)
        return file_name
    except Exception as e:
        logging.error(f"Возникла ошибка при скачивании изображения {url}: {e}.")
        return None

