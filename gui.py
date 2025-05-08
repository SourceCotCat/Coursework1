# Импорт необходимых библиотек
import os  # Для работы с файловой системой
import sys  # Для системных функций
import threading  # Для многопоточности
import json  # Для работы с JSON
import requests  # Для HTTP-запросов
import logging  # Для логирования
import shutil  # Для работы с файлами и папками
import subprocess  # Для запуска внешних процессов
from dotenv import load_dotenv  # Для работы с .env файлами
import customtkinter as ctk  # GUI библиотека
from yadisk import YaDisk  # Для работы с Яндекс.Диском
import tkinter as tk  # Базовый GUI модуль
from tkinter import ttk, messagebox  # Виджеты и диалоговые окна
from main import proc_image, get_breeds, resolve_breed_subbreed  # Функции из main.py


ctk.set_appearance_mode("System")  # Использовать системную тему
ctk.set_default_color_theme("blue")  # Установить синюю цветовую схему

DOG_API_URL = 'https://dog.ceo/api'  # URL API для получения изображений собак
IMAGES_DIR = "images"  # Папка для сохранения изображений
JSON_FILE = "results.json"  # Файл для сохранения результатов


import tkinter as tk
from tkinter import ttk

class CTkTooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)

    def show(self, event):
        x = self.widget.winfo_pointerx() + 10
        y = self.widget.winfo_pointery() + 10
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        # стиль подсказки
        label = tk.Label(
            self.tooltip,
            text=self.text,
            bg="white",
            fg="black",
            relief="solid",
            borderwidth=1,
            padx=5,
            pady=5
        )
        label.pack()

    def hide(self, event):
        if self.tooltip:
            self.tooltip.destroy()


