import os
import json
import random
from tqdm import tqdm
from yadisk import YaDisk

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

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


def validation(input_data: str, 
               filter=None, 
               failure="Некорректный ввод. Повторите попытку.", 
               allow_empty=False) -> str:
    """Запрашивает у пользователя входные данные, то тех пор пока не будет введено нужное значение"""
    while True: 
        value = input(input_data).strip()
        if not value:
            if allow_empty:
                return ""
            else:
                logger.warning(f"Значение не может быть пустым.")
            continue
        if filter is None or filter(value):
            return value
        else:
            logger.warning(failure)

def clear_f():
    """ Очищаем папку JSON"""
    choice = validation("Очистить файл results.json? (yes/Enter): ",
                        filter=lambda x: x.strip().lower() in ("", "yes"),
                        failure="Введите yes или enter(для пропуска).",
                        allow_empty=True
                        ).strip().lower()
    
    if choice == "yes":
        # Очищаем JSON
        if os.path.exists(json_file): # проверяем сущ-ие указанного пути
            with open(json_file, "w", encoding="utf-8") as f:
                    f.truncate()
            logger.info(f"Файл '{json_file}' очищен.")
        else:
            logger.warning(f"Файл '{json_file}' не найден.") 
    else:
        logger.info(f"Очистка файла отменена.")


def build_remote_path(breed: str, subbreed: str | None) -> str:
    """
    Формирует путь для Яндекс.Диска на основе породы и подпороды.
    """
    remote_dir = f"/{breed}"
    if subbreed:
        remote_dir += f"/{subbreed}"
    return remote_dir

def create_remote_directory(y_disk: YaDisk, remote_dir: str):
    """
    Создаёт папку на Яндекс.Диске, если она ещё не существует.
    """
    try:
        ensure_remote_path_exists(y_disk, remote_dir)
    except Exception as e:
        if "existent directory" not in str(e):
            logger.error(f"Ошибка создания папки {remote_dir}: {e}")

def process_image(url: str, breed: str) -> tuple | None:
    """
    Скачивает изображение по URL и возвращает имя файла и данные.
    """
    result = download_image(url, breed)
    if result is None:
        return None
    file_name, image_data = result
    return file_name, image_data

def upload_single_image(y_disk: YaDisk, image_data, remote_path: str):
    """
    Загружает одно изображение на Яндекс.Диск.
    """
    image_data.seek(0)  # Перематываем поток в начало
    upload_on_disk(y_disk, image_data, remote_path)

def save_metadata(data: list[dict]):
    """
    Сохраняет список данных о файлах в JSON-файл.
    """
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    logger.info(f"Обновлён файл JSON -> {json_file}")

def proc_image(breed: str, subbreeds: list[str] | None, subbreed: str | None, cnt: int | None, y_disk: YaDisk):
    
    res = []

    if subbreed:
        breed_sub = [f"{breed}/{subbreed}"]
    else:
        breed_sub = [f"{breed}/{s}" for s in subbreeds] if subbreeds else [breed]

    for bre in breed_sub:
        main_breed, *sub_part = bre.split("/")
        sub = sub_part[0] if sub_part else None

        image_urls = get_image(main_breed, sub)
        if not image_urls:
            logger.warning(f"Изображения для {bre} не найдены.")
            continue

        if cnt:
            image_urls = image_urls[:cnt]

        remote_dir = build_remote_path(main_breed, sub)
        create_remote_directory(y_disk, remote_dir)

        for url in tqdm(image_urls, desc=f"Скачивание {bre}"):
            downloaded = process_image(url, main_breed)
            if downloaded is None:
                continue

            file_name, image_data = downloaded
            remote_path = f"{remote_dir}/{file_name}"

            upload_single_image(y_disk, image_data, remote_path)

            res.append({
                 "file_name": file_name,
                 "breed": main_breed,
                 "subbreed": sub,
                 "url": url
             })

    save_metadata(res)


def find_breeds_by_subbreed(subbreed: str, all_breeds: dict[str, list[str]]) -> list[str]:
    """
    Возвращает список основных пород, в которых есть указанная подпорода.
    """
    return [main_breed for main_breed, subs in all_breeds.items() if subbreed in subs]

