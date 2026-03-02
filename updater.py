import os
import json
import shutil
import zipfile
import asyncio
import hashlib
from pathlib import Path
from typing import Optional, Callable, Dict
import requests


class AutoUpdater:
    """Модуль автоматического обновления приложения"""
    
    REPO_OWNER = "itrickon"
    REPO_NAME = "YMapsParser"
    VERSION_FILE = "version.json"
    EXCLUDE_FROM_UPDATE = [
        "ymaps_parse_results/",
        "__pycache__/",
        ".git/",
        "*.pyc",
    ]
    
    def __init__(self, current_version: str = None):
        self.current_version = current_version or self._get_current_version()
        self.latest_version: Optional[str] = None
        self.release_info: Optional[Dict] = None
        self.download_url: Optional[str] = None
        
    def _get_current_version(self) -> str:
        """Получить текущую версию из version.json"""
        try:
            with open(self.VERSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("version", "0.0.0")
        except (FileNotFoundError, json.JSONDecodeError):
            return "0.0.0"
    
    def _parse_version(self, version: str) -> tuple:
        """Преобразовать версию в кортеж для сравнения"""
        try:
            return tuple(map(int, version.split(".")))
        except (ValueError, AttributeError):
            return (0, 0, 0)
    
    def check_for_updates(self) -> bool:
        """
        Проверить наличие обновлений на GitHub
        Returns: True если есть обновление, False если нет или ошибка
        """
        try:
            api_url = f"https://api.github.com/repos/{self.REPO_OWNER}/{self.REPO_NAME}/releases/latest"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            release_data = response.json()
            self.latest_version = release_data.get("tag_name", "").lstrip("v")
            self.release_info = {
                "version": self.latest_version,
                "name": release_data.get("name", ""),
                "description": release_data.get("body", ""),
                "published_at": release_data.get("published_at", ""),
            }
            
            # Ищем ZIP-архив в ассетах
            for asset in release_data.get("assets", []):
                if asset.get("name", "").endswith(".zip"):
                    self.download_url = asset.get("browser_download_url")
                    break
            
            # Если нет ассетов, пробуем скачать исходники
            if not self.download_url:
                self.download_url = release_data.get("zipball_url")
            
            if not self.latest_version:
                return False
            
            return self._is_newer(self.latest_version, self.current_version)
            
        except requests.RequestException as e:
            print(f"Ошибка проверки обновлений: {e}")
            return False
    
    def _is_newer(self, new_ver: str, old_ver: str) -> bool:
        """Сравнить версии"""
        return self._parse_version(new_ver) > self._parse_version(old_ver)
    
    def get_release_notes(self) -> str:
        """Получить текст релиза"""
        if not self.release_info:
            return "Информация о релизе недоступна"
        
        notes = f"Версия: {self.release_info['version']}\n"
        if self.release_info.get('name'):
            notes += f"Название: {self.release_info['name']}\n"
        notes += f"\n{self.release_info.get('description', 'Описание отсутствует')}"
        return notes
    
    def download_update(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> str:
        """
        Скачать обновление
        Args:
            progress_callback: функция callback(bytes_loaded, bytes_total)
        Returns:
            Путь к скачанному файлу
        """
        if not self.download_url:
            raise ValueError("URL загрузки не найден. Сначала вызовите check_for_updates()")
        
        temp_dir = Path("temp_update")
        temp_dir.mkdir(exist_ok=True)
        
        zip_path = temp_dir / "update.zip"
        
        try:
            response = requests.get(self.download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)
            
            return str(zip_path)
            
        except Exception as e:
            if zip_path.exists():
                zip_path.unlink()
            raise Exception(f"Ошибка загрузки: {e}")
    
    def extract_and_prepare(self, zip_path: str, progress_callback: Optional[Callable[[int], None]] = None) -> str:
        """
        Распаковать обновление и подготовить файлы
        Returns:
            Путь к папке с распакованными файлами
        """
        extract_dir = Path("temp_update/extracted")
        extract_dir.mkdir(exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                file_list = zip_ref.namelist()
                total_files = len(file_list)
                
                for i, file in enumerate(file_list):
                    zip_ref.extract(file, extract_dir)
                    if progress_callback:
                        progress_callback(i + 1)
            
            # Найти корневую папку (GitHub добавляет префикс с именем репозитория)
            extracted_items = list(extract_dir.iterdir())
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                return str(extracted_items[0])
            
            return str(extract_dir)
            
        except zipfile.BadZipFile as e:
            raise Exception(f"Ошибка распаковки: {e}")
    
    def apply_update(self, source_dir: str, progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """
        Применить обновление (скопировать файлы)
        Returns:
            True если успешно
        """
        source_path = Path(source_dir)
        files_to_copy = []
        
        # Собрать файлы для копирования (исключая ненужные)
        for file_path in source_path.rglob("*"):
            relative_path = file_path.relative_to(source_path)
            str_path = str(relative_path)
            
            # Пропустить исключенные файлы/папки
            if any(excl in str_path for excl in self.EXCLUDE_FROM_UPDATE):
                continue
            
            if file_path.is_file():
                files_to_copy.append(relative_path)
        
        total_files = len(files_to_copy)
        
        # Копировать файлы
        for i, relative_path in enumerate(files_to_copy):
            src = source_path / relative_path
            dst = Path(".") / relative_path
            
            # Создать директории если нужно
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                # Создать резервную копию для важных файлов
                if dst.exists() and relative_path.name.endswith(".py"):
                    backup = dst.with_suffix(".py.backup")
                    shutil.copy2(dst, backup)
                
                shutil.copy2(src, dst)
                
                if progress_callback:
                    progress_callback(i + 1)
                    
            except Exception as e:
                print(f"Ошибка копирования {relative_path}: {e}")
                return False
        
        # Очистить временные файлы
        self.cleanup_temp()
        
        return True
    
    def cleanup_temp(self):
        """Очистить временные файлы"""
        temp_dir = Path("temp_update")
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def update(self, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> bool:
        """
        Полный цикл обновления
        Args:
            progress_callback: функция callback(stage, current, total)
                stage: "check", "download", "extract", "apply"
        Returns:
            True если обновление успешно применено
        """
        try:
            # Шаг 1: Проверка
            if progress_callback:
                progress_callback("check", 0, 100)
            
            if not self.check_for_updates():
                return False
            
            if not self._is_newer(self.latest_version, self.current_version):
                return False
            
            # Шаг 2: Загрузка
            if progress_callback:
                progress_callback("download", 0, 100)
            
            def download_progress(loaded, total):
                if progress_callback and total > 0:
                    progress_callback("download", loaded, total)
            
            zip_path = self.download_update(download_progress)
            
            # Шаг 3: Распаковка
            if progress_callback:
                progress_callback("extract", 0, 100)
            
            def extract_progress(current):
                if progress_callback:
                    progress_callback("extract", current, 100)
            
            extracted_dir = self.extract_and_prepare(zip_path, extract_progress)
            
            # Шаг 4: Применение
            if progress_callback:
                progress_callback("apply", 0, 100)
            
            def apply_progress(current):
                if progress_callback:
                    progress_callback("apply", current, 100)
            
            success = self.apply_update(extracted_dir, apply_progress)
            
            if success:
                # Обновить версию в файле
                self.current_version = self.latest_version
                self._save_version()
            
            return success
            
        except Exception as e:
            print(f"Ошибка обновления: {e}")
            self.cleanup_temp()
            return False
    
    def _save_version(self):
        """Сохранить новую версию в файл"""
        with open(self.VERSION_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "version": self.current_version,
                "release_date": str(asyncio.get_event_loop().run_until_complete(
                    asyncio.to_thread(lambda: __import__("datetime").datetime.now().strftime("%Y-%m-%d"))
                ))
            }, f, indent=4, ensure_ascii=False)


def check_and_notify(parent_window=None) -> tuple:
    """
    Быстрая проверка и уведомление
    Returns:
        (has_update: bool, message: str, new_version: str)
    """
    updater = AutoUpdater()
    
    try:
        if updater.check_for_updates():
            return (
                True,
                f"Доступна новая версия {updater.latest_version}!\n\n{updater.get_release_notes()}",
                updater.latest_version
            )
        else:
            return (False, "Установлена последняя версия", updater.current_version)
    except Exception as e:
        return (False, f"Ошибка проверки обновлений: {e}", updater.current_version)


if __name__ == "__main__":
    # Тестовый запуск
    print("Проверка обновлений...")
    has_update, message, version = check_and_notify()
    print(message)