class BreedSelectionFrame(ctk.CTkFrame):
    """Фрейм для выбора породы и подпороды с кнопочным интерфейсом"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Настройка сетки - одна колонка с возможностью растяжения
        self.grid_columnconfigure(0, weight=1)  
        
        # Словарь для хранения пород и подпород {порода: [подпороды]}
        self.breeds_dict = {}  
        
        # Временное хранилище для выбора породы в диалоговом окне
        self.temp_selected_breed = None  
        
        # Текущая выбранная порода (None если не выбрана)
        self.selected_breed = None  
        
        # Словарь для хранения кнопок-радиокнопок
        self.radio_buttons = {}  

        # Создаем все элементы интерфейса
        self.create_widgets()  
        
        # Загружаем список пород с API
        self.fetch_breeds()  

    def create_widgets(self):
        """Создает все элементы интерфейса"""

        # заголовок для выбора породы
        ctk.CTkLabel(self, text="Выберите породу:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w")
        
        # прокручиваемая менюшка для списка пород 
        self.breeds_scroll = ctk.CTkScrollableFrame(self, height=150)
        self.breeds_scroll.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        # прокручиваемая менюшка для списка подпород как подсказка
        subbreed_hint_label = ctk.CTkLabel(self, text="Доступные подпороды:")
        subbreed_hint_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.subbreed_hint_scroll = ctk.CTkScrollableFrame(self, height=150, width=220)
        self.subbreed_hint_scroll.grid(row=1, column=1, rowspan=5, padx=5, pady=5, sticky="nsew")
            
        # поле для ввода подпороды
        ctk.CTkLabel(self, text="Введите подпороду (если нужно):").grid(
            row=2, column=0, padx=5, pady=5, sticky="w")
        
        self.subbreed_entry = ctk.CTkEntry(self)
        self.subbreed_entry.grid(row=3, column=0, padx=5, pady=5, sticky="ew")

        # поле для ввода количества изображений
        ctk.CTkLabel(self, text="Количество изображений:").grid(
            row=4, column=0, padx=5, pady=5, sticky="w")

        # рамка для размещения виджетов внутри окна 
        self.count_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.count_frame.grid(row=5, column=0, padx=5, pady=5, sticky="ew")

        # поле ввода количества (значение по умолчанию "1")
        self.count_entry = ctk.CTkEntry(self.count_frame, width=100)
        self.count_entry.insert(0, "1")
        self.count_entry.pack(side=tk.LEFT, padx=5)

        # кнопка "Все" - вставляет "all" в поле ввода
        ctk.CTkButton(
            self.count_frame,
            text="Все",
            width=50,
            fg_color="#3B82F6",
            hover_color="#2563EB",
            command=self.set_all_images  # Новый обработчик
        ).pack(side=tk.LEFT, padx=5)

        # кнопка "None" 
        self.none_button = ctk.CTkButton(
            self.breeds_scroll,
            text="None (только подпорода)",
            fg_color="#3B82F6",
            hover_color="#2563EB",
            command=lambda: self.select_breed(None)
        )
        self.none_button.pack(pady=2, padx=5, fill="x")
        self.radio_buttons[None] = self.none_button

    def get_all_subbreeds(self):
        """Возвращает список всех уникальных подпород"""
        all_subbreeds = set()
        for subbreeds in self.breeds_dict.values():
            all_subbreeds.update(subbreeds)
        return sorted(all_subbreeds)
    
    def set_all_images(self):
        """Обработчик кнопки 'Все' - вставляет 'all' в поле ввода"""
        self.count_entry.delete(0, tk.END)  # Очищаем поле
        self.count_entry.insert(0, "all")   # Вставляем текст 'all'

    def on_breed_selected(self, breed):
        """Обработчик выбора породы из списка"""
        self.selected_breed = breed  # Сохраняем выбранную породу

    def on_dialog_breed_selected(self, breed, window):
        """Обработчик выбора породы в диалоговом окне"""
        self.temp_selected_breed = breed  # Временное сохранение выбора
        window.destroy()  # Закрываем диалоговое окно

    def select_breed(self, breed):
        """Обработчик выбора породы с подсветкой активной кнопки"""
        # сбрасываем цвет всех кнопок
        for btn in self.radio_buttons.values():
            btn.configure(fg_color="#3B82F6")
        
        # устанавливаем цвет для выбранной кнопки
        if breed in self.radio_buttons:
            self.radio_buttons[breed].configure(fg_color="#1E40AF")  # Темный синий
        
        self.selected_breed = breed

    def insert_subbred(self, subbreed):
        """Вставляет подпороду в окошко"""
        self.subbreed_entry.delete(0, tk.END) # очищаем окошко
        self.subbreed_entry.insert(0, subbreed) # вставляем текст в окошко

    def fetch_breeds(self):
        """Загружает список пород и создает кнопки"""
        try:
            self.breeds_dict = get_breeds()
            
            for breed in sorted(self.breeds_dict.keys()):
                btn = ctk.CTkButton(
                    self.breeds_scroll,
                    text=breed,
                    fg_color="#3B82F6",
                    hover_color="#2563EB",
                    command=lambda b=breed: self.select_breed(b), 
                )
                btn.pack(pady=2, padx=5, fill="x")
                self.radio_buttons[breed] = btn  
            
            self.populate_subbreed_hints()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось получить список пород: {e}")


    def populate_subbreed_hints(self):
        """Заполняет справочный список всех возможных подпород с указанием их пород"""
        all_subbreeds = self.get_all_subbreeds()
        max_len=30
        if not all_subbreeds:
            ctk.CTkLabel(self.subbreed_hint_scroll, text="Нет данных", fg_color="gray30").pack(pady=2)
            return

        for sub in sorted(all_subbreeds):
            # Ищем все породы, которые содержат эту подпороду
            breeds_with_sub = [breed for breed, subbreeds in self.breeds_dict.items() if sub in subbreeds]
            breeds_str = ", ".join(breeds_with_sub)  # Преобразуем в строку для отображения
            label_text = f"{sub} ({breeds_str})"

            # сокращаем текст 
            text_short = (label_text[:max_len] + '......') if len(label_text) > max_len else label_text
            
            # создаем кликабельные кнопочки 
            bn = ctk.CTkButton(
                self.subbreed_hint_scroll,
                text=text_short,
                anchor="w",
                fg_color="transparent",
                hover_color=("gray80", "gray25"),
                text_color=("gray10", "gray90"),
                command=lambda s=sub: self.insert_subbred(s))

            bn.pack(pady=2, padx=5, fill="x")
            CTkTooltip(bn, label_text) # полный текст всплыв подсказка фун-ия 

    def get_selection(self):
        """Возвращает выбранные параметры в виде кортежа: 
        (порода, список подпород, подпорода, количество)"""
        # получаем выбранную породу
        breed = self.selected_breed  
        
        # получаем подпороду (если введена)
        subbreed = self.subbreed_entry.get().strip().lower() or None  
        
        # получаем количество (либо число, либо None если 'all')
        count_str = self.count_entry.get().lower()  
        try:
            count = None if count_str == "all" else int(count_str)
        except ValueError:
            messagebox.showerror("Ошибка", "Введите число или 'all'")
            return None, None, None, None

        # если выбрана только подпорода (breed=None)
        if not breed and subbreed:
            # ищем породы, содержащие эту подпороду
            matching = [main_br for main_br, subbreeds in self.breeds_dict.items()
                      if subbreed in subbreeds]
            
            if not matching:
                messagebox.showerror("Ошибка", f"Подпорода '{subbreed}' не найдена")
                return None, None, None, None
                
            if len(matching) > 1:
                # если подпорода есть у нескольких пород - показываем диалог выбора
                selection_window = ctk.CTkToplevel(self)
                selection_window.title("Выберите породу")
                selection_window.geometry("350x300")
                selection_window.resizable(False, False)

                scroll_frame = ctk.CTkScrollableFrame(selection_window)
                scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

                ctk.CTkLabel(scroll_frame,
                            text=f"Найдены породы для подпороды '{subbreed}':",
                            font=("Helvetica", 12)).pack(pady=10)

                # создаем кнопки для выбора породы
                for i, br in enumerate(matching, 1):
                    btn = ctk.CTkButton(
                        scroll_frame,
                        text=f"{i}. {br}",
                        fg_color="#3B82F6",
                        hover_color="#2563EB",
                        command=lambda b=br: self.on_dialog_breed_selected(b, selection_window)
                    )
                    btn.pack(pady=5, fill="x", padx=20)

                # блокируем основное окно до выбора
                selection_window.transient(self.master)
                selection_window.grab_set()
                self.wait_window(selection_window)

                if not self.temp_selected_breed:
                    return None, None, None, None
                    
                breed = self.temp_selected_breed
                self.temp_selected_breed = None
            else:
                breed = matching[0]
                
            return breed, None, subbreed, count

        # если выбрана только порода (без подпороды)
        if breed and not subbreed:
            if breed not in self.breeds_dict:
                messagebox.showerror("Ошибка", f"Порода '{breed}' не найдена")
                return None, None, None, None
                
            # возвращаем список подпород для этой породы
            subbreeds = self.breeds_dict.get(breed, [])
            return breed, subbreeds, None, count

        # если выбраны и порода и подпорода
        if breed and subbreed:
            if breed not in self.breeds_dict:
                messagebox.showerror("Ошибка", f"Порода '{breed}' не найдена")
                return None, None, None, None
                
            if subbreed not in self.breeds_dict.get(breed, []):
                messagebox.showerror("Ошибка",
                                   f"Подпорода '{subbreed}' не найдена для породы '{breed}'")
                return None, None, None, None
                
            return breed, None, subbreed, count

        # если ничего не выбрано
        messagebox.showerror("Ошибка", "Выберите хотя бы породу или подпороду")
        return None, None, None, None

class LogFrame(ctk.CTkFrame):
    """Фрейм для отображения логов"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)  # Настройка колонки
        self.log_count = 0  # Счетчик логов
        self.create_widgets()  # Создание виджетов
        self.progress = 0 # значение прогресса
        self.progress_running = False

    def create_widgets(self):
        """Создание элементов интерфейса"""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # метка для заголовка логов
        ctk.CTkLabel(header_frame,
                    text="Логи выполнения:",
                    font=("Helvetica", 12, "bold")).pack(side=tk.LEFT)


        # прогресс бар
        self.progress_bar = ctk.CTkProgressBar(self, height=20,mode="indeterninate")
        self.progress_bar.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        self.progress_bar.set(0)
        self.progress_bar.stop() # изначально скрываем

        # кнопка очистки логов
        ctk.CTkButton(header_frame,
                     text="Очистить логи",
                     width=100,
                     command=self.clear_logs).pack(side=tk.RIGHT, padx=5)

        # прокручиваемая область для логов
        self.logs_scroll = ctk.CTkScrollableFrame(self)
        self.logs_scroll.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def start_progress(self):
        """анимация бара"""
        if not self.progress_running:
            self.progress_bar.configure(mode="indeterninate")
            self.progress_bar.start()
            self.progress_running = True

    def stop_progress(self):
        """остановка анимации и скрывает бар"""
        if self.winfo_exists():
            self.progress_bar.stop()
            self.progress_bar.set(0)
            self.progress_running = False

    def update_bar(self, value):
        """обновляет бар"""
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(value)

    def add_log(self, message, level="INFO"):
        """Безопасное добавление лога"""
        if not self.winfo_exists():  # Проверяем существование виджета
            return
            
        colors = {
            "INFO": "gray70",
            "WARNING": "orange",
            "ERROR": "red",
            "SUCCESS": "green"
        }
        color = colors.get(level, "gray70")
        
        try:
            log_label = ctk.CTkLabel(
                self.logs_scroll,
                text=message,
                anchor="w",
                fg_color=("gray95", "gray20"),
                corner_radius=6,
                text_color=color,
                wraplength=600
            )
            log_label.pack(padx=5, pady=2, fill="x")
        except Exception:
            pass  # игнорируем ошибки если виджет уже уничтожен

    def clear_logs(self):
        """Очистка всех логов"""
        for widget in self.logs_scroll.winfo_children():
            widget.destroy()  # Удаляем все виджеты
        self.log_count = 0  # Сбрасываем счетчик

