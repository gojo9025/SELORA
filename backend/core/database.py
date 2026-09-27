import sqlite3
import json
from pathlib import Path
from typing import List, Optional
from loguru import logger
from schemas import RegistrationResult

DB_PATH = Path(__file__).parent.parent.parent / "selora.db"

def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    logger.info(f"Initializing SQLite database at {DB_PATH}")
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id TEXT PRIMARY KEY,
                created_at TEXT,
                source_sensor TEXT,
                reference_sensor TEXT,
                mode TEXT,
                confidence REAL,
                status TEXT,
                data TEXT
            )
        """)
        conn.commit()

def save_registration(result: RegistrationResult):
    try:
        with _get_conn() as conn:
            data_json = result.model_dump_json()
            conf = result.metrics.confidence if result.metrics else 0.0
            
            conn.execute("""
                INSERT OR REPLACE INTO registrations 
                (id, created_at, source_sensor, reference_sensor, mode, confidence, status, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.registration_id,
                result.created_at.isoformat(),
                result.source_sensor,
                result.reference_sensor,
                result.mode,
                conf,
                result.status,
                data_json
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to save registration to DB: {e}")

def get_all_registrations() -> List[RegistrationResult]:
    try:
        with _get_conn() as conn:
            rows = conn.execute("SELECT data FROM registrations ORDER BY created_at DESC").fetchall()
            results = []
            for row in rows:
                try:
                    results.append(RegistrationResult.model_validate_json(row["data"]))
                except Exception as parse_e:
                    logger.warning(f"Failed to parse history row: {parse_e}")
            return results
    except Exception as e:
        logger.error(f"Failed to fetch registrations from DB: {e}")
        return []

def get_registration(reg_id: str) -> Optional[RegistrationResult]:
    try:
        with _get_conn() as conn:
            row = conn.execute("SELECT data FROM registrations WHERE id = ?", (reg_id,)).fetchone()
            if row:
                return RegistrationResult.model_validate_json(row["data"])
    except Exception as e:
        logger.error(f"Failed to fetch registration {reg_id}: {e}")
    return None

# Initialize on import
init_db()
