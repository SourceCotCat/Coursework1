import os
import requests
import json
import logging
import random
import shutil
from tqdm import tqdm
from dotenv import load_dotenv
from yadisk import YaDisk
from yadisk.exceptions import DirectoryExistsError
import io
from io import BytesIO

# Наши константы 
dog_api_url = 'https://dog.ceo/api'
images = "images"
json_file = "results.json"

yadisk_logger = logging.getLogger("yadisk")
yadisk_logger.setLevel(logging.WARNING)

# настройка вывода логов
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def clear_f():
    """ Очищаем папки JSON и Images """
    сhoice = input(f"Хотите очистить содержимое папки 'images' и файла 'results.json'?\n"
                   f"Введите 'yes' для подтверждения, иначе Enter: "
                   ).strip().lower()
    
    if сhoice == "yes":
        # Очищаем Images
        if os.path.exists(images): # проверяем сущ-ие указанного пути
            try:
                for folder_name in os.listdir(images):
                    folder_path = os.path.join(images, folder_name)
                    if os.path.isdir(folder_path): 
                        shutil.rmtree(folder_path)
                        logging.info(f"Папка '{folder_path}' и ее содержимое удалено")
            except Exception as e:
                logging.error(f"Ошибка при удалении папок в  {images}: {e}")
        else:
            logging.warning(f"Папка '{images}' не существует.")

        # Очищаем JSON
        if os.path.exists(json_file): # проверяем сущ-ие указанного пути\
            with open(json_file, "w", encoding="utf-8") as f:
                    f.truncate()
            logging.info(f"Файл '{json_file}' очищен.")
        else:
            logging.warning(f"Файл '{json_file}' не найден.") 


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


def download_image(url: str, breed: str) -> tuple[str, BytesIO] | None:
    """ Скачиваем изображение по url и возвращаем его имя и содержимое в виде BytesIO """
    try:
        response = requests.get(url)
        response.raise_for_status()
        file_name = f"{breed}_{url.split('/')[-1]}"
        image_data = BytesIO(response.content)
        return file_name, image_data
    except Exception as e:
        logging.error(f"Ошибка при скачивании изображения {url}: {e}")
        return None


def ensure_remote_path_exists(ya_disk: YaDisk, remote_path: str):
    """
    Рекурсивно создаёт все папки по указанному пути на Яндекс.Диске.
    """
    path_parts = remote_path.strip("/").split("/")
    current_path = ""
    for part in path_parts:
        current_path += f"/{part}"
        try:
            ya_disk.mkdir(current_path)
        except DirectoryExistsError:
            pass
        except Exception as e:
            if "Directory already exists" not in str(e):
                logging.error(f"Ошибка при создании папки {current_path}: {e}")


def upload_on_disk(ya_disk: YaDisk, image_data: BytesIO, remote_path: str):
    """ Загружает изображение из памяти (BytesIO) на Яндекс.Диск """
    try:
        ya_disk.upload(image_data, remote_path)
        # logging.info(f"Файл успешно загружен на диск: {remote_path}")
    except Exception as e:
        logging.error(f"Ошибка при загрузке файла на Яндекс.Диск: {e}")


def proc_image(breed: str, subbreeds: list[str] | None, subbreed: str | None, cnt: int | None, y_disk: YaDisk):
    res = []
    
    if subbreed:
        breed_sub = [f"{breed}/{subbreed}"]
    else:
        breed_sub = [f"{breed}/{s}" for s in subbreeds] if subbreeds else [breed]

    # Скачиваем изображения и сразу грузим на диск
    for bre in breed_sub:
        main_breed, *sub_part = bre.split("/")
        sub = sub_part[0] if sub_part else None
        image_urls = get_image(main_breed, sub)

        if not image_urls:
            logging.warning(f"Изображения для {bre} не найдены")
            continue

        if cnt:
            image_urls = image_urls[:cnt]


        remote_dir = f"/{main_breed}"
        if sub:
            remote_dir += f"/{sub}"
        # Создаём структуру папок на Яндекс.Диске
        try:
            ensure_remote_path_exists(y_disk, remote_dir)
        except Exception as e:
            if "existent directory" not in str(e):
                logging.error(f"Ошибка создания папки {remote_dir}: {e}")



        for url in tqdm(image_urls, desc=f"Скачивание {bre}"):
            downloaded = download_image(url, main_breed)
            if downloaded is None:
                continue

            file_name, image_data = downloaded


            remote_path = f"{remote_dir}/{file_name}"



            # Загружаем напрямую из памяти
            image_data.seek(0)  # Важно! Перематываем поток в начало
            upload_on_disk(y_disk, image_data, remote_path)

            # Сохраняем информацию о файле
            res.append({
                "file_name": file_name,
                "breed": main_breed,
                "subbreed": sub,
                "url": url
            })

    # Сохраняем метаданные в JSON
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=4, ensure_ascii=False)
    logging.info(f"Обновлен файл Json -> {json_file}")

