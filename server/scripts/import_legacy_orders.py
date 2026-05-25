from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pymysql
from passlib.hash import bcrypt
from pymysql.cursors import DictCursor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402

STAGING_TABLE = "legacy_order_import_tmp"
MONEY_ZERO = Decimal("0.00")
MONEY_SCALE = Decimal("0.01")
PLACEHOLDER_PASSWORD_HASH = bcrypt.hash("legacy-order-user-disabled")

ORDER_LEGACY_COLUMNS: list[tuple[str, str]] = [
    ("total_price", "DECIMAL(18,2) NULL"),
    ("pay_price", "DECIMAL(18,2) NULL"),
    ("create_time", "DATETIME NULL"),
    ("create_by", "BIGINT NULL"),
    ("update_by", "BIGINT NULL"),
    ("update_time", "DATETIME NULL"),
    ("address_id", "BIGINT NULL"),
    ("is_delete", "INT NULL"),
    ("state", "INT NULL"),
    ("bank_card_id", "BIGINT NULL"),
    ("pay_time", "DATETIME NULL"),
    ("pay_way", "INT NULL"),
    ("trade_no", "VARCHAR(128) NULL"),
    ("remark", "TEXT NULL"),
    ("dept_id", "BIGINT NULL"),
    ("write_off_qr_code", "VARCHAR(255) NULL"),
    ("legacy_order_type", "INT NULL"),
    ("is_seperate", "INT NULL"),
    ("xiaofeijin_price", "DECIMAL(18,2) NULL"),
    ("logistics_name", "VARCHAR(128) NULL"),
    ("logistics_no", "VARCHAR(128) NULL"),
    ("evaluate", "INT NULL"),
    ("refund_state", "INT NULL"),
    ("refund_no", "VARCHAR(128) NULL"),
    ("refund_time", "DATETIME NULL"),
    ("refund_price", "DECIMAL(18,2) NULL"),
    ("refund_remark", "TEXT NULL"),
    ("refund_real_price", "DECIMAL(18,2) NULL"),
    ("refund_trade_no", "VARCHAR(128) NULL"),
    ("refund_by", "BIGINT NULL"),
    ("refund_verify_state", "INT NULL"),
    ("refund_verify_time", "DATETIME NULL"),
    ("writeoff_by", "BIGINT NULL"),
    ("writeoff_time", "DATETIME NULL"),
    ("is_send", "INT NULL"),
    ("order_by", "BIGINT NULL"),
    ("is_bonus", "INT NULL"),
    ("bonus_amount", "DECIMAL(18,2) NULL"),
    ("re_order_by_reason", "VARCHAR(255) NULL"),
    ("is_re_order_by", "INT NULL"),
    ("legacy_imported_at", "DATETIME NULL"),
    ("legacy_source_file", "VARCHAR(255) NULL"),
]

ORDER_INSERT_COLUMNS = [
    "id",
    "order_no",
    "user_id",
    "team_id",
    "order_type",
    "zone_type",
    "source_ref_id",
    "total_amount",
    "discount_amount",
    "payable_amount",
    "paid_amount",
    "pay_status",
    "order_status",
    "paid_at",
    "confirmed_at",
    "created_at",
    "updated_at",
    "total_price",
    "pay_price",
    "create_time",
    "create_by",
    "update_by",
    "update_time",
    "address_id",
    "is_delete",
    "state",
    "bank_card_id",
    "pay_time",
    "pay_way",
    "trade_no",
    "remark",
    "dept_id",
    "write_off_qr_code",
    "legacy_order_type",
    "is_seperate",
    "xiaofeijin_price",
    "logistics_name",
    "logistics_no",
    "evaluate",
    "refund_state",
    "refund_no",
    "refund_time",
    "refund_price",
    "refund_remark",
    "refund_real_price",
    "refund_trade_no",
    "refund_by",
    "refund_verify_state",
    "refund_verify_time",
    "writeoff_by",
    "writeoff_time",
    "is_send",
    "order_by",
    "is_bonus",
    "bonus_amount",
    "re_order_by_reason",
    "is_re_order_by",
    "legacy_imported_at",
    "legacy_source_file",
]

