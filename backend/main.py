"""
Inventory Monitor - FastAPI Backend
Real-time inventory tracking with WebSocket updates
"""

import os
import json
import math
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from data_parser import parse_inventory_file
from file_watcher import FileWatcher
from database import init_db, upsert_manual_count, delete_manual_count, get_manual_count, get_all_manual_counts, merge_with_csv_data

# Инициализируем БД при старте
init_db()

app = FastAPI(title="Inventory Monitor API", version="1.0.0")

# CORS для разработки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранилище данных
inventory_data: dict = {}
connected_clients: List[WebSocket] = []

# Файловый вотчер — на Render используем persistent disk
UPLOAD_DIR = os.environ.get("RENDER_UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
    
    # Удаляем отключённых клиентов
    for client in disconnected:
        if client in connected_clients:
            connected_clients.remove(client)


def _broadcast_update(data: dict):
    """Рассылка обновлений всем подключённым клиентам"""
    global inventory_data
    # Мержим данные из CSV с ручными отметками из SQLite
    data["groups"] = merge_with_csv_data(data.get("groups", []))
    # Пересчитываем summary
    data["summary"] = _recalculate_summary(data["groups"])
    inventory_data = data
    import sys
    print(f"[BROADCAST] summary={data.get('summary')}", file=sys.stderr, flush=True)
    asyncio.create_task(_send_to_clients(data))


def _recalculate_summary(groups: list) -> dict:
    """Пересчёт summary на основе текущих данных групп"""
    total = len(groups)
    counted = sum(1 for g in groups if g.get("Доля", 0) == 100)
    partial = sum(1 for g in groups if 0 < g.get("Доля", 0) < 100)
    not_counted = sum(1 for g in groups if g.get("Доля", 0) == 0)
    manual = sum(1 for g in groups if g.get("is_manual"))

    # Готовность = средний процент выполнения по всем группам (округление в большую сторону)
    raw_percentage = sum(g.get("Доля", 0) for g in groups) / total if total > 0 else 0
    avg_percentage = math.ceil(raw_percentage) if raw_percentage > 0 else 0

    return {
        "total_groups": total,
        "counted_groups": counted,
        "partial_groups": partial,
        "not_counted_groups": not_counted,
        "counted_percentage": avg_percentage,
        "manual_counts": manual,
    }


def _apply_manual_update_to_memory(group_id: str, store: str, result: dict):
    """Применить ручную отметку к данным в памяти"""
    if not inventory_data:
        return
    
    for group in inventory_data.get("groups", []):
        if group.get("Группа ID") == group_id and group.get("Магазин") == store:
            group["Найдено"] = result["found_count"]
            group["Излишки"] = result["surplus"]
            group["Недостачи"] = result["shortage"]
            group["Брак"] = result["defect"]
            group["Доля"] = result["percentage"]
            group["Посчитано групп"] = 1 if result["percentage"] > 0 else 0
            group["is_manual"] = True
            group["manual_updated_at"] = result["updated_at"]
            break
    
    # Пересчитываем summary
    if inventory_data.get("groups"):
        inventory_data["summary"] = _recalculate_summary(inventory_data["groups"])


def _remove_manual_from_memory(group_id: str, store: str):
    """Удалить ручную отметку из данных в памяти"""
    if not inventory_data:
        return
    
    for group in inventory_data.get("groups", []):
        if group.get("Группа ID") == group_id and group.get("Магазин") == store:
            # Возвращаем к CSV данным (или 0% если в CSV не было)
            group["is_manual"] = False
            group["manual_updated_at"] = None
            break
    
    # Пересчитываем summary
    if inventory_data.get("groups"):
        inventory_data["summary"] = _recalculate_summary(inventory_data["groups"])


# Создаём вотчер после определения функций
file_watcher = FileWatcher(UPLOAD_DIR, on_new_data=_broadcast_update)


# ==================== API Endpoints ====================

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Загрузка CSV/Excel файла"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Файл не указан")
    
    # Проверяем расширение
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.csv', '.xlsx', '.xls']:
        raise HTTPException(status_code=400, detail="Поддерживаются только CSV и Excel файлы")
    
    # Сохраняем файл
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Парсим файл и мержим с ручными отметками
    try:
        data = parse_inventory_file(file_path)
        # Мержим данные из CSV с ручными отметками из SQLite
        data["groups"] = merge_with_csv_data(data.get("groups", []))
        # Пересчитываем summary
        data["summary"] = _recalculate_summary(data["groups"])
        
        inventory_data.update(data)
        # Рассылаем обновление
        await _send_to_clients({
            "type": "update",
            "timestamp": datetime.now().isoformat(),
            "data": inventory_data
        })
        return {"status": "ok", "message": f"Файл {file.filename} загружен", "groups_count": len(data.get("groups", []))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(e)}")


