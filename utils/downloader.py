import requests
from io import BytesIO
from .logger import get_log, setup_log

# константа
dog_api_url = 'https://dog.ceo/api'

setup_log()
logger = get_log(__name__)

def get_breeds() -> dict[str, list[str]]:
    """ Получаем список пород/под-пород с dog.ceo.

    Возвращает словарь, где ключами являются названия пород, а значениями - списки под-пород.
    Если не получилось сделать запрос, возвращает пустой словарь.

    Returns: Dict 
    Raises: Exception
    """ 
    response = requests.get(f"{dog_api_url}/breeds/list/all")
    if response.status_code != 200 or response.json().get("status") != "success":
        logger.error("Возникла ошибка при получении списка пород.")
        return {}
    return response.json().get("message", {})


def get_image(breed: str, subbreed: str | None = None) -> list[str]:
    """ Получаем список изображений для пород/под-пород с dog.ceo.
    Args: 
        breed (str): Название породы.
        subbreed (str | None): Название подпороды.
    Returns: list[str]: Список url-адресов изображений.
    """ 
    images = []
    breeds_d = get_breeds()

    if subbreed is None:
        response1 = requests.get(f"{dog_api_url}/breed/{breed}/images")
        if response1.status_code == 200 and response1.json().get("status") == "success":
            images.extend(response1.json().get("message", []))

        if breed in breeds_d:
            subbreeds = breeds_d.get(breed, [])
            for sub in subbreeds:
                response_sub = requests.get(f"{dog_api_url}/breed/{breed}/{sub}/images")
                if response_sub.status_code == 200 and response_sub.json().get("status") == "success":
                    images.extend(response_sub.json().get("message", []))

    else:
        br = f"{breed}/{subbreed}"
        response2 = requests.get(f"{dog_api_url}/breed/{br}/images")
        if response2.status_code == 200 and response2.json().get("status") == "success":
            images.extend(response2.json().get("message", []))
    
    return images


def download_image(url: str, breed: str) -> tuple[str, BytesIO] | None:
    """ Скачиваем изображение по url и возвращаем его имя и содержимое в виде BytesIO """
    try:
        response = requests.get(url)
        response.raise_for_status()
        file_name = f"{breed}_{url.split('/')[-1]}"
        image_data = BytesIO(response.content)
        return file_name, image_data
    except Exception as e:
        logger.error(f"Ошибка при скачивании изображения {url}: {e}")
        return None