STAGING_TABLE_SQL = f"""
CREATE TEMPORARY TABLE `{STAGING_TABLE}` (
    `id` BIGINT NOT NULL,
    `order_no` VARCHAR(64) NOT NULL,
    `total_price` DECIMAL(18,2) NULL,
    `pay_price` DECIMAL(18,2) NULL,
    `create_time` DATETIME NULL,
    `create_by` BIGINT NULL,
    `update_by` BIGINT NULL,
    `update_time` DATETIME NULL,
    `address_id` BIGINT NULL,
    `is_delete` INT NULL,
    `state` INT NULL,
    `bank_card_id` BIGINT NULL,
    `pay_time` DATETIME NULL,
    `pay_way` INT NULL,
    `trade_no` VARCHAR(128) NULL,
    `remark` TEXT NULL,
    `dept_id` BIGINT NULL,
    `write_off_qr_code` VARCHAR(255) NULL,
    `order_type` INT NULL,
    `is_seperate` INT NULL,
    `xiaofeijin_price` DECIMAL(18,2) NULL,
    `logistics_name` VARCHAR(128) NULL,
    `logistics_no` VARCHAR(128) NULL,
    `evaluate` INT NULL,
    `refund_state` INT NULL,
    `refund_no` VARCHAR(128) NULL,
    `refund_time` DATETIME NULL,
    `refund_price` DECIMAL(18,2) NULL,
    `refund_remark` TEXT NULL,
    `refund_real_price` DECIMAL(18,2) NULL,
    `refund_trade_no` VARCHAR(128) NULL,
    `refund_by` BIGINT NULL,
    `refund_verify_state` INT NULL,
    `refund_verify_time` DATETIME NULL,
    `writeoff_by` BIGINT NULL,
    `writeoff_time` DATETIME NULL,
    `is_send` INT NULL,
    `order_by` BIGINT NULL,
    `is_bonus` INT NULL,
    `bonus_amount` DECIMAL(18,2) NULL,
    `re_order_by_reason` VARCHAR(255) NULL,
    `is_re_order_by` INT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_{STAGING_TABLE}_order_no` (`order_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

ORDER_INSERT_SQL = f"""
INSERT INTO `orders` (
    {", ".join(f"`{column}`" for column in ORDER_INSERT_COLUMNS)}
) VALUES (
    {", ".join(["%s"] * len(ORDER_INSERT_COLUMNS))}
)
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import legacy order SQL into the current orders table.")
    parser.add_argument("source", type=Path, help="Path to the legacy order SQL file.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only inspect the file and report what would be imported.",
    )
    return parser.parse_args()


def connect_db() -> pymysql.Connection:
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_db,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )


def iter_chunks(items: Iterable[Any], chunk_size: int = 1000) -> Iterable[list[Any]]:
    chunk: list[Any] = []
    for item in items:
        chunk.append(item)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def read_source_lines(source: Path) -> list[str]:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = source.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise UnicodeDecodeError("legacy-order", b"", 0, 1, f"Cannot decode file: {source}")
    return text.splitlines()


def ensure_order_columns(cursor: pymysql.cursors.Cursor) -> list[str]:
    existing = current_order_columns(cursor)
    added: list[str] = []
    for column_name, column_type in ORDER_LEGACY_COLUMNS:
        if column_name in existing:
            continue
        cursor.execute(f"ALTER TABLE `orders` ADD COLUMN `{column_name}` {column_type}")
        added.append(column_name)
    return added


def current_order_columns(cursor: pymysql.cursors.Cursor) -> set[str]:
    cursor.execute("SHOW COLUMNS FROM `orders`")
    return {row["Field"] for row in cursor.fetchall()}


def create_staging_table(cursor: pymysql.cursors.Cursor) -> None:
    cursor.execute(STAGING_TABLE_SQL)


