"""
Inventory Monitor - FastAPI Backend
Real-time inventory tracking with WebSocket updates
"""

import os
import sys
import json
import math
import asyncio
from pathlib import PurePath
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware

from data_parser import parse_inventory_file
from file_watcher import FileWatcher
from database import init_db

app = FastAPI(title="Inventory Monitor API", version="1.0.0")

# CORS — конкретный origin вместо wildcard
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Максимальный размер файла (50 МБ)
MAX_FILE_SIZE = 50 * 1024 * 1024

# Хранилище данных
inventory_data: dict = {}
connected_clients: List[WebSocket] = []
_data_lock = asyncio.Lock()

# Файловый вотчер — на Render используем persistent disk
UPLOAD_DIR = os.environ.get("RENDER_UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _safe_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    name = PurePath(filename).name
    if not name or name.startswith('.'):
        raise ValueError(f"Недопустимое имя файла: {filename}")
    # Проверяем, что путь остаётся внутри UPLOAD_DIR
    full = os.path.realpath(os.path.join(UPLOAD_DIR, name))
    if not full.startswith(os.path.realpath(UPLOAD_DIR)):
        raise ValueError(f"Подозрительный путь: {filename}")
    return name


async def _safe_parse(file_path: str, skip_header_rows: int = 0) -> dict:
    """Parse file in a thread pool to avoid blocking the event loop."""
    return await asyncio.to_thread(parse_inventory_file, file_path, skip_header_rows)


async def _send_to_clients(data: dict):
    """Отправка данных всем подключённым WebSocket клиентам"""
    message = json.dumps({
        "type": "update",
        "timestamp": datetime.now().isoformat(),
        "data": data
    }, ensure_ascii=False)

    disconnected = []
    for client in connected_clients:
        try:
            await client.send_text(message)
        except Exception:
            disconnected.append(client)

    for client in disconnected:
        try:
            connected_clients.remove(client)
        except ValueError:
            pass


def _cleanup_uploads(keep: str = None):
    """Удалить старые файлы из uploads/, оставив только keep"""
    if not os.path.exists(UPLOAD_DIR):
        return
    for f in os.listdir(UPLOAD_DIR):
        if keep and f == keep:
            continue
        ext = os.path.splitext(f)[1].lower()
        if ext in ['.csv', '.xlsx', '.xls']:
            fpath = os.path.join(UPLOAD_DIR, f)
            try:
                os.remove(fpath)
                print(f"[CLEANUP] Removed old file: {f}", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"[CLEANUP] Failed to remove {f}: {e}", file=sys.stderr, flush=True)


async def _send_update_to_clients():
    """Отправить минимальное обновление (только summary + file_name, без групп)"""
    if not inventory_data:
        return
    summary = inventory_data.get("summary", {})
    file_name = inventory_data.get("file_name", "")
    print(f"[WS UPDATE] Sending update: summary={summary}, file={file_name}", file=sys.stderr, flush=True)
    message = json.dumps({
        "type": "update",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "summary": summary,
            "file_name": file_name,
        }
    }, ensure_ascii=False)

    async def _do_send():
        try:
            await _send_text_to_all(message)
        except Exception as e:
            print(f"[WS ERROR] Failed to send update: {e}", file=sys.stderr, flush=True)

    asyncio.create_task(_do_send())


async def _send_text_to_all(text: str):
    """Отправить текст всем подключённым клиентам"""
    disconnected = []
    for client in connected_clients:
        try:
            await client.send_text(text)
        except Exception:
            disconnected.append(client)

    for client in disconnected:
        try:
            connected_clients.remove(client)
        except ValueError:
            pass


def _broadcast_update(data: dict):
    """Рассылка обновлений всем подключённым клиентам"""
    global inventory_data
    data["summary"] = _recalculate_summary(data["groups"])
    inventory_data = data
    print(f"[BROADCAST] summary={data.get('summary')}", file=sys.stderr, flush=True)
    # Fire-and-forget с обработкой ошибок
    async def _do_broadcast():
        try:
            await _send_update_to_clients()
        except Exception as e:
            print(f"[BROADCAST ERROR] {e}", file=sys.stderr, flush=True)
    asyncio.create_task(_do_broadcast())


def _recalculate_summary(groups: list) -> dict:
    """Пересчёт summary на основе текущих данных групп"""
    total = len(groups)
    counted = sum(1 for g in groups if g.get("Доля", 0) == 100)
    partial = sum(1 for g in groups if 0 < g.get("Доля", 0) < 100)
    not_counted = sum(1 for g in groups if g.get("Доля", 0) == 0)

    raw_percentage = sum(g.get("Доля", 0) for g in groups) / total if total > 0 else 0
    avg_percentage = math.ceil(raw_percentage) if raw_percentage > 0 else 0

    return {
        "total_groups": total,
        "counted_groups": counted,
        "partial_groups": partial,
        "not_counted_groups": not_counted,
        "counted_percentage": avg_percentage,
    }