@app.get("/api/groups")
async def get_groups(
    store: Optional[str] = Query(None, description="Фильтр по магазину"),
    division: Optional[str] = Query(None, description="Фильтр по дивизиону"),
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    status: Optional[str] = Query(None, description="Фильтр по статусу: counted, partial, not_counted"),
    search: Optional[str] = Query(None, description="Поиск по названию группы"),
):
    """Получение списка товарных групп с фильтрами"""
    if not inventory_data:
        return {"groups": [], "total": 0}
    
    groups = inventory_data.get("groups", [])
    
    # Применяем фильтры
    if store:
        groups = [g for g in groups if g.get("Магазин") == store]
    if division:
        groups = [g for g in groups if g.get("Дивизион ASM") == division]
    if category:
        groups = [g for g in groups if g.get("Категория") == category]
    if status:
        if status == "counted":
            groups = [g for g in groups if g.get("Доля", 0) == 100]
        elif status == "partial":
            groups = [g for g in groups if 0 < g.get("Доля", 0) < 100]
        elif status == "not_counted":
            groups = [g for g in groups if g.get("Доля", 0) == 0]
        elif status == "manual":
            groups = [g for g in groups if g.get("is_manual")]
    if search:
        search_lower = search.lower()
        groups = [g for g in groups if search_lower in g.get("Группа", "").lower()]
    
    return {"groups": groups, "total": len(groups)}


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
        "manual_counts": sum(1 for g in groups if g.get("is_manual")),
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


# ==================== Ручные отметки ====================


class CountRequest(BaseModel):
    store: str
    found_count: int = 0
    total_planned: int = 0
    surplus: int = 0
    shortage: int = 0
    defect: int = 0

class CountResponse(BaseModel):
    status: str
    message: str
    data: Dict[str, Any]

@app.post("/api/count/{group_id}", response_model=CountResponse)
async def count_group(group_id: str, request: CountRequest):
    """Отметить группу как посчитанную (ручной ввод)"""
    result = upsert_manual_count(
        group_id=group_id,
        store=request.store,
        found_count=request.found_count,
        total_planned=request.total_planned,
        surplus=request.surplus,
        shortage=request.shortage,
        defect=request.defect,
    )
    
    # Обновляем данные в памяти
    _apply_manual_update_to_memory(group_id, request.store, result)
    
    # Рассылаем обновление
    await _send_to_clients({
        "type": "update",
        "timestamp": datetime.now().isoformat(),
        "data": inventory_data
    })
    
    return CountResponse(status="ok", message="Группа отмечена", data=result)


class StoreParam(BaseModel):
    store: str

@app.delete("/api/count/{group_id}")
async def uncount_group(group_id: str, request: StoreParam):
    """Сбросить ручную отметку группы"""
    deleted = delete_manual_count(group_id, request.store)
    
    if deleted:
        _remove_manual_from_memory(group_id, request.store)
        
        # Рассылаем обновление
        await _send_to_clients({
            "type": "update",
            "timestamp": datetime.now().isoformat(),
            "data": inventory_data
        })
    
    return {"status": "ok", "deleted": deleted}


@app.get("/api/manual_counts")
async def get_manual_counts():
    """Все ручные отметки"""
    counts = get_all_manual_counts()
    return {"counts": counts, "total": len(counts)}


# ==================== WebSocket ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    
    try:
        import sys
        # Отправляем текущие данные при подключении
        print(f"[WS CONNECT] inventory_data keys={list(inventory_data.keys()) if inventory_data else 'EMPTY'}", file=sys.stderr, flush=True)
        if inventory_data:
            groups = inventory_data.get("groups")
            print(f"[WS CONNECT] groups count={len(groups) if groups else 0}", file=sys.stderr, flush=True)
            # Пересчитываем summary актуальными данными
            if groups:
                # Проверяем типы данных
                sample = groups[:3]
                for i, g in enumerate(sample):
                    d = g.get("Доля", 0)
                    print(f"[WS SAMPLE {i}] Доля={d!r} type={type(d).__name__}", file=sys.stderr, flush=True)

                inventory_data["summary"] = _recalculate_summary(groups)
                print(f"[WS AFTER RECALC] summary={inventory_data['summary']}", file=sys.stderr, flush=True)
            await websocket.send_text(json.dumps({
                "type": "initial",
                "timestamp": datetime.now().isoformat(),
                "data": inventory_data
            }, ensure_ascii=False))
        
        # Ждём сообщения от клиента (ping)
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)


# ==================== Запуск файлового вотчера ====================

@app.on_event("startup")
async def startup_event():
    """Запуск файлового вотчера при старте"""
    global inventory_data
    # Загружаем последний CSV файл при старте
    if os.path.exists(UPLOAD_DIR):
        csv_files = []
        for f in os.listdir(UPLOAD_DIR):
            ext = os.path.splitext(f)[1].lower()
            if ext in ['.csv', '.xlsx', '.xls']:
                fpath = os.path.join(UPLOAD_DIR, f)
                csv_files.append((f, os.path.getmtime(fpath), fpath))

        if csv_files:
            # Берём самый свежий файл
            csv_files.sort(key=lambda x: x[1], reverse=True)
            latest_name, _, latest_path = csv_files[0]
            try:
                data = parse_inventory_file(latest_path)
                data["groups"] = merge_with_csv_data(data.get("groups", []))
                data["summary"] = _recalculate_summary(data["groups"])
                data["file_name"] = latest_name
                inventory_data = data
                print(f"[STARTUP] Loaded: {latest_name}, groups={len(data['groups'])}, pct={data['summary']['counted_percentage']}%")
            except Exception as e:
                print(f"[STARTUP] Error loading {latest_name}: {e}")

        await file_watcher.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Остановка файлового вотчера"""
    await file_watcher.stop()