def load_legacy_sql(cursor: pymysql.cursors.Cursor, source: Path) -> int:
    statements = 0
    buffer: list[str] = []
    for raw_line in read_source_lines(source):
        line = raw_line.lstrip("\ufeff").strip()
        if not line:
            continue
        buffer.append(line)
        if not line.endswith(";"):
            continue
        statement = " ".join(buffer)
        buffer.clear()
        if not statement.startswith("INSERT INTO"):
            continue
        if "`<table_name>`" not in statement:
            raise ValueError(f"Unsupported INSERT statement in {source}: {statement[:120]}")
        cursor.execute(statement.replace("`<table_name>`", f"`{STAGING_TABLE}`", 1))
        statements += 1
    if buffer:
        raise ValueError(f"Found unterminated SQL statement in {source}")
    return statements


def fetch_staging_rows(cursor: pymysql.cursors.Cursor) -> list[dict[str, Any]]:
    cursor.execute(f"SELECT * FROM `{STAGING_TABLE}` ORDER BY `id` ASC")
    return list(cursor.fetchall())


def summarize(rows: list[dict[str, Any]]) -> dict[str, Counter[Any]]:
    summary = {
        "state": Counter(),
        "pay_way": Counter(),
        "refund_state": Counter(),
        "order_type": Counter(),
        "is_send": Counter(),
    }
    for row in rows:
        for key, counter in summary.items():
            counter[row.get(key)] += 1
    return summary


def print_summary(rows: list[dict[str, Any]], summary: dict[str, Counter[Any]]) -> None:
    print(f"loaded_rows={len(rows)}")
    for name, counter in summary.items():
        print(f"{name}_counts={dict(sorted(counter.items(), key=lambda item: (item[0] is None, item[0])))}")


def collect_legacy_user_ids(rows: list[dict[str, Any]]) -> set[int]:
    legacy_user_ids: set[int] = set()
    for row in rows:
        for key in ("create_by", "update_by", "refund_by", "writeoff_by", "order_by"):
            value = row.get(key)
            if value is None:
                continue
            value = int(value)
            if value > 0:
                legacy_user_ids.add(value)
    return legacy_user_ids


def load_legacy_user_mapping(cursor: pymysql.cursors.Cursor, legacy_user_ids: set[int]) -> dict[int, dict[str, Any]]:
    mapping: dict[int, dict[str, Any]] = {}
    for chunk in iter_chunks(sorted(legacy_user_ids)):
        placeholders = ", ".join(["%s"] * len(chunk))
        cursor.execute(
            f"""
            SELECT p.`legacy_user_id`, p.`user_id`, u.`team_id`
            FROM `user_legacy_profiles` p
            LEFT JOIN `users` u ON u.`id` = p.`user_id`
            WHERE p.`legacy_user_id` IN ({placeholders})
            """,
            tuple(chunk),
        )
        for row in cursor.fetchall():
            mapping[int(row["legacy_user_id"])] = {
                "user_id": int(row["user_id"]),
                "team_id": int(row["team_id"]) if row["team_id"] is not None else None,
            }
    return mapping


def generate_invite_code(cursor: pymysql.cursors.Cursor, legacy_user_id: int) -> str:
    base = f"LEGACY{legacy_user_id}"
    for attempt in range(100):
        if attempt == 0:
            invite_code = base[:32]
        else:
            suffix = f"-{attempt}"
            invite_code = f"{base[: 32 - len(suffix)]}{suffix}"
        cursor.execute("SELECT 1 FROM `users` WHERE `invite_code` = %s LIMIT 1", (invite_code,))
        if cursor.fetchone() is None:
            return invite_code
    raise RuntimeError(f"Unable to generate unique invite_code for legacy user {legacy_user_id}")


