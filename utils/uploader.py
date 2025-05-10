from yadisk import YaDisk
from yadisk.exceptions import DirectoryExistsError
from io import BytesIO
from .logger import get_log, setup_log

setup_log()
logger = get_log(__name__)

def ensure_remote_path_exists(ya_disk: YaDisk, remote_path: str):
    """ Рекурсивно создаёт все папки по указанному пути на Яндекс.Диске. """
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
                logger.error(f"Ошибка при создании папки {current_path}: {e}")


def upload_on_disk(ya_disk: YaDisk, image_data: BytesIO, remote_path: str):
    """ Загружает изображение из памяти (BytesIO) на Яндекс.Диск. """
    try:
        ya_disk.upload(image_data, remote_path)
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла на Яндекс.Диск: {e}")