def resolve_breed_subbreed(subbreed: str, all_breeds: dict[str, list[str]]) -> str | None:
    matching = [main_br for main_br, subbreeds in all_breeds.items() if subbreed in subbreeds]
    if not matching:
        logging.error(f"Подпорода {subbreed} не найдена.")
        return None
    if len(matching) > 1:
        print("Найдены следующие подпороды:")
        for i, el in enumerate(matching, start=1):
            print(f"{i}. {el}")
        choice = input("Выберите номер породы(или введите '-' для случайного выбора): ").strip()
        if choice == '-':
            breed = random.choice(matching)
            logging.info(f"Случайно выбрана порода '{breed}' для подпороды '{subbreed}'.")
        elif choice.isdigit() and 1 <= int(choice) <= len(matching):
            breed = matching[int(choice) - 1]
            logging.info(f"Выбрана порода '{breed}' для подпороды '{subbreed}'.")
        else:
            logging.error('Ошибка выбора')
            return None
    else:
        breed = matching[0]
        logging.info(f"Подпорода '{subbreed}' найдена в породе '{breed}.")
    return breed

def main():
    """ 
    Удалаем/очищаем папку 'images' и файл 'results.json в случае необходимости.
    Получаем от пользователя кол-во изображений и название породы(подпороды).
    Проверяем наличие яндекс токена.
    Получаем список пород(подпород) с Api.
    Скачиваем изображения и сохраняем локально.
    Загружаем изображения на диск.
    Сохраняем информацию в Json.

    Returns:
        None
    """ 
    clear_f()

    def get_user_input_cnt() -> int | None:
        try:
            cnt_input = input("Введите кол-во изображений для скачивания(или 'all' для всех): ").strip().lower()
            if cnt_input == "all":
                return None
            
            cnt = int(cnt_input)
            if cnt <= 0:
                logging.error("Количество изображений должно быть больше 0")
                return None
            
            return cnt
        
        except ValueError:
            logging.error("Введено некорректное значение. Введите целое число или 'all'.")
            return None
    

    def get_users_breed_subreed() -> tuple[str | None, list[str] | None, str | None]:

        breed = input("Введите название породы(или '-' если знаете только подпороду): ").strip().lower()
        subbreed = None
        subbreeds = None

        if breed == "-":
            subbreed = input("Введите название подпороды: ").strip().lower()
            if not subbreed:
                logging.error('Название подпороды не может быть пустым.')
                return None, None, None
        else:
            # получаем список подпород для введеной порды
            breeds_sub = get_breeds()
            if breed in breeds_sub:
                subbreeds = breeds_sub.get(breed, [])
            else:
                logging.error(f"Порода '{breed}' не найдена")
                return None, None, None
           
        return breed, subbreeds, subbreed


    def check_token() -> YaDisk | None:

        load_dotenv() # получаем переменную окружения 
        yandex_disk_token = os.getenv("yandex_disk_token")

        if not yandex_disk_token:
            logging.error(f"Токен не найден. Проверьте файл .env.")
            return None
        y_disk = YaDisk(token=yandex_disk_token)
        try:
            if not y_disk.check_token():
                logging.error(f"Неверный токен диска.")
                return None
            return y_disk
        except Exception as e:
            logging.error(f"Ошибка при проверке токена: {e}")
            return None

    cnt = get_user_input_cnt()
    if cnt is None:
        return 
    
    breed, subbreeds, subbreed = get_users_breed_subreed()
    if not breed and not subbreed:
        return

    y_disk = check_token()
    if not y_disk:
        return

    all_breeds = get_breeds()
    breed = resolve_breed_subbreed(subbreed, all_breeds) if subbreed else breed
    if not breed:
        logging.error("Порода не найдена.")
        return 
    
    proc_image(breed, subbreeds, subbreed, cnt, y_disk)

if __name__ == "__main__":
    main()