# Создаём вотчер после определения функций
file_watcher = FileWatcher(UPLOAD_DIR, on_new_data=_broadcast_update)


# ==================== API Endpoints ====================

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/api/cleanup")
async def cleanup_old_files():
    """Удалить старые CSV файлы, оставив только последний"""
    if not os.path.exists(UPLOAD_DIR):
        return {"status": "ok", "removed": []}

    csv_files = []
    for f in os.listdir(UPLOAD_DIR):
        ext = os.path.splitext(f)[1].lower()
        if ext in ['.csv', '.xlsx', '.xls']:
            fpath = os.path.join(UPLOAD_DIR, f)
            csv_files.append((f, os.path.getmtime(fpath), fpath))

    if len(csv_files) <= 1:
        return {"status": "ok", "removed": [], "message": "Нечего очищать"}

    csv_files.sort(key=lambda x: x[1], reverse=True)
    removed = []
    for name, _, path in csv_files[1:]:
        try:
            os.remove(path)
            removed.append(name)
        except Exception as e:
            pass

    return {"status": "ok", "removed": removed, "kept": csv_files[0][0]}


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    skip_header_rows: int = Form(0),
):
    """Загрузка CSV/Excel файла"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Файл не указан")

    # Path traversal защита
    try:
        safe_name = _safe_filename(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Проверяем расширение
    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in ['.csv', '.xlsx', '.xls']:
        raise HTTPException(status_code=400, detail="Поддерживаются только CSV и Excel файлы")

    # Проверяем размер файла
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимум: {MAX_FILE_SIZE // (1024*1024)} МБ"
        )

    # Сохраняем файл
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as f:
        f.write(content)

    # Парсим файл в отдельном потоке (не блокируем event loop)
    try:
        data = await asyncio.to_thread(parse_inventory_file, file_path, skip_header_rows)
        data["summary"] = _recalculate_summary(data["groups"])
        data["file_name"] = safe_name

        async with _data_lock:
            inventory_data.clear()
            inventory_data.update(data)

        # Чистим старые файлы после успешной загрузки нового
        _cleanup_uploads(keep=safe_name)

        # Рассылаем обновление
        await _send_update_to_clients()

        msg = f"Файл {safe_name} загружен"
        if skip_header_rows > 0:
            msg += f" (пропущено первых {skip_header_rows} строк)"
        return {"status": "ok", "message": msg, "groups_count": len(data.get("groups", []))}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка парсинга файла")


@app.get("/api/groups")
async def get_groups(
    store: Optional[str] = Query(None, description="Фильтр по магазину"),
    division: Optional[str] = Query(None, description="Фильтр по дивизиону"),
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    frequency: Optional[str] = Query(None, description="Фильтр по частоте подсчёта"),
    status: Optional[str] = Query(None, description="Фильтр по статусу: counted, partial, not_counted"),
    search: Optional[str] = Query(None, description="Поиск по названию группы"),
    limit: Optional[int] = Query(None, description="Лимит (пагинация)"),
    offset: Optional[int] = Query(0, description="Смещение (пагинация)"),
):
    """Получение списка товарных групп с фильтрами и пагинацией"""
    if not inventory_data:
        return {"groups": [], "total": 0, "has_more": False}

    groups = inventory_data.get("groups", [])

    # Применяем фильтры
    if store:
        groups = [g for g in groups if g.get("Магазин") == store]
    if division:
        groups = [g for g in groups if g.get("Дивизион ASM") == division]
    if category:
        groups = [g for g in groups if g.get("Категория") == category]
    if frequency:
        groups = [g for g in groups if g.get("Частота подсчета") == frequency]
    if status:
        if status == "counted":
            groups = [g for g in groups if g.get("Доля", 0) == 100]
        elif status == "partial":
            groups = [g for g in groups if 0 < g.get("Доля", 0) < 100]
        elif status == "not_counted":
            groups = [g for g in groups if g.get("Доля", 0) == 0]
    if search:
        search_lower = search.lower()
        groups = [g for g in groups if search_lower in g.get("Группа", "").lower()]

    total = len(groups)

    # Пагинация
    if limit is not None:
        paginated = groups[offset:offset + limit]
        has_more = (offset + limit) < total
    else:
        paginated = groups
        has_more = False

    return {"groups": paginated, "total": total, "has_more": has_more}


@app.get("/api/stats")
async def get_stats(
    store: Optional[str] = Query(None, description="Фильтр по магазину")
):
    """Общая статистика по инвентаризации"""
    if not inventory_data:
        return {
            "total_groups": 0,
            "counted_groups": 0,
            "partial_groups": 0,
            "not_counted_groups": 0,
            "counted_percentage": 0,
            "total_items": 0,
            "total_found": 0,
            "total_surplus": 0,
            "total_shortage": 0,
            "total_defect": 0,
        }
    
    groups = inventory_data.get("groups", [])
    if store:
        groups = [g for g in groups if g.get("Магазин") == store]
    
    total = len(groups)
    counted = sum(1 for g in groups if g.get("Доля", 0) == 100)
    partial = sum(1 for g in groups if 0 < g.get("Доля", 0) < 100)
    not_counted = sum(1 for g in groups if g.get("Доля", 0) == 0)

    # Готовность = средний процент выполнения по всем группам (округление в большую сторону)
    raw_percentage = sum(g.get("Доля", 0) for g in groups) / total if total > 0 else 0
    avg_percentage = math.ceil(raw_percentage) if raw_percentage > 0 else 0

    return {
        "total_groups": total,
        "counted_groups": counted,
        "partial_groups": partial,
        "not_counted_groups": not_counted,
        "counted_percentage": avg_percentage,
        "total_items": sum(g.get("Товаров в группе", 0) for g in groups),
        "total_found": sum(g.get("Найдено", 0) for g in groups),
        "total_surplus": sum(g.get("Излишки", 0) for g in groups),
        "total_shortage": sum(g.get("Недостачи", 0) for g in groups),
        "total_defect": sum(g.get("Брак", 0) for g in groups),
    }


@app.get("/api/stores")
async def get_stores():
    """Список всех магазинов"""
    if not inventory_data:
        return {"stores": []}
    
    stores = set()
    for group in inventory_data.get("groups", []):
        store_name = group.get("Магазин", "")
        if store_name:
            stores.add(store_name)
    
    return {"stores": sorted(stores)}


@app.get("/api/categories")
async def get_categories():
    """Список всех категорий"""
    if not inventory_data:
        return {"categories": []}

    categories = set()
    for group in inventory_data.get("groups", []):
        category = group.get("Категория", "")
        if category:
            categories.add(category)

    return {"categories": sorted(categories)}


@app.get("/api/frequencies")
async def get_frequencies():
    """Список всех частот подсчёта"""
    if not inventory_data:
        return {"frequencies": []}

    frequencies = set()
    for group in inventory_data.get("groups", []):
        freq = group.get("Частота подсчета", "")
        if freq:
            frequencies.add(freq)

    return {"frequencies": sorted(frequencies)}


# ==================== WebSocket ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)

    try:
        # Отправляем summary при подключении (без групп — они загрузятся через REST)
        print(f"[WS CONNECT] inventory_data keys={list(inventory_data.keys()) if inventory_data else 'EMPTY'}", file=sys.stderr, flush=True)
        if inventory_data:
            groups = inventory_data.get("groups")
            print(f"[WS CONNECT] groups count={len(groups) if groups else 0}", file=sys.stderr, flush=True)
            if groups:
                async with _data_lock:
                    inventory_data["summary"] = _recalculate_summary(groups)
                    print(f"[WS AFTER RECALC] summary={inventory_data['summary']}", file=sys.stderr, flush=True)
            await websocket.send_text(json.dumps({
                "type": "initial",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "summary": inventory_data.get("summary"),
                    "file_name": inventory_data.get("file_name", ""),
                }
            }, ensure_ascii=False))

        # Ждём сообщения от клиента (ping)
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
    except Exception as e:
        # Перехватываем ConnectionClosed и другие ошибки
        print(f"[WS ERROR] {e}", file=sys.stderr, flush=True)
        if websocket in connected_clients:
            try:
                connected_clients.remove(websocket)
            except ValueError:
                pass


# ==================== Запуск файлового вотчера ====================

@app.on_event("startup")
async def startup_event():
    """Инициализация БД и запуск файлового вотчера при старте"""
    global inventory_data

    try:
        init_db()
        print("[STARTUP] Database initialized", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[STARTUP] DB init error: {e}", file=sys.stderr, flush=True)

    # Загружаем последний CSV файл при старте (в отдельном потоке)
    if os.path.exists(UPLOAD_DIR):
        csv_files = []
        for f in os.listdir(UPLOAD_DIR):
            ext = os.path.splitext(f)[1].lower()
            if ext in ['.csv', '.xlsx', '.xls']:
                fpath = os.path.join(UPLOAD_DIR, f)
                csv_files.append((f, os.path.getmtime(fpath), fpath))

        if csv_files:
            csv_files.sort(key=lambda x: x[1], reverse=True)
            latest_name, _, latest_path = csv_files[0]
            _cleanup_uploads(keep=latest_name)

            try:
                data = await _safe_parse(latest_path)
                data["summary"] = _recalculate_summary(data["groups"])
                data["file_name"] = latest_name
                async with _data_lock:
                    inventory_data.clear()
                    inventory_data.update(data)
                print(f"[STARTUP] Loaded: {latest_name}, groups={len(data['groups'])}, pct={data['summary']['counted_percentage']}%")
            except Exception as e:
                print(f"[STARTUP] Error loading {latest_name}: {e}")

        await file_watcher.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Остановка файлового вотчера"""
    await file_watcher.stop()