def create_placeholder_legacy_user(cursor: pymysql.cursors.Cursor, legacy_user_id: int, imported_at: datetime) -> dict[str, Any]:
    invite_code = generate_invite_code(cursor, legacy_user_id)
    cursor.execute(
        """
        INSERT INTO `users` (
            `phone`,
            `password_hash`,
            `nickname`,
            `avatar`,
            `global_role`,
            `business_identity`,
            `status`,
            `invite_code`,
            `parent_id`,
            `grandparent_id`,
            `team_id`,
            `real_name`,
            `last_login_at`,
            `created_at`,
            `updated_at`
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            None,
            PLACEHOLDER_PASSWORD_HASH,
            f"LegacyUser-{legacy_user_id}",
            None,
            "USER",
            "NORMAL_MEMBER",
            "DISABLED",
            invite_code,
            None,
            None,
            None,
            None,
            None,
            imported_at,
            imported_at,
        ),
    )
    user_id = int(cursor.lastrowid)
    cursor.execute(
        """
        INSERT INTO `user_legacy_profiles` (`user_id`, `legacy_user_id`, `imported_at`)
        VALUES (%s, %s, %s)
        """,
        (user_id, legacy_user_id, imported_at),
    )
    return {"user_id": user_id, "team_id": None}


def ensure_legacy_user_mapping(
    cursor: pymysql.cursors.Cursor,
    legacy_user_ids: set[int],
    imported_at: datetime,
) -> tuple[dict[int, dict[str, Any]], list[int]]:
    mapping = load_legacy_user_mapping(cursor, legacy_user_ids)
    missing_ids = sorted(legacy_user_ids - set(mapping))
    for legacy_user_id in missing_ids:
        mapping[legacy_user_id] = create_placeholder_legacy_user(cursor, legacy_user_id, imported_at)
    return mapping, missing_ids


def find_existing_conflicts(cursor: pymysql.cursors.Cursor, rows: list[dict[str, Any]]) -> tuple[set[int], set[str]]:
    existing_ids: set[int] = set()
    existing_order_nos: set[str] = set()
    ids = sorted({int(row["id"]) for row in rows})
    order_nos = sorted({str(row["order_no"]) for row in rows})
    for chunk in iter_chunks(ids):
        placeholders = ", ".join(["%s"] * len(chunk))
        cursor.execute(f"SELECT `id` FROM `orders` WHERE `id` IN ({placeholders})", tuple(chunk))
        existing_ids.update(int(row["id"]) for row in cursor.fetchall())
    for chunk in iter_chunks(order_nos):  # type: ignore[arg-type]
        placeholders = ", ".join(["%s"] * len(chunk))
        cursor.execute(f"SELECT `order_no` FROM `orders` WHERE `order_no` IN ({placeholders})", tuple(chunk))
        existing_order_nos.update(str(row["order_no"]) for row in cursor.fetchall())
    return existing_ids, existing_order_nos


def get_fallback_user(cursor: pymysql.cursors.Cursor) -> dict[str, Any]:
    cursor.execute("SELECT `id`, `team_id` FROM `users` ORDER BY `id` ASC LIMIT 1")
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("users table is empty, cannot import orders")
    return {"user_id": int(row["id"]), "team_id": int(row["team_id"]) if row["team_id"] is not None else None}


def money(value: Any) -> Decimal:
    if value is None:
        return MONEY_ZERO
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    return amount.quantize(MONEY_SCALE)


def is_truthy(value: Any) -> bool:
    return value not in (None, 0, "0", "", False)


def map_current_order_type(row: dict[str, Any]) -> tuple[str, str | None]:
    legacy_order_type = row.get("order_type")
    if is_truthy(row.get("is_re_order_by")):
        return "REPURCHASE_ORDER", "REPURCHASE"
    mapping = {
        0: ("NORMAL_PRODUCT", None),
        1: ("NORMAL_PRODUCT", None),
        2: ("SELF_OPERATED_ORDER", "SELF_OPERATED"),
        3: ("HOT_SALE_ORDER", "HOT_SALE"),
        4: ("LOCAL_LIFE_ORDER", "LOCAL_LIFE"),
    }
    return mapping.get(legacy_order_type, ("NORMAL_PRODUCT", None))


def resolve_status(row: dict[str, Any]) -> tuple[str, str]:
    legacy_state = row.get("state")
    paid = (
        row.get("pay_time") is not None
        or is_truthy(row.get("trade_no"))
        or is_truthy(row.get("pay_way"))
        or money(row.get("pay_price")) > MONEY_ZERO
        or legacy_state in (1, 2, 3)
    )
    refunded = (
        row.get("refund_time") is not None
        or is_truthy(row.get("refund_no"))
        or is_truthy(row.get("refund_trade_no"))
        or money(row.get("refund_price")) > MONEY_ZERO
        or money(row.get("refund_real_price")) > MONEY_ZERO
        or row.get("refund_state") not in (None, 0)
    )
    if refunded:
        return "REFUNDED", "REFUNDED"
    if legacy_state == 3 or row.get("writeoff_time") is not None or row.get("writeoff_by") is not None:
        return "PAID", "CONFIRMED"
    if legacy_state in (4, 5) or is_truthy(row.get("is_delete")):
        return "PAID" if paid else "UNPAID", "CLOSED"
    if legacy_state in (1, 2) or paid:
        return "PAID", "PAID"
    return "UNPAID", "CREATED"


def build_order_record(
    row: dict[str, Any],
    user_mapping: dict[int, dict[str, Any]],
    fallback_user: dict[str, Any],
    imported_at: datetime,
    source_name: str,
) -> dict[str, Any]:
    owner = user_mapping.get(int(row["create_by"])) if row.get("create_by") is not None else None
    if owner is None:
        owner = user_mapping.get(int(row["order_by"])) if row.get("order_by") is not None else None
    if owner is None:
        owner = fallback_user

    referrer = user_mapping.get(int(row["order_by"])) if row.get("order_by") is not None else None
    order_type, zone_type = map_current_order_type(row)
    pay_status, order_status = resolve_status(row)

    total_amount = money(row.get("total_price"))
    payable_amount = money(row.get("pay_price")) if row.get("pay_price") is not None else total_amount
    discount_amount = max(total_amount - payable_amount, MONEY_ZERO).quantize(MONEY_SCALE)
    paid_amount = payable_amount if pay_status in {"PAID", "REFUNDED"} else MONEY_ZERO
    created_at = row.get("create_time") or imported_at
    updated_at = row.get("update_time") or row.get("create_time") or imported_at

    return {
        "id": int(row["id"]),
        "order_no": str(row["order_no"]),
        "user_id": owner["user_id"],
        "team_id": owner["team_id"],
        "order_type": order_type,
        "zone_type": zone_type,
        "source_ref_id": referrer["user_id"] if referrer else None,
        "total_amount": total_amount,
        "discount_amount": discount_amount,
        "payable_amount": payable_amount,
        "paid_amount": paid_amount,
        "pay_status": pay_status,
        "order_status": order_status,
        "paid_at": row.get("pay_time"),
        "confirmed_at": row.get("writeoff_time") or (updated_at if order_status == "CONFIRMED" else None),
        "created_at": created_at,
        "updated_at": updated_at,
        "total_price": row.get("total_price"),
        "pay_price": row.get("pay_price"),
        "create_time": row.get("create_time"),
        "create_by": row.get("create_by"),
        "update_by": row.get("update_by"),
        "update_time": row.get("update_time"),
        "address_id": row.get("address_id"),
        "is_delete": row.get("is_delete"),
        "state": row.get("state"),
        "bank_card_id": row.get("bank_card_id"),
        "pay_time": row.get("pay_time"),
        "pay_way": row.get("pay_way"),
        "trade_no": row.get("trade_no"),
        "remark": row.get("remark"),
        "dept_id": row.get("dept_id"),
        "write_off_qr_code": row.get("write_off_qr_code"),
        "legacy_order_type": row.get("order_type"),
        "is_seperate": row.get("is_seperate"),
        "xiaofeijin_price": row.get("xiaofeijin_price"),
        "logistics_name": row.get("logistics_name"),
        "logistics_no": row.get("logistics_no"),
        "evaluate": row.get("evaluate"),
        "refund_state": row.get("refund_state"),
        "refund_no": row.get("refund_no"),
        "refund_time": row.get("refund_time"),
        "refund_price": row.get("refund_price"),
        "refund_remark": row.get("refund_remark"),
        "refund_real_price": row.get("refund_real_price"),
        "refund_trade_no": row.get("refund_trade_no"),
        "refund_by": row.get("refund_by"),
        "refund_verify_state": row.get("refund_verify_state"),
        "refund_verify_time": row.get("refund_verify_time"),
        "writeoff_by": row.get("writeoff_by"),
        "writeoff_time": row.get("writeoff_time"),
        "is_send": row.get("is_send"),
        "order_by": row.get("order_by"),
        "is_bonus": row.get("is_bonus"),
        "bonus_amount": row.get("bonus_amount"),
        "re_order_by_reason": row.get("re_order_by_reason"),
        "is_re_order_by": row.get("is_re_order_by"),
        "legacy_imported_at": imported_at,
        "legacy_source_file": source_name,
    }


def insert_orders(
    cursor: pymysql.cursors.Cursor,
    rows: list[dict[str, Any]],
    user_mapping: dict[int, dict[str, Any]],
    fallback_user: dict[str, Any],
    imported_at: datetime,
    source_name: str,
) -> tuple[int, int]:
    imported = 0
    skipped = 0
    for row in rows:
        record = build_order_record(row, user_mapping, fallback_user, imported_at, source_name)
        values = [record[column] for column in ORDER_INSERT_COLUMNS]
        try:
            cursor.execute(ORDER_INSERT_SQL, values)
            imported += 1
        except pymysql.err.IntegrityError as exc:
            if exc.args and exc.args[0] == 1062:
                skipped += 1
                continue
            raise
    return imported, skipped


def main() -> int:
    args = parse_args()
    source = args.source
    if not source.exists():
        raise FileNotFoundError(f"Legacy order SQL not found: {source}")

    connection = connect_db()
    try:
        with connection.cursor() as cursor:
            create_staging_table(cursor)
            loaded_statements = load_legacy_sql(cursor, source)
            rows = fetch_staging_rows(cursor)
            summary = summarize(rows)
            legacy_user_ids = collect_legacy_user_ids(rows)
            existing_mapping = load_legacy_user_mapping(cursor, legacy_user_ids)
            order_columns = current_order_columns(cursor)
            missing_columns = [name for name, _ in ORDER_LEGACY_COLUMNS if name not in order_columns]
            existing_ids, existing_order_nos = find_existing_conflicts(cursor, rows)

            print(f"source={source}")
            print(f"loaded_statements={loaded_statements}")
            print_summary(rows, summary)
            print(f"legacy_user_ids={len(legacy_user_ids)}")
            print(f"mapped_legacy_users={len(existing_mapping)}")
            print(f"missing_legacy_users={len(legacy_user_ids - set(existing_mapping))}")
            print(f"duplicate_ids={len(existing_ids)}")
            print(f"duplicate_order_nos={len(existing_order_nos)}")

            if args.dry_run:
                print("mode=dry-run")
                print(f"missing_order_columns={missing_columns}")
                connection.rollback()
                return 0

            added_columns = ensure_order_columns(cursor)
            imported_at = datetime.now()
            user_mapping, created_legacy_users = ensure_legacy_user_mapping(cursor, legacy_user_ids, imported_at)
            fallback_user = get_fallback_user(cursor)
            imported, skipped = insert_orders(cursor, rows, user_mapping, fallback_user, imported_at, source.name)
            connection.commit()

            with connection.cursor() as verify_cursor:
                verify_cursor.execute(
                    "SELECT COUNT(*) AS total FROM `orders` WHERE `legacy_source_file` = %s",
                    (source.name,),
                )
                imported_total = int(verify_cursor.fetchone()["total"])

            print("mode=apply")
            print(f"added_order_columns={added_columns}")
            print(f"created_placeholder_legacy_users={len(created_legacy_users)}")
            print(f"imported_orders={imported}")
            print(f"skipped_orders={skipped}")
            print(f"orders_with_source_file={imported_total}")
            return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
