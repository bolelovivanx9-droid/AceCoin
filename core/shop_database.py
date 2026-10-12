import sqlite3
import time
from pathlib import Path


DB_PATH = Path("database/casino.db")

RELIC_ID = "acecoin_heart"
XP_DAILY_PURCHASE_LIMIT = 2

SECRET_CATEGORY = "secret"
SECRET_UNLOCK_LEVEL = 5
SECRET_UNLOCK_ACHIEVEMENT = "games_10"


SHOP_ITEMS = {
    "frame_bronze": {
        "name": "Бронзовая рамка",
        "description": "Сдержанное оформление карточки профиля.",
        "category": "frames",
        "price": 2500,
        "kind": "frame",
        "rarity": "Обычный",
    },
    "frame_silver": {
        "name": "Серебряная рамка",
        "description": "Серебристое оформление профиля.",
        "category": "frames",
        "price": 35000,
        "kind": "frame",
        "rarity": "Редкий",
    },
    "frame_gold": {
        "name": "Золотая рамка",
        "description": "Золотое оформление профиля.",
        "category": "frames",
        "price": 100000,
        "kind": "frame",
        "rarity": "Эпический",
    },
    "frame_diamond": {
        "name": "Алмазная рамка",
        "description": "Драгоценное оформление профиля.",
        "category": "frames",
        "price": 500000,
        "kind": "frame",
        "rarity": "Легендарный",
    },
    "frame_cosmic": {
        "name": "Космическая рамка",
        "description": "Космическое оформление профиля.",
        "category": "frames",
        "price": 2000000,
        "kind": "frame",
        "rarity": "Мифический",
    },
    "xp_100": {
        "name": "Малый XP-бустер",
        "description": "Мгновенно начисляет 100 XP.",
        "category": "boosters",
        "price": 5000,
        "kind": "xp",
        "xp": 100,
        "rarity": "Обычный",
    },
    "xp_500": {
        "name": "Средний XP-бустер",
        "description": "Мгновенно начисляет 500 XP.",
        "category": "boosters",
        "price": 20000,
        "kind": "xp",
        "xp": 500,
        "rarity": "Редкий",
    },
    "xp_1500": {
        "name": "Большой XP-бустер",
        "description": "Мгновенно начисляет 1500 XP.",
        "category": "boosters",
        "price": 50000,
        "kind": "xp",
        "xp": 1500,
        "rarity": "Эпический",
    },
    "title_collector": {
        "name": "Титул «Коллекционер»",
        "description": "Титул для любителей коллекций.",
        "category": "titles",
        "price": 75000,
        "kind": "title",
        "rarity": "Редкий",
    },
    "title_veteran": {
        "name": "Титул «Ветеран»",
        "description": "Титул опытного игрока.",
        "category": "titles",
        "price": 150000,
        "kind": "title",
        "rarity": "Эпический",
    },
    "title_legend": {
        "name": "Титул «Легенда казино»",
        "description": "Престижный декоративный титул.",
        "category": "titles",
        "price": 1000000,
        "kind": "title",
        "rarity": "Легендарный",
    },
    RELIC_ID: {
        "name": "Сердце AceCoin",
        "description": (
            "Уникальная реликвия. Во всём боте существует "
            "только один экземпляр. Даёт только престижное "
            "оформление и титул."
        ),
        "category": "relics",
        "price": 1000000000,
        "kind": "relic",
        "rarity": "Уникальный",
    },

    # Секретный магазин.
    "frame_neon": {
        "name": "Неоновая рамка",
        "description": (
            "Секретная неоновая рамка. Открывается вместе "
            "с доступом к секретному магазину."
        ),
        "category": SECRET_CATEGORY,
        "price": 250000,
        "kind": "frame",
        "rarity": "Мифический",
    },
    "title_treasure_keeper": {
        "name": "Титул «Хранитель сокровищ»",
        "description": (
            "Секретный титул для игроков, получивших "
            "достижение «Ветеран» за 100 сыгранных игр."
        ),
        "category": SECRET_CATEGORY,
        "price": 750000,
        "kind": "title",
        "rarity": "Легендарный",
        "unlock_achievement": "games_100",
    },
    "title_secret_legend": {
        "name": "Титул «Тайная легенда»",
        "description": (
            "Особый секретный титул. Доступен игрокам "
            "20-го уровня и выше."
        ),
        "category": SECRET_CATEGORY,
        "price": 5000000,
        "kind": "title",
        "rarity": "Мифический",
        "unlock_level": 20,
    },
}