def choose_breed_from_list(matching_breeds: list[str], subbreed: str) -> str | None:
    """
    Предлагает пользователю выбрать породу из списка, если найдено несколько вариантов.
    """
    print(f"Найдены следующие породы для подпороды '{subbreed}':")
    for i, breed in enumerate(matching_breeds, start=1):
        print(f"{i}. {breed}")

    choice = validation(
        "Выберите номер породы (или введите '-' для случайного выбора): ",
        filter=lambda x: x.isdigit() and 1 <= int(x) <= len(matching_breeds) or x.strip() == "-",
        failure=f"Введите число от 1 до {len(matching_breeds)} или '-'."
    ).strip()

    if choice == '-':
        breed = random.choice(matching_breeds)
        logger.info(f"Случайно выбрана порода '{breed}' для подпороды '{subbreed}'.")
    elif choice.isdigit() and 1 <= int(choice) <= len(matching_breeds):
        breed = matching_breeds[int(choice) - 1]
        logger.info(f"Выбрана порода '{breed}' для подпороды '{subbreed}'.")
    else:
        logger.error("Ошибка выбора.")
        return None

    return breed

def resolve_breed_subbreed(subbreed: str, all_breeds: dict[str, list[str]]) -> str | None:
    
    matching_breeds = find_breeds_by_subbreed(subbreed, all_breeds)

    if not matching_breeds:
        logger.error(f"Подпорода '{subbreed}' не найдена.")
        return None

    if len(matching_breeds) > 1:
        return choose_breed_from_list(matching_breeds, subbreed)
    else:
        breed = matching_breeds[0]
        logger.info(f"Подпорода '{subbreed}' найдена в породе '{breed}'.")
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
        def validator(valu):
            try: 
                num = int(valu)
                if num <= 0:
                    logger.warning(f"Количество изображений должно быть больше 0.")
                    return False
                return True
            except ValueError:
                if valu.lower() == "all":
                    return True
                else:
                    return False

        def cust_filter(value):
            is_v = validator(value)
            if not is_v and value.isdigit():
                return False
            return is_v

        cnt_input = validation("Введите кол-во изображений для скачивания(или 'all' для всех): ", 
                               filter=cust_filter,
                               failure="Введите целое значение или 'all'.", 
                               ).strip().lower()
        
        if cnt_input == "all":
            return None
 
        return int(cnt_input)

    def get_users_breed_subreed() -> tuple[str | None, list[str] | None, str | None]:
        """
        Получает от пользователя название породы или подпороды с автодополнением и повторным запросом при ошибке.
        Возвращает (breed, subbreeds, subbreed)
        """
        all_br = get_breeds()
        breeds_list = list(all_br.keys())
        subbreeds_list = list({sub for subs in all_br.values() for sub in subs})

        breed_completer = WordCompleter(breeds_list, ignore_case=True)
        subbreed_completer = WordCompleter(subbreeds_list, ignore_case=True)

        while True:
            breed_input = prompt(
                f"Введите породу: \n'-' если знаете только подпороду \n'?' если необходима справка \n",
                completer=breed_completer,
                complete_while_typing=True
            ).strip().lower()

            if breed_input == "?":
                print("\nДоступные породы:")
                for breed in sorted(breeds_list):
                    print(f" - {breed}")
                print()
                continue

            elif breed_input == "-":
                while True:
                    subbreed_input = prompt(
                        "Введите название подпороды: ",
                        completer=subbreed_completer,
                        complete_while_typing=True
                    ).strip().lower()

                    if not subbreed_input:
                        logger.warning("Название подпороды не может быть пустым.")
                        continue

                    if subbreed_input not in subbreeds_list:
                        logger.warning(f"Подпорода '{subbreed_input}' не найдена.")
                        continue

                    breed = resolve_breed_subbreed(subbreed_input, all_br)
                    if not breed:
                        logger.error("Не удалось определить породу для этой подпороды.")
                        continue

                    return breed, None, subbreed_input

            else:
                # Проверяем корректность породы
                if breed_input not in breeds_list:
                    logger.warning(f"Порода '{breed_input}' не найдена.")
                    continue

                # Получаем список подпород
                subbreeds = all_br.get(breed_input, [])

                # Если есть подпороды — спрашиваем, какую использовать
                if subbreeds:
                    choice = validation(
                        f"Хотите выбрать конкретную подпороду? ({', '.join(subbreeds)}) или введите 'all': ",
                        filter=lambda x: x.strip().lower() in [s.lower() for s in subbreeds + ["all"]],
                        failure=f"Введите одну из подпород или 'all'.",
                        allow_empty=False
                    ).strip().lower()

                    if choice == "all":
                        return breed_input, subbreeds, None
                    else:
                        return breed_input, None, choice
                else:
                    # Нет подпород — просто возвращаем породу
                    return breed_input, None, None
    
    
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
    
    breed, subbreeds, subbreed = get_users_breed_subreed()
    if not breed and not subbreed:
        return

    y_disk = check_token()
    if not y_disk:
        return

    get_breeds()    

    proc_image(breed, subbreeds, subbreed, cnt, y_disk)

if __name__ == "__main__":
    main()