class App(ctk.CTk):
    """Основной класс приложения"""
    def __init__(self):
        super().__init__()
        self.title("Dog Image Downloader")  # Заголовок окна
        self.geometry("900x800")  # Размер окна
        self.resizable(False, False)  # Запрет изменения размера
        self.grid_rowconfigure(1, weight=1)  # Настройка строк
        self.grid_columnconfigure(0, weight=1)  # Настройка колонок
        self.create_menu_bar()  # Создание меню
        self.create_main_content()  # Создание основного содержимого
        
        # Создание папки для изображений, если ее нет
        if not os.path.exists(IMAGES_DIR):
            os.makedirs(IMAGES_DIR)

    def create_menu_bar(self):
        """Создание верхней панели меню"""
        menu_frame = ctk.CTkFrame(self, fg_color=("gray90", "gray20"))
        menu_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        menu_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Заголовок приложения
        ctk.CTkLabel(menu_frame,
                    text="Dog Image Downloader",
                    font=("Helvetica", 16, "bold")).grid(
                        row=0, column=0, padx=20, pady=10, sticky="w")

        # Кнопка открытия папки с фото
        ctk.CTkButton(menu_frame,
                     text="Открыть папку с фотографиями",
                     command=lambda: self.open_folder(IMAGES_DIR)).grid(
                         row=0, column=1, padx=5, pady=10)

        # Кнопка открытия файла JSON
        ctk.CTkButton(menu_frame,
                     text="Открыть папку с JSON",
                     command=lambda: self.open_folder(JSON_FILE)).grid(
                         row=0, column=2, padx=5, pady=10)

        # Выбор темы интерфейса
        ctk.CTkLabel(menu_frame, text="Тема:").grid(
            row=0, column=3, padx=5, pady=10, sticky="e")
        self.current_theme = tk.StringVar(value="System")  # Текущая тема
        ctk.CTkOptionMenu(
            menu_frame,
            values=["System", "Light", "Dark"],  # Варианты тем
            variable=self.current_theme,
            command=self.change_theme  # Обработчик изменения темы
        ).grid(row=0, column=4, padx=20, pady=10, sticky="e")

    def create_main_content(self):
        """Создание основного содержимого окна"""
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        # Фрейм для выбора породы
        selection_frame = ctk.CTkFrame(main_frame)
        selection_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        selection_frame.grid_columnconfigure(0, weight=1)

        self.breed_selection = BreedSelectionFrame(selection_frame)
        self.breed_selection.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Фрейм для кнопок
        button_frame = ctk.CTkFrame(selection_frame)
        button_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        button_frame.grid_columnconfigure((0, 1), weight=1)

        # Кнопка скачивания
        ctk.CTkButton(button_frame,
                     text="Скачать",
                     height=40,
                     font=("Helvetica", 14, "bold"),
                     fg_color="#3B82F6",
                     hover_color="#2563EB",
                     command=self.start_download).grid(
                         row=0, column=0, padx=5, pady=5, sticky="ew")

        # Кнопка очистки файлов
        ctk.CTkButton(button_frame,
                     text="Очистить файлы",
                     height=40,
                     font=("Helvetica", 14, "bold"),
                     fg_color="#F97316",
                     hover_color="#EA580C",
                     command=self.clear_files).grid(
                         row=0, column=1, padx=5, pady=5, sticky="ew")

        # Фрейм для логов
        self.log_frame = LogFrame(main_frame)
        self.log_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    def change_theme(self, new_theme):
        """Изменение темы интерфейса"""
        ctk.set_appearance_mode(new_theme)

    def clear_files(self):
        """Очистка всех файлов"""
        result = messagebox.askyesno("Подтверждение", "Удалить все скачанные файлы?")
        if result:
            try:
                # Удаление папки с изображениями
                if os.path.exists(IMAGES_DIR):
                    shutil.rmtree(IMAGES_DIR)
                    os.makedirs(IMAGES_DIR)
                # Очистка файла JSON
                if os.path.exists(JSON_FILE):
                    with open(JSON_FILE, "w", encoding="utf-8") as f:
                        f.truncate()
                self.log("Файлы очищены", "SUCCESS")
            except Exception as e:
                self.log(f"Ошибка при очистке файлов: {e}", "ERROR")

    def open_folder(self, path):
        """Открытие папки или файла"""
        try:
            if not os.path.exists(path):
                self.log(f"Файл/папка '{path}' не найдена", "WARNING")
                return
            # Для разных операционных систем
            if sys.platform == "win32":
                if os.path.isdir(path):
                    os.startfile(path)
                else:
                    os.startfile(os.path.dirname(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path if os.path.isdir(path) else os.path.dirname(path)])
            else:
                subprocess.Popen(["xdg-open", path if os.path.isdir(path) else os.path.dirname(path)])
        except Exception as e:
            self.log(f"Ошибка при открытии папки/файла: {e}", "ERROR")

    def start_download(self):
        breed, subbreeds, subbreed, count = self.breed_selection.get_selection()
        if breed is None:
            return
        
        load_dotenv()
        token = os.getenv("yandex_disk_token")
        if not token:
            messagebox.showerror("Ошибка", "Токен Яндекс.Диска не найден")
            return
        
        # запускает прогресс бар
        self.log_frame.start_progress()
        y_disk = YaDisk(token=token)

        def download_complete():
            """Безопасное завершение загрузки"""
            if self.winfo_exists():  # Проверяем существование окна
                self.log("Загрузка завершена!", "SUCCESS")
                self.after(0, self.log_frame.stop_progress)

        def thread_target():
            try:
                proc_image(breed, subbreeds, subbreed, count, y_disk)
                self.after(0, download_complete)  # Запланировать в основном потоке
            except Exception as e:
                if self.winfo_exists():
                    self.log(f"Ошибка при загрузке: {str(e)}", "ERROR")
                    self.after(0, self.log_frame.stop_progress)
                    
        thread = threading.Thread(target=thread_target, daemon=True)
        thread.start()
        
        if self.winfo_exists():  # Проверяем перед выводом лога
            self.log(
                f"Начато скачивание {count if count else 'всех'} изображений "
                f"для {'подпороды' if subbreed else 'породы'} {subbreed if subbreed else breed}...",
                "INFO"
            )

    def log(self, message, level="INFO"):
        """Добавление записи в лог"""
        self.after(0, lambda: self.log_frame.add_log(message, level))