CATEGORY_NAMES = {
    "frames": "🖼️ Рамки",
    "boosters": "⭐ XP-бустеры",
    "titles": "🏷️ Титулы",
    "relics": "🏺 Реликвии",
    SECRET_CATEGORY: "🔐 Секретный магазин",
}


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_shop_db():
    """Создаёт таблицы магазина, не удаляя существующие данные."""
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shop_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                acquired_at INTEGER NOT NULL,
                UNIQUE(user_id, item_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shop_equipped (
                user_id INTEGER PRIMARY KEY,
                frame_id TEXT,
                title_id TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shop_relic (
                item_id TEXT PRIMARY KEY,
                owner_id INTEGER,
                purchased_at INTEGER,
                sold_out INTEGER NOT NULL DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shop_rare_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                event TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shop_xp_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                purchased_at INTEGER NOT NULL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_shop_inventory_user
            ON shop_inventory(user_id, acquired_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_shop_history_item
            ON shop_rare_history(item_id, created_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_shop_xp_daily
            ON shop_xp_purchases(user_id, item_id, purchased_at)
        """)

        cursor.execute("""
            INSERT OR IGNORE INTO shop_relic (
                item_id, owner_id, purchased_at, sold_out
            )
            VALUES (?, NULL, NULL, 0)
        """, (RELIC_ID,))

        conn.commit()

    finally:
        conn.close()


def get_shop_catalog(category=None):
    """Возвращает каталог магазина."""
    items = []

    for item_id, item in SHOP_ITEMS.items():
        if category is not None and item["category"] != category:
            continue

        entry = dict(item)
        entry["id"] = item_id
        items.append(entry)

    return items


def _secret_status_cursor(cursor, user_id):
    """
    Проверяет доступ к секретному магазину и возвращает статус.
    Использует уже открытый курсор, в том числе внутри транзакции.
    """
    user = cursor.execute("""
        SELECT xp
        FROM users
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    if not user:
        return {
            "unlocked": False,
            "level": 1,
            "via_level": False,
            "via_achievement": False,
        }

    xp = max(0, int(user["xp"] or 0))
    level = xp // 100 + 1

    try:
        achievement = cursor.execute("""
            SELECT 1
            FROM user_achievements
            WHERE user_id = ? AND achievement_id = ?
        """, (user_id, SECRET_UNLOCK_ACHIEVEMENT)).fetchone()
        via_achievement = achievement is not None
    except sqlite3.OperationalError:
        # Например, если таблица достижений ещё не создана.
        via_achievement = False

    via_level = level >= SECRET_UNLOCK_LEVEL

    return {
        "unlocked": via_level or via_achievement,
        "level": level,
        "via_level": via_level,
        "via_achievement": via_achievement,
    }


def get_secret_shop_status(user_id):
    """Возвращает информацию о доступе игрока к секретному магазину."""
    conn = get_connection()

    try:
        return _secret_status_cursor(conn.cursor(), user_id)
    finally:
        conn.close()


def _item_unlock_status_cursor(cursor, user_id, item_id):
    """Проверяет доступность конкретного товара."""
    item = SHOP_ITEMS.get(item_id)

    if not item:
        return {
            "unlocked": False,
            "reason": "unknown_item",
            "message": "Предмет не найден.",
        }

    if item["category"] == SECRET_CATEGORY:
        secret_status = _secret_status_cursor(cursor, user_id)

        if not secret_status["unlocked"]:
            return {
                "unlocked": False,
                "reason": "secret_locked",
                "message": (
                    "Секретный магазин открывается на 5-м уровне "
                    "или после достижения «Игрок» за 10 игр."
                ),
            }

    required_achievement = item.get("unlock_achievement")

    if required_achievement:
        try:
            achievement = cursor.execute("""
                SELECT 1
                FROM user_achievements
                WHERE user_id = ? AND achievement_id = ?
            """, (user_id, required_achievement)).fetchone()
        except sqlite3.OperationalError:
            achievement = None

        if not achievement:
            if required_achievement == "games_100":
                message = (
                    "Для этого предмета нужно достижение "
                    "«Ветеран» за 100 сыгранных игр."
                )
            else:
                message = "Сначала получи необходимое достижение."

            return {
                "unlocked": False,
                "reason": "item_locked",
                "message": message,
            }

    required_level = item.get("unlock_level")

    if required_level:
        user = cursor.execute("""
            SELECT xp
            FROM users
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        xp = max(0, int(user["xp"] or 0)) if user else 0
        level = xp // 100 + 1

        if level < required_level:
            return {
                "unlocked": False,
                "reason": "item_locked",
                "message": (
                    f"Предмет открывается на {required_level}-м уровне. "
                    f"Твой уровень: {level}."
                ),
            }

    return {
        "unlocked": True,
        "reason": None,
        "message": "",
    }


def get_item_unlock_status(user_id, item_id):
    """Проверяет доступность предмета для отображения в интерфейсе."""
    conn = get_connection()

    try:
        return _item_unlock_status_cursor(
            conn.cursor(),
            user_id,
            item_id,
        )
    finally:
        conn.close()


def get_inventory(user_id):
    """Возвращает предметы игрока."""
    conn = get_connection()

    try:
        rows = conn.execute("""
            SELECT item_id, acquired_at
            FROM shop_inventory
            WHERE user_id = ?
            ORDER BY acquired_at DESC, id DESC
        """, (user_id,)).fetchall()

        result = []

        for row in rows:
            item = SHOP_ITEMS.get(row["item_id"])
            if not item:
                continue

            entry = dict(item)
            entry["id"] = row["item_id"]
            entry["acquired_at"] = row["acquired_at"]
            result.append(entry)

        return result

    finally:
        conn.close()


def get_equipped(user_id):
    """Возвращает выбранную рамку и титул."""
    conn = get_connection()

    try:
        row = conn.execute("""
            SELECT frame_id, title_id
            FROM shop_equipped
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        if not row:
            return {"frame_id": None, "title_id": None}

        return {
            "frame_id": row["frame_id"],
            "title_id": row["title_id"],
        }

    finally:
        conn.close()


def get_relic_status():
    """Возвращает постоянный статус уникальной реликвии."""
    conn = get_connection()

    try:
        row = conn.execute("""
            SELECT item_id, owner_id, purchased_at, sold_out
            FROM shop_relic
            WHERE item_id = ?
        """, (RELIC_ID,)).fetchone()

        return dict(row) if row else None

    finally:
        conn.close()


def get_rare_history(item_id=None, limit=20):
    """История редких предметов."""
    limit = max(1, min(int(limit), 100))
    conn = get_connection()

    try:
        if item_id:
            rows = conn.execute("""
                SELECT item_id, user_id, event, created_at
                FROM shop_rare_history
                WHERE item_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (item_id, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT item_id, user_id, event, created_at
                FROM shop_rare_history
                ORDER BY id DESC
                LIMIT ?
            """, (limit,)).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


def get_xp_daily_purchases(user_id, item_id):
    """Количество покупок конкретного XP-бустера за текущие UTC-сутки."""
    item = SHOP_ITEMS.get(item_id)

    if not item or item["kind"] != "xp":
        return 0

    conn = get_connection()

    try:
        row = conn.execute("""
            SELECT COUNT(*) AS total
            FROM shop_xp_purchases
            WHERE user_id = ?
              AND item_id = ?
              AND date(purchased_at, 'unixepoch') = date('now')
        """, (user_id, item_id)).fetchone()

        return int(row["total"]) if row else 0

    finally:
        conn.close()


def purchase_item(user_id, item_id):
    """
    Покупает предмет атомарно.

    Возвращает (успех, код результата, данные).
    Каждый XP-бустер разрешено купить не более двух раз
    за UTC-сутки. XP начисляется сразу, без инвентаря.
    """
    if item_id not in SHOP_ITEMS:
        return False, "unknown_item", None

    item = SHOP_ITEMS[item_id]
    price = item["price"]
    now = int(time.time())

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        user = cursor.execute("""
            SELECT balance, xp
            FROM users
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        if not user:
            conn.rollback()
            return False, "user_not_found", None

        # Условия секретного магазина и отдельных предметов
        # проверяются внутри той же транзакции, что и покупка.
        unlock_status = _item_unlock_status_cursor(
            cursor,
            user_id,
            item_id,
        )

        if not unlock_status["unlocked"]:
            conn.rollback()
            return (
                False,
                unlock_status["reason"],
                {"message": unlock_status["message"]},
            )

        if item["kind"] == "xp":
            row = cursor.execute("""
                SELECT COUNT(*) AS total
                FROM shop_xp_purchases
                WHERE user_id = ?
                  AND item_id = ?
                  AND date(purchased_at, 'unixepoch') = date('now')
            """, (user_id, item_id)).fetchone()

            purchases_today = int(row["total"])

            if purchases_today >= XP_DAILY_PURCHASE_LIMIT:
                conn.rollback()
                return False, "xp_daily_limit", {
                    "item": item,
                    "limit": XP_DAILY_PURCHASE_LIMIT,
                    "purchased": purchases_today,
                    "remaining": 0,
                }

        if item["kind"] == "relic":
            relic = cursor.execute("""
                SELECT owner_id, purchased_at, sold_out
                FROM shop_relic
                WHERE item_id = ?
            """, (item_id,)).fetchone()

            if relic and relic["sold_out"]:
                conn.rollback()
                return False, "relic_sold", dict(relic)

        if item["kind"] != "xp":
            exists = cursor.execute("""
                SELECT 1
                FROM shop_inventory
                WHERE user_id = ? AND item_id = ?
            """, (user_id, item_id)).fetchone()

            if exists:
                conn.rollback()
                return False, "already_owned", None

        if user["balance"] < price:
            conn.rollback()
            return False, "insufficient_funds", {
                "balance": user["balance"],
                "price": price,
            }

        cursor.execute("""
            UPDATE users
            SET balance = balance - ?
            WHERE user_id = ? AND balance >= ?
        """, (price, user_id, price))

        if cursor.rowcount != 1:
            conn.rollback()
            return False, "insufficient_funds", None

        if item["kind"] == "xp":
            cursor.execute("""
                UPDATE users
                SET xp = COALESCE(xp, 0) + ?
                WHERE user_id = ?
            """, (item["xp"], user_id))

            cursor.execute("""
                INSERT INTO shop_xp_purchases (
                    user_id, item_id, purchased_at
                )
                VALUES (?, ?, ?)
            """, (user_id, item_id, now))

            purchases_today = cursor.execute("""
                SELECT COUNT(*) AS total
                FROM shop_xp_purchases
                WHERE user_id = ?
                  AND item_id = ?
                  AND date(purchased_at, 'unixepoch') = date('now')
            """, (user_id, item_id)).fetchone()["total"]

            conn.commit()

            return True, "xp_granted", {
                "item": item,
                "xp": item["xp"],
                "balance": user["balance"] - price,
                "purchased_today": purchases_today,
                "remaining_today": max(
                    0, XP_DAILY_PURCHASE_LIMIT - purchases_today
                ),
                "daily_limit": XP_DAILY_PURCHASE_LIMIT,
            }

        cursor.execute("""
            INSERT INTO shop_inventory (user_id, item_id, acquired_at)
            VALUES (?, ?, ?)
        """, (user_id, item_id, now))

        if item["kind"] == "relic":
            cursor.execute("""
                UPDATE shop_relic
                SET owner_id = ?, purchased_at = ?, sold_out = 1
                WHERE item_id = ? AND sold_out = 0
            """, (user_id, now, item_id))

            if cursor.rowcount != 1:
                conn.rollback()
                return False, "relic_sold", None

        if item["rarity"] in (
            "Легендарный", "Мифический", "Уникальный"
        ):
            cursor.execute("""
                INSERT INTO shop_rare_history (
                    item_id, user_id, event, created_at
                )
                VALUES (?, ?, 'purchased', ?)
            """, (item_id, user_id, now))

        conn.commit()

        return True, "purchased", {
            "item": item,
            "balance": user["balance"] - price,
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def equip_item(user_id, item_id):
    """Выбирает купленную рамку или титул."""
    item = SHOP_ITEMS.get(item_id)

    if not item or item["kind"] not in ("frame", "title", "relic"):
        return False, "not_equipable"

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        owned = cursor.execute("""
            SELECT 1
            FROM shop_inventory
            WHERE user_id = ? AND item_id = ?
        """, (user_id, item_id)).fetchone()

        if not owned:
            conn.rollback()
            return False, "not_owned"

        cursor.execute("""
            INSERT OR IGNORE INTO shop_equipped (
                user_id, frame_id, title_id
            )
            VALUES (?, NULL, NULL)
        """, (user_id,))

        if item["kind"] == "frame":
            cursor.execute("""
                UPDATE shop_equipped
                SET frame_id = ?
                WHERE user_id = ?
            """, (item_id, user_id))
        else:
            cursor.execute("""
                UPDATE shop_equipped
                SET title_id = ?
                WHERE user_id = ?
            """, (item_id, user_id))

        conn.commit()
        return True, "equipped"

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_equipped_details(user_id):
    """Возвращает данные выбранной рамки и титула."""
    equipped = get_equipped(user_id)

    frame = SHOP_ITEMS.get(equipped["frame_id"])
    title = SHOP_ITEMS.get(equipped["title_id"])

    return {
        "frame_id": equipped["frame_id"],
        "frame": dict(frame) if frame else None,
        "title_id": equipped["title_id"],
        "title": dict(title) if title else None,
    }