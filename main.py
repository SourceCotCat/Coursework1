import os
import json
import random
from tqdm import tqdm
from yadisk import YaDisk

from dotenv import load_dotenv
from utils.downloader import get_breeds, get_image, download_image
from utils.uploader import ensure_remote_path_exists, upload_on_disk
from utils.logger import get_log, setup_log

# константы 
dog_api_url = 'https://dog.ceo/api'   
images = "images"
json_file = "results.json"

# настраиваем логирование
setup_log()
logger = get_log(__name__)

def clear_f():
    """ Очищаем папку JSON"""
    choice = input(f"Хотите очистить содержимое файла 'results.json'?\n"
                   f"Введите 'yes' для подтверждения, иначе Enter: "
                   ).strip().lower()
    
    if choice == "yes":
        # Очищаем JSON
        if os.path.exists(json_file): # проверяем сущ-ие указанного пути
            with open(json_file, "w", encoding="utf-8") as f:
                    f.truncate()
            logger.info(f"Файл '{json_file}' очищен.")
        else:
            logger.warning(f"Файл '{json_file}' не найден.") 


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
            logger.warning(f"Изображения для {bre} не найдены")
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
                logger.error(f"Ошибка создания папки {remote_dir}: {e}")



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
    logger.info(f"Обновлен файл Json -> {json_file}")

def resolve_breed_subbreed(subbreed: str, all_breeds: dict[str, list[str]]) -> str | None:
    matching = [main_br for main_br, subbreeds in all_breeds.items() if subbreed in subbreeds]
    if not matching:
        logger.error(f"Под порода {subbreed} не найдена.")
        return None
    if len(matching) > 1:
        print("Найдены следующие подпороды:")
        for i, el in enumerate(matching, start=1):
            print(f"{i}. {el}")
        choice = input("Выберите номер породы(или введите '-' для случайного выбора): ").strip()
        if choice == '-':
            breed = random.choice(matching)
            logger.info(f"Случайно выбрана порода '{breed}' для подпороды '{subbreed}'.")
        elif choice.isdigit() and 1 <= int(choice) <= len(matching):
            breed = matching[int(choice) - 1]
            logger.info(f"Выбрана порода '{breed}' для подпороды '{subbreed}'.")
        else:
            logger.error('Ошибка выбора')
            return None
    else:
        breed = matching[0]
        logger.info(f"Подпорода '{subbreed}' найдена в породе '{breed}.")
    return breed

def main():
    """ 
    очищаем файл 'results.json в случае необходимости.
    Получаем от пользователя кол-во изображений и название породы(подпороды).
    Проверяем наличие яндекс токена.
    Получаем список пород(подпород) с Api.
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
                logger.error("Количество изображений должно быть больше 0")
                return None
            
            return cnt
        
        except ValueError:
            logger.error("Введено некорректное значение. Введите целое число или 'all'.")
            return None
    

    def get_users_breed_subreed() -> tuple[str | None, list[str] | None, str | None]:

        breed = input("Введите название породы(или '-' если знаете только подпороду): ").strip().lower()
        subbreed = None
        subbreeds = None

        if breed == "-":
            subbreed = input("Введите название подпороды: ").strip().lower()
            if not subbreed:
                logger.error('Название подпороды не может быть пустым.')
                return None, None, None
        else:
            # получаем список подпород для введённой породы
            breeds_sub = get_breeds()
            if breed in breeds_sub:
                subbreeds = breeds_sub.get(breed, [])
            else:
                logger.error(f"Порода '{breed}' не найдена")
                return None, None, None
           
        return breed, subbreeds, subbreed


    def check_token() -> YaDisk | None:

        load_dotenv() # получаем переменную окружения 
        yandex_disk_token = os.getenv("yandex_disk_token")

        if not yandex_disk_token:
            logger.error(f"Токен не найден. Проверьте файл .env.")
            return None
        y_disk = YaDisk(token=yandex_disk_token)
        try:
            if not y_disk.check_token():
                logger.error(f"Неверный токен диска.")
                return None
            return y_disk
        except Exception as e:
            logger.error(f"Ошибка при проверке токена: {e}")
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
        logger.error("Порода не найдена.")
        return 
    
    proc_image(breed, subbreeds, subbreed, cnt, y_disk)

if __name__ == "__main__":
    main()

