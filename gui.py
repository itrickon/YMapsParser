import os
import re
import time
import sv_ttk
import shutil
import asyncio
import datetime
import threading
import webbrowser
import tkinter as tk
from urllib.parse import unquote
from tkinter import ttk, messagebox
from deep_translator import GoogleTranslator
from tkinter import ttk, messagebox, filedialog, Toplevel, Text
from Main_YMaps import YMapsParse
from async_runner import AsyncParserRunner


class MainApplication(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.parent.title("YMapsParser")
        self.parent.geometry("930x700")
        self.source_file_path = "ymaps_parse_results/yandex_map_pic.xlsx"
        try:
            self.parent.iconbitmap("static/yandex_map_pic.ico")
        except Exception as e:
            print(f"Cannot load icon: {e}")

        self.interface_style()
        self.pack(fill=tk.BOTH, expand=True)
        self.create_widgets()
        self.toggle_parser_mode()

        # Для управления парсингом
        self.is_parsing = False
        self.parser_thread = None
        self.parser_instance = None

    def interface_style(self):
        sv_ttk.set_theme("light")

    def create_widgets(self):
        """Создание всех виджетов интерфейса"""
        self.top_level_menu()
        self.create_parser_controls()
        self.create_status_bar()
        self.bind_hotkeys()

    def top_level_menu(self):
        """Верхнее меню"""
        menubar = tk.Menu(self.parent)
        self.parent.config(menu=menubar)

        parse_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Парсинг", menu=parse_menu)
        parse_menu.add_command(label="Запустить парсинг", command=self.run_parsing)
        parse_menu.add_separator()
        parse_menu.add_command(label="Выход", command=self.btn_exit)

        menubar.add_command(label="Экспорт", command=self.file_to_path)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="Руководство пользователя", command=self.open_link)
        help_menu.add_command(label="Горячие клавиши", command=self.hotkeys_info)
        help_menu.add_separator()
        help_menu.add_command(label="О программе", command=self.btn_about)

    def create_parser_controls(self):
        """Создание элементов управления для парсера"""
        # Основной фрейм с grid для точного контроля
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Конфигурация grid - основной контейнер
        main_frame.grid_columnconfigure(0, weight=1)

        # Счетчик строк для grid
        row = 0

        # 1. Фрейм для выбора режима парсинга
        mode_frame = ttk.LabelFrame(main_frame, text="Режим парсинга", padding=10)
        mode_frame.grid(row=row, column=0, sticky=tk.EW, padx=10, pady=(0, 5))
        mode_frame.config(height=70)

        self.parser_mode_key = tk.StringVar(value="keyword")

        ttk.Radiobutton(mode_frame, text="Парсер по ключу",
                        variable=self.parser_mode_key,
                        value="keyword",
                        command=self.toggle_parser_mode).grid(row=0, column=0, sticky=tk.W, padx=15, pady=0)

        ttk.Radiobutton(mode_frame, text="Парсер по URL",
                        variable=self.parser_mode_key,
                        value="url",
                        command=self.toggle_parser_mode).grid(row=0, column=1, sticky=tk.W, padx=15, pady=0)

        row += 1

        # 2. Фрейм для темы парсера
        theme_frame = ttk.LabelFrame(main_frame, text="Тема парсера", padding=10)
        theme_frame.grid(row=row, column=0, sticky=tk.EW, padx=10, pady=(0, 5))
        theme_frame.config(height=70)

        self.parser_mode_t = tk.StringVar(value="tlight")

        ttk.Radiobutton(theme_frame, text="Светлая тема",
            variable=self.parser_mode_t,
            value="tlight",
            command=self.theme_parser_mode).grid(row=0, column=0, sticky=tk.W, padx=15, pady=0)

        ttk.Radiobutton(theme_frame, text="Темная тема",
            variable=self.parser_mode_t,
            value="tdark",
            command=self.theme_parser_mode).grid(row=0, column=1, sticky=tk.W, padx=15, pady=0)

        row += 1

        # 3. Фрейм для параметров парсинга
        self.params_frame = ttk.LabelFrame(main_frame, text="Параметры парсинга", padding=8)
        self.params_frame.grid(row=row, column=0, sticky=tk.EW, padx=10, pady=(0, 5))
        self.params_frame.config(height=90)

        # Создаем оба варианта параметров, но показываем только один
        self.create_keyword_params()
        self.create_url_params()

        row += 1

        # 4. Дополнительные параметры
        common_frame = ttk.LabelFrame(main_frame, text="Дополнительные параметры", padding=10)
        common_frame.grid(row=row, column=0, sticky=tk.EW, padx=10, pady=(0, 5))
        common_frame.config(height=90)

        # Содержимое common_frame
        ttk.Label(common_frame, text="Количество фирм:").grid(row=0, column=0, sticky=tk.W, pady=0)
        self.firm_count_var = tk.IntVar(value=50)
        self.firm_count_spinbox = ttk.Spinbox(common_frame, from_=1, to=1000, textvariable=self.firm_count_var, width=15)
        self.firm_count_spinbox.grid(row=0, column=1, padx=5, pady=0, sticky=tk.W)

        self.text_url_btn = ttk.Label(common_frame, text="Парсинг по URL:", width=20)
        self.text_url_btn.grid(row=1, column=0, sticky=tk.W, pady=0)

        self.generate_url_btn = ttk.Button(common_frame, text="Сгенерировать URL", command=self.generate_url, width=22)
        self.generate_url_btn.grid(row=1, column=1, sticky=tk.W, padx=5, pady=0)

        row += 1

        # 5. Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, sticky=tk.W, padx=20, pady=4)
        button_frame.config(height=40)

        ttk.Button(button_frame, text="Запустить парсинг", 
                   command=self.run_parsing, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Остановить парсинг", 
                   command=self.stop_parsing, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Очистить лог", 
                   command=self.clear_log, width=20).pack(side=tk.LEFT, padx=5)

        row += 1

        # Лог выполнения
        log_frame = ttk.LabelFrame(main_frame, text="Лог выполнения", padding=10)
        log_frame.grid(row=row, column=0, sticky=tk.NSEW, padx=10, pady=0)

        # Настраиваем вес строки для растягивания лога
        main_frame.grid_rowconfigure(row, weight=1)

        # Создаем текстовое поле для логов
        self.log_text = tk.Text(log_frame, height=20, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Добавляем раскраску вывода текста в "Лог выполнения"
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("ERROR", foreground="red")
        self.log_text.tag_config("WARNING", foreground="#cf7c00")
        self.log_text.tag_config("SUCCESS", foreground="#00a800")

        # Добавляем скроллбар
        scrollbar = ttk.Scrollbar(self.log_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)

    def create_keyword_params(self):
        """Создание элементов для парсера по ключу"""
        self.keyword_frame = ttk.Frame(self.params_frame)
        self.keyword_frame.place(x=0, y=0, relwidth=1, relheight=1)  # Занимает весь params_frame

        # Ключевое слово
        ttk.Label(self.keyword_frame, text="Ключевое слово:").grid(row=0, column=0, sticky=tk.W, pady=0)
        self.keyword_var = tk.StringVar(value="Мойка")
        self.keyword_entry = ttk.Entry(self.keyword_frame, textvariable=self.keyword_var, width=25)
        self.keyword_entry.grid(row=0, column=1, padx=5, pady=0, sticky=tk.W)

        # Город
        ttk.Label(self.keyword_frame, text="Город:").grid(row=1, column=0, sticky=tk.W, pady=0)
        self.city_var = tk.StringVar(value="Челябинск")
        self.city_entry = ttk.Entry(self.keyword_frame, textvariable=self.city_var, width=25)
        self.city_entry.grid(row=1, column=1, padx=5, pady=0, sticky=tk.W)

    def create_url_params(self):
        """Создание элементов для парсера по URL"""
        self.url_frame = ttk.Frame(self.params_frame)
        self.url_frame.place(x=0, y=0, relwidth=1, relheight=1)

        # URL для парсинга
        ttk.Label(self.url_frame, text="URL страницы 2ГИС:").grid(row=0, column=0, sticky=tk.W, pady=0)
        self.url_var = tk.StringVar(value="https://yandex.ru/maps/1/a/search/Челябинск,Мойка")
        self.url_entry = ttk.Entry(self.url_frame, textvariable=self.url_var, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=0, sticky=tk.W)

        # Пустое пространство для выравнивания
        empty_space = ttk.Frame(self.url_frame, height=30)
        empty_space.grid(row=1, column=0, columnspan=2, pady=0)

    def toggle_parser_mode(self):
        """Переключение между режимами парсинга"""
        if self.parser_mode_key.get() == "keyword":
            # Показываем параметры для парсера по ключу
            self.url_frame.place_forget()
            self.keyword_frame.place(x=0, y=0, relwidth=1, relheight=1)
            self.generate_url_btn.config(state=tk.NORMAL)
            self.status_var.set("Режим: Парсер по ключу")
        else:
            # Показываем параметры для парсера по URL
            self.keyword_frame.place_forget()
            self.url_frame.place(x=0, y=0, relwidth=1, relheight=1)
            self.generate_url_btn.config(state=tk.DISABLED)
            self.status_var.set("Режим: Парсер по URL")

    def theme_parser_mode(self):
        """Переключение между темой парсера"""
        current_geometry = self.parent.geometry()  # Сохраняем текущие размеры окна

        if self.parser_mode_t.get() == "tlight":
            sv_ttk.set_theme("light")
            self.log_text.tag_config("INFO", foreground="black")
            self.log_text.tag_config("WARNING", foreground="#cf7c00")
            self.log_text.tag_config("SUCCESS", foreground="#00a800")
            self.status_var.set("Установлена: Светлая тема")
        else:
            sv_ttk.set_theme("dark")
            self.log_text.tag_config("INFO", foreground="white")
            self.log_text.tag_config("WARNING", foreground="#ffc766")
            self.log_text.tag_config("SUCCESS", foreground="#00e600")
            self.status_var.set("Установлена: Темная тема")

        # Принудительно обновляем интерфейс
        self.parent.update_idletasks()

        # Восстанавливаем размеры окна
        self.parent.geometry(current_geometry)

    async def translate_text(self, city):
        """Переводим город на английский для удобства"""
        # Если русское слово - переводим
        self.translator = GoogleTranslator(source="ru", target="en")
        a = await asyncio.to_thread(self.translator.translate, city)
        a = "-".join(a.split())
        return a.lower()

    def generate_url(self):
        """Генерация URL на основе ключевого слова и города"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        keyword = self.keyword_var.get().strip()
        city = loop.run_until_complete(self.translate_text(self.city_var.get().strip()))

        if not keyword or not city:
            messagebox.showwarning("Предупреждение", "Введите ключевое слово и город!")
            return

        generated_url = f"https://yandex.ru/maps/1/a/search/{city},{keyword}"

        self.url_var.set(generated_url)

        # Предлагаем переключиться на режим по URL
        if messagebox.askyesno(
            "URL сгенерирован",
            f"URL успешно сгенерирован:\n{generated_url}\n\n"
            f"Хотите переключиться на парсер по URL?",):
            self.parser_mode_key.set("url")
            self.toggle_parser_mode()
        self.status_var.set("URL сгенерирован")

    def run_parsing(self):
        """Запуск парсинга в зависимости от выбранного режима"""
        if self.is_parsing:
            messagebox.showwarning("Предупреждение", "Парсинг уже выполняется!")
            return
        self.is_parsing = True
        if self.parser_mode_key.get() == "keyword":
            self.run_keyword_parsing()
        else:
            self.run_url_parsing()

    def run_keyword_parsing(self):
        """Запуск парсинга по ключу"""
        keyword = self.keyword_var.get()
        city = self.city_var.get()
        firm_count = self.firm_count_var.get()

        if not keyword or not city:
            messagebox.showwarning("Предупреждение", "Заполните все поля!")
            return
        right_city = re.sub(r"[^а-яА-Яa-zA-Z\s]", "", city).strip()
        self.log_message(f"Начало парсинга по ключу: '{keyword}' в {right_city}, количество: {firm_count}")
        self.status_var.set(f"Парсинг по ключу: {keyword} в {city}")

        # Запуск асинхронного парсинга в отдельном потоке
        self.is_parsing = True
        self.parser_instance = YMapsParse(keyword, city, firm_count, gui_url_work=False)
        self.parser_thread = threading.Thread(
            target=self.run_async_parsing, args=(self.parser_instance,), daemon=True)
        self.parser_thread.start()

    def run_url_parsing(self):
        """Запуск парсинга по URL - извлекаем город и ключ из URL"""
        url = self.url_var.get()
        firm_count = self.firm_count_var.get()
        print(url)
        if not url:
            messagebox.showwarning("Предупреждение", "Введите URL для парсинга!")
            return

        # Проверяем, что это URL 2ГИС
        if not url.startswith(("https://yandex.ru/", "http://yandex.ru/")):
            self.is_parsing = False
            messagebox.showwarning("Предупреждение", "Введите корректный URL 2ГИС!")
            return

        try:
            # Извлекаем город и ключевое слово из URL
            pattern = r"https?://yandex\.ru/maps/\d+/\w+/search/([^,]+),(.+)"
            match = re.search(pattern, url)

            if match:
                city_code = match.group(1)
                keyword = match.group(2)

                keyword = unquote(keyword)

                self.log_message(f"Парсинг по URL: {url}")
                self.status_var.set(f"Парсинг по URL: {url}")
                # Запускаем парсинг так же, как для ключа
                self.is_parsing = True
                self.parser_instance = YMapsParse(url, city_code, firm_count, gui_url_work=True)
                self.parser_thread = threading.Thread(
                    target=self.run_async_parsing,
                    args=(self.parser_instance,),
                    daemon=True,
                )
                self.parser_thread.start()
            else:
                self.is_parsing = False
                messagebox.showwarning(
                    "Ошибка",
                    "Не удалось извлечь данные из URL. Проверьте формат URL!"
                )

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка парсинга по URL: {str(e)}")

    def run_async_parsing(self, parser_instance):
        """Запуск асинхронного парсинга в отдельном потоке"""
        try:
            # Создаем и запускаем runner
            runner = AsyncParserRunner(
                parser_instance,
                update_callback=self.update_gui_from_thread,
                completion_callback=self.on_parsing_complete,
            )
            self.parser_thread = runner.start()

        except Exception as e:
            self.update_gui_from_thread(f"Ошибка запуска: {str(e)}")
            self.is_parsing = False

    def on_parsing_complete(self, flag=True):
        """Вызывается при завершении парсинга (успешном или с ошибкой)"""

        def update():
            self.is_parsing = False
            if flag:
                self.status_var.set("Парсинг успешно завершен")
                self.log_message("Парсинг успешно завершен")
            else:
                self.status_var.set("Парсинг остановлен")
                self.log_message("Парсинг остановлен")

        # Выполняем в основном потоке GUI
        self.after(0, update)

    def update_gui_from_thread(self, message):
        """Обновление GUI из потока"""

        def update():
            self.log_message(message)
            self.status_var.set(message[:50] + "..." if len(message) > 50 else message)

        self.after(0, update)

    def stop_parsing(self):
        """Остановка парсинга"""
        if not self.is_parsing:
            self.log_message("Парсинг не выполняется!")
            self.status_var.set("Парсинг не выполняется!")
            return

        # Закрытие страницы в отдельном потоке
        time.sleep(1)
        if hasattr(self, "parser_instance"):
            threading.Thread(target=lambda: (
                    asyncio.run(self.parser_instance.page.close())
                    if hasattr(self.parser_instance, "page")
                    else None
                ),
                daemon=True,
            ).start()

        self.is_parsing = False
        self.status_var.set("Парсинг остановлен")
        self.log_message("Парсинг остановлен пользователем")

    def clear_log(self):
        """Очистка лога"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("Лог очищен")
        self.status_var.set("Лог очищен")

    def log_message(self, message):
        """Добавление сообщения в лог с цветами"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        message = str(message)
        # Определяем уровень
        msg_lower = message.lower()
        error_words = ["ошибка", "error", "closed", "exception", "failed", "прервано"]
        warning_words = ["предупреждение", "warning", "внимание", "остановлен"]
        success_words = ["успешно", "success", "завершен", "готово"]

        if any(word in msg_lower for word in error_words):
            level = "ERROR"
        elif any(word in msg_lower for word in warning_words):
            level = "WARNING"
        elif any(word in msg_lower for word in success_words):
            level = "SUCCESS"
        else:
            level = "INFO"

        formatted_message = f"[{timestamp}] [{level}] {message}\n"

        # Вставляем с тегом
        self.log_text.insert(tk.END, formatted_message, (level,))
        self.log_text.see(tk.END)

    def user_manual(self):
        """Обработчик кнопки 'Руководство пользователя'"""
        # Создаем собственное окно вместо messagebox
        top = Toplevel()
        top.title("Руководство пользователя")

        # Создаем Frame для размещения текстового виджета и скроллбара
        frame = tk.Frame(top)
        frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Создаем текстовое поле
        text_widget = Text(frame, wrap=tk.WORD, width=61, height=20, font=("Arial", 10))

        top.resizable(False, False)

        # Добавляем остальной текст
        user_manual_text = [
            "     Руководство пользователя\n",
            "  1. Выберите режим парсинга:\n",
            "   • Парсер по ключу - поиск по ключевому слову и городу\n",
            "   • Парсер по URL - парсинг конкретной страницы 2ГИС\n\n",
            "  2. Заполните параметры:\n",
            "   • Для парсера по ключу: ключевое слово и город\n",
            "   • Для парсера по URL: вставьте URL страницы\n",
            "   • Укажите количество фирм для парсинга\n\n",
            "  3. Дополнительные параметры:\n",
            "   • Для парсера по ключу: кнопка 'Сгенерировать URL'\n",
            "  4. Нажмите 'Запустить парсинг'\n\n",
            "  Примечания:\n",
            "    • Парсинг выполняется асинхронно - интерфейс не блокируется\n",
            "    • Результаты сохраняются в папке 2gis_parse_results/twogis_data.xlsx\n",
            "    • Для работы требуется установленный Playwright\n",
            "    • Можно остановить парсинг в любой момент\n",
        ]

        for city_text in user_manual_text:
            text_widget.insert(tk.END, city_text)

        text_widget.configure(state="disabled")  # Только для чтения

        # Кнопка закрытия
        button = tk.Button(top, text="Закрыть", command=top.destroy)

        text_widget.pack()
        button.pack(pady=10)

        # Центрируем окно
        top.update_idletasks()
        width = top.winfo_width()
        height = top.winfo_height()
        x = (top.winfo_screenwidth() // 2) - (width // 2)
        y = (top.winfo_screenheight() // 2) - (height // 2)
        top.geometry(f"{width}x{height}+{x}+{y}")

    def hotkeys_info(self):
        """Обработчик кнопки 'Горячие клавиши'"""
        # Создаем собственное окно вместо messagebox
        top = Toplevel()
        top.title("Горячие клавиши")

        # Создаем Frame для размещения текстового виджета и скроллбара
        frame = tk.Frame(top)
        frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Создаем текстовое поле
        text_widget = Text(frame, wrap=tk.WORD, width=60, height=12, font=("Arial", 10))

        top.resizable(False, False)

        # Добавляем остальной текст
        cities = [
            "       Горячие клавиши приложения:\n",
            "   Основные операции:\n",
            "     • Ctrl + R   - Запустить парсинг\n",
            "     • Ctrl + S   - Остановить парсинг\n",
            "     • Ctrl + L    - Очистить лог\n",
            "     • Ctrl + Q   - Выйти из приложения\n",
            "   Дополнительные:\n",
            "     • Ctrl + G - Сгенерировать URL (в режиме по ключу)\n",
            "     • F1         - Руководство пользователя\n",
            "     • Enter     - Запустить парсинг (когда курсор в поле ввода)\n",
            "   Сочетания клавиш работают в любом месте приложения.\n",
        ]

        for city_text in cities:
            text_widget.insert(tk.END, city_text)

        text_widget.configure(state="disabled")  # Только для чтения

        # Кнопка закрытия
        button = tk.Button(top, text="Закрыть", command=top.destroy)

        text_widget.pack()
        button.pack(pady=10)

        # Центрируем окно
        top.update_idletasks()
        width = top.winfo_width()
        height = top.winfo_height()
        x = (top.winfo_screenwidth() // 2) - (width // 2)
        y = (top.winfo_screenheight() // 2) - (height // 2)
        top.geometry(f"{width}x{height}+{x}+{y}")

    def file_to_path(self):
        """Копирование конкретного файла в выбранную папку"""
        file_path = self.source_file_path
        if not os.path.exists(file_path):
            self.log_message("Ошибка экспорта объявлений! Исходный файл не найден.")
            self.status_var.set("Исходный файл не найден.")
            return
        
        target_folder = filedialog.askdirectory(title="Выберите папку для копирования файла")
        
        if not target_folder:
            return
        
        try:
            filename = os.path.basename(file_path)
            target_path = os.path.join(target_folder, filename)
            
            # Проверка на существование
            if os.path.exists(target_path):
                overwrite = messagebox.askyesno(
                    "Подтверждение",
                    f"Файл '{filename}' уже существует. Заменить?"
                )
                if not overwrite:
                    return
            
            shutil.copy2(file_path, target_path)
            
            self.log_message(f"Успех! Файл '{filename}' успешно скопирован в:\n{target_folder}")
            self.status_var.set(f"Файл '{filename}' успешно скопирован!")
            
        except Exception as e:
            self.log_message(f"Ошибка! Не удалось скопировать файл:\n{str(e)}")
            self.status_var.set("Не удалось скопировать файл.")

    def btn_about(self):
        """Обработчик кнопки 'О программе'"""
        # Создаем собственное окно вместо messagebox
        top = Toplevel()
        top.title("О программе")

        # Создаем Frame для размещения текстового виджета и скроллбара
        frame = tk.Frame(top)
        frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Создаем текстовое поле
        text_widget = Text(frame, wrap=tk.WORD, width=67, height=25, font=("Arial", 10))

        top.resizable(False, False)

        # Добавляем остальной текст
        about_text = [
            "       YMapsParser\n\n",
            "  Данный инструмент предназначен для сбора открытой информации в образовательных и исследовательских целях.\n\n",
            "    Версия 0.0.5\n\n",
            "  Режимы работы:\n",
            "    1. Парсер по ключу - поиск организаций по ключевому слову и городу\n",
            "    2. Парсер по URL - парсинг конкретной страницы поиска YMaps\n\n",
            "  Возможности:\n",
            "    • Асинхронный парсинг с Playwright\n",
            "    • Сохранение данных в Excel\n",
            "    • Автоматическая генерация URL\n",
            "    • Поддержка светлой и темной темы\n\n",
            "  Используемые технологии:\n",
            "    • Python 3.13+\n",
            "    • Playwright для веб-скрапинга\n",
            "    • tkinter для графического интерфейса\n",
            "    • sv_ttk для современных стилей\n",
            "    • Openpyxl для работы с Excel\n\n",
            "    https://github.com/itrickon/YMapsParser",
        ]

        for city_text in about_text:
            text_widget.insert(tk.END, city_text)

        text_widget.configure(state="disabled")  # Только для чтения

        # Кнопка закрытия
        button = tk.Button(top, text="Закрыть", command=top.destroy)

        text_widget.pack()
        button.pack(pady=10)

        # Центрируем окно
        top.update_idletasks()
        width = top.winfo_width()
        height = top.winfo_height()
        x = (top.winfo_screenwidth() // 2) - (width // 2)
        y = (top.winfo_screenheight() // 2) - (height // 2)
        top.geometry(f"{width}x{height}+{x}+{y}")

    def btn_exit(self):
        """Выход из приложения"""
        if self.is_parsing:
            if not messagebox.askyesno(
                "Предупреждение", "Парсинг выполняется. Вы уверены, что хотите выйти?"
            ):
                return

        if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти?"):
            if self.is_parsing:
                self.stop_parsing()
            self.parent.quit()

    def create_status_bar(self):
        """Создание строки состояния"""
        self.status_var = tk.StringVar()
        self.status_var.set("Готов к работе")
        self.status_bar = ttk.Label(
            self, textvariable=self.status_var, relief=tk.SUNKEN, padding=(10, 5)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def open_link(self):
        webbrowser.open("https://github.com/itrickon/YMapsParser") 

    def bind_hotkeys(self):
        """Привязка горячих клавиш к существующим функциям"""
        self.parent.bind("<Control-r>", lambda e: self.run_parsing())
        self.parent.bind("<Control-s>", lambda e: self.stop_parsing())
        self.parent.bind("<Control-l>", lambda e: self.clear_log())
        self.parent.bind("<Control-q>", lambda e: self.btn_exit())
        self.parent.bind("<F1>", lambda e: self.user_manual())
        self.parent.bind("<Control-g>", lambda e: self.generate_url())


def main():
    """Точка входа в приложение"""
    root = tk.Tk()
    app = MainApplication(root)
    root.mainloop()


if __name__ == "__main__":
    main()
