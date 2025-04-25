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
    Args: 
        breed (str): Название породы.
        subbreed (str | None): Название подпороды.
    Returns: list[str]: Список url-адресов изобрадений.
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

def upload_on_disk(ya_disk, local_path, remote_path):
    """ Загружаем файл на диск.

    Args:
        ya_disk (Yadisk): Объект Yadisk для работы с Api.
        local_path(str): Локальный путь к файлу.
        remote_path(str): Удаленный путь для сохранения файла .
    Returns: 
        None
    """ 
    if not os.path.exists(local_path):
        logging.error(f"Файл {local_path} не найден")

    try:
        ya_disk.upload(local_path, remote_path)
        logging.info(f"Файл {local_path} успешно загружен на диск.")
    except Exception as e:
        logging.error(f"Возникла ошибка при загрузке файла {local_path} на диск.")

def main():
    """ 
    Получаем от пользователя кол-во изображений и название породы(подпороды).
    Проверяет наличие яндекс токена.
    Получаем список пород(подпород) с Api.
    Скачиваем изображения и сохраняем локально.
    Загружаем изображения на диск.
    Сохраняем информацию в Json.

    Returns:
        None
    """ 
    try:
        cnt_input = input("Введите кол-во изображений для скачивания(или 'all' для всех): ").strip().lower()
        if cnt_input == "all":
            cnt = None
        else:
            cnt = int(cnt_input)
            if cnt < 0:
                logging.error("Количество изображений должно быть больше 0")
                return
    
    except ValueError:
        logging.error("Введено некорректное значение. Введите целое число или 'all'.")
        return
    
    breed = input("Введите название породы: ").lower()

    if not yandex_disk_token:
        logging.error(f"Токен не найден. Проверьте файл .env.")
        return 


    y_disk = YaDisk(token=yandex_disk_token)
    try:
        if not y_disk.check_token():
            logging.error(f"Неверный токен диска.")
            return 
    except Exception as e:
        logging.error(f"Ошибка при проверке токена: {e}")
        return


    all_breeds = get_breeds()
    if breed not in all_breeds:
        for main_br, subbreeds in all_breeds.items():
            if breed in subbreeds:
                logging.info(f"Подпорода {breed} не найдена в породе {main_br}.")
                breed = main_br
                break
        else:
            logging.error(f"Порода {breed} не найдена.")
            return


    res = []
    subbre = all_breeds.get(breed, [])
    breed_sub =[f"{breed}/{subbreed}" for subbreed in subbre] if subbre else [breed]

    # папки с породами 
    folder_p = os.path.join(images, breed)
    os.makedirs(folder_p, exist_ok=True)


    for bre in breed_sub:
        image_urls = get_image(*bre.split("/"))
        if not image_urls:
            logging.warning(f"изображения для {bre} не найдены")
            continue


        if cnt is not None:
            image_urls = image_urls[:cnt]

        for url in tqdm(image_urls, desc=f"Скачивание изображений для {bre}"):
            file_name = download_image(url, breed, folder_p)
            if file_name:
                res.append({"file_name": file_name})
    

    remote_folder = os.path.join("/", breed)


    try:
        y_disk.mkdir(remote_folder)
    except Exception as e:
        logging.warning(f"Папка {remote_folder} уже существует на диске.")


    for file_name in os.listdir(folder_p):
        local_path = os.path.join(folder_p, file_name)
        remote_path = os.path.join(remote_folder, file_name)
        upload_on_disk(y_disk, local_path, remote_path)
    

    json_f_p = os.path.join(os.getcwd(), json_file)
    with open(json_f_p, "w") as f:
        json.dump(res, f, indent=4)
    logging.info(f"Результат сохранен в {json_f_p}.")


if __name__ == "__main__":
    main()