if __name__ == "__main__":
    # Создание окна для ввода токена
    token_window = ctk.CTk()
    token_window.title("Yandex Disk Token")  # Заголовок окна
    token_window.geometry("400x250")  # Размер окна
    token_window.resizable(False, False)  # Запрет изменения размера

    # Позиционирование окна по центру экрана
    window_width = token_window.winfo_reqwidth()
    window_height = token_window.winfo_reqheight()
    position_right = int(token_window.winfo_screenwidth()/2 - window_width/2)
    position_down = int(token_window.winfo_screenheight()/2 - window_height/2)
    token_window.geometry(f"+{position_right}+{position_down}")

    # Заголовок окна
    ctk.CTkLabel(token_window,
                text="🔑 Введите токен Яндекс.Диска",
                font=("Helvetica", 20, "bold")).pack(pady=20)

    # Поле ввода токена
    token_var = tk.StringVar()  # Переменная для хранения токена
    token_entry = ctk.CTkEntry(token_window,
                              textvariable=token_var,
                              width=300,
                              show="*")  # Скрытие ввода
    token_entry.pack(pady=10)

    # Загрузка существующего токена, если есть
    load_dotenv()
    existing_token = os.getenv("yandex_disk_token")
    if existing_token:
        token_var.set(existing_token)

    # Фрейм для кнопок
    button_frame = ctk.CTkFrame(token_window, fg_color="transparent")
    button_frame.pack(pady=20)

    def verify_token():
        token = token_var.get()
        if not token:
            messagebox.showerror("Ошибка", "Введите токен")
            return
        
        try:
            y_disk = YaDisk(token=token)
            if y_disk.check_token():
                with open(".env", "w") as f:
                    f.write(f"yandex_disk_token={token}")
                
                # Правильное закрытие окна токена
                token_window.after_cancel("all")  # Отменяем все запланированные команды
                token_window.withdraw()  # Скрываем окно
                token_window.quit()  # Завершаем его mainloop
                
                # Запуск основного приложения
                app = App()
                app.mainloop()
            else:
                messagebox.showerror("Ошибка", "Неверный токен")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка проверки токена: {e}")
        finally:
            app.quit()

    # Кнопка проверки токена
    ctk.CTkButton(button_frame,
                 text="Проверить и продолжить",
                 command=verify_token).pack(side=tk.LEFT, padx=10)
    
    # Кнопка выхода
    ctk.CTkButton(button_frame,
                 text="Выход",
                 fg_color="#F97316",
                 hover_color="#EA580C",
                 command=token_window.quit).pack(side=tk.RIGHT, padx=10)

    # Запуск главного цикла
    token_window.mainloop()
