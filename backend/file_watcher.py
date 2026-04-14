"""
File watcher - monitors uploads/ directory for new/changed files
"""

import os
import asyncio
from typing import Callable, Dict, Any
from datetime import datetime

from data_parser import parse_inventory_file


class FileWatcher:
    """
    Мониторинг папки uploads/ на наличие новых или изменённых файлов
    """
    
    def __init__(self, watch_dir: str, on_new_data: Callable[[Dict[str, Any]], None]):
        self.watch_dir = watch_dir
        self.on_new_data = on_new_data
        self._running = False
        self._file_times: Dict[str, float] = {}
        self._task: asyncio.Task = None
    
    async def start(self):
        """Запуск мониторин"""
        if self._running:
            return
        
        self._running = True
        
        # Сканируем существующие файлы
        self._scan_files()
        
        # Запускаем цикл мониторинга
        self._task = asyncio.create_task(self._watch_loop())
    
    async def stop(self):
        """Остановка мониторинга"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    def _scan_files(self):
        """Сканирование папки и запоминание времён файлов"""
        if not os.path.exists(self.watch_dir):
            return
        
        for filename in os.listdir(self.watch_dir):
            if filename.startswith('.'):
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext in ['.csv', '.xlsx', '.xls']:
                file_path = os.path.join(self.watch_dir, filename)
                try:
                    mtime = os.path.getmtime(file_path)
                    self._file_times[filename] = mtime
                except OSError:
                    pass
    
    async def _watch_loop(self):
        """Цикл мониторинга с проверкой каждые 2 секунды"""
        while self._running:
            try:
                await self._check_for_changes()
            except Exception as e:
                print(f"File watcher error: {e}")

            await asyncio.sleep(2)

    async def _check_for_changes(self):
        """Проверка на новые или изменённые файлы (async-safe)"""
        if not os.path.exists(self.watch_dir):
            return

        current_files = {}
        for filename in os.listdir(self.watch_dir):
            if filename.startswith('.'):
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext in ['.csv', '.xlsx', '.xls']:
                file_path = os.path.join(self.watch_dir, filename)
                try:
                    mtime = os.path.getmtime(file_path)
                    current_files[filename] = mtime
                except OSError:
                    pass

        # Проверяем новые или изменённые файлы
        changed_files = []
        for filename, mtime in current_files.items():
            if filename not in self._file_times or current_files[filename] > self._file_times.get(filename, 0):
                changed_files.append(filename)

        # Парсим изменённые файлы в отдельном потоке (не блокируем event loop)
        for filename in changed_files:
            file_path = os.path.join(self.watch_dir, filename)
            try:
                # Файлы из папки uploads/ обычно без SAP-заголовков — skip=0
                data = await asyncio.to_thread(parse_inventory_file, file_path, 0)
                self.on_new_data(data)
                print(f"[{datetime.now().isoformat()}] Parsed: {filename}")
            except Exception as e:
                print(f"[{datetime.now().isoformat()}] Error parsing {filename}: {e}")

        # Обновляем известные файлы
        self._file_times = current_files
