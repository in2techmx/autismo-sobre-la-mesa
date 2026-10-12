"""
Módulo de Persistencia SQLite y Exportación CSV para la Bitácora Alimentaria TEA.
Diseñado bajo el principio de Cero Cajas Negras: consultas SQL parametrizadas,
esquema auditable y exportación determinista compatible con Excel (UTF-8 con BOM).
"""

import csv
import io
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class BitacoraEntry:
    id: int
    user_id: int
    child_name: str
    food_item: str
    sensory_step: str  # Ej: Toleró presencia, Tocó, Olió, Probó, Comió, Rechazó
    texture_notes: str
    mood_state: str    # Ej: En calma, Ansioso, Sobrecargado, Curioso
    raw_notes: str
    created_at: str


class BitacoraRepository:
    """Gestor de base de datos SQLite para registros de la bitácora y perfiles de usuario."""

    def __init__(self, db_path: str | Path = "bitacora_tea.db") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with closing(self._get_connection()) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    child_name TEXT DEFAULT 'Mi peque',
                    sensory_profile TEXT DEFAULT 'En exploración',
                    safe_foods TEXT DEFAULT '',
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS food_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    child_name TEXT NOT NULL,
                    food_item TEXT NOT NULL,
                    sensory_step TEXT NOT NULL,
                    texture_notes TEXT DEFAULT '',
                    mood_state TEXT DEFAULT 'No especificado',
                    raw_notes TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bambi_assessments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    total_score INTEGER NOT NULL,
                    refusal_score INTEGER DEFAULT 0,
                    selectivity_score INTEGER DEFAULT 0,
                    disruptive_score INTEGER DEFAULT 0,
                    notes TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
                )
                """
            )
            conn.commit()

    def upsert_profile(
        self,
        user_id: int,
        username: str = "",
        child_name: Optional[str] = None,
        sensory_profile: Optional[str] = None,
        safe_foods: Optional[str] = None,
    ) -> dict:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with closing(self._get_connection()) as conn:
            cur = conn.execute(
                "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
            )
            existing = cur.fetchone()
            if existing is None:
                c_name = child_name or "Mi peque"
                s_prof = sensory_profile or "En exploración"
                s_foods = safe_foods or ""
                conn.execute(
                    """
                    INSERT INTO user_profiles (user_id, username, child_name, sensory_profile, safe_foods, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, username, c_name, s_prof, s_foods, now),
                )
            else:
                c_name = child_name if child_name is not None else existing["child_name"]
                s_prof = (
                    sensory_profile
                    if sensory_profile is not None
                    else existing["sensory_profile"]
                )
                s_foods = safe_foods if safe_foods is not None else existing["safe_foods"]
                u_name = username or existing["username"]
                conn.execute(
                    """
                    UPDATE user_profiles
                    SET username = ?, child_name = ?, sensory_profile = ?, safe_foods = ?, updated_at = ?
                    WHERE user_id = ?
                    """,
                    (u_name, c_name, s_prof, s_foods, now, user_id),
                )
            conn.commit()
        return self.get_profile(user_id)

    def get_profile(self, user_id: int) -> dict:
        with closing(self._get_connection()) as conn:
            cur = conn.execute(
                "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
            )
            row = cur.fetchone()
            if row is None:
                return {
                    "user_id": user_id,
                    "username": "",
                    "child_name": "Mi peque",
                    "sensory_profile": "En exploración",
                    "safe_foods": "",
                }
            return dict(row)

    def add_entry(
        self,
        user_id: int,
        food_item: str,
        sensory_step: str,
        raw_notes: str,
        texture_notes: str = "",
        mood_state: str = "No especificado",
        child_name: Optional[str] = None,
    ) -> BitacoraEntry:
        profile = self.get_profile(user_id)
        effective_child = child_name or profile["child_name"]
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        with closing(self._get_connection()) as conn:
            cur = conn.execute(
                """
                INSERT INTO food_logs (
                    user_id, child_name, food_item, sensory_step,
                    texture_notes, mood_state, raw_notes, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    effective_child.strip(),
                    food_item.strip(),
                    sensory_step.strip(),
                    texture_notes.strip(),
                    mood_state.strip(),
                    raw_notes.strip(),
                    now,
                ),
            )
            entry_id = cur.lastrowid
            conn.commit()

        return BitacoraEntry(
            id=int(entry_id),
            user_id=user_id,
            child_name=effective_child.strip(),
            food_item=food_item.strip(),
            sensory_step=sensory_step.strip(),
            texture_notes=texture_notes.strip(),
            mood_state=mood_state.strip(),
            raw_notes=raw_notes.strip(),
            created_at=now,
        )

    def get_recent_entries(self, user_id: int, limit: int = 15) -> List[BitacoraEntry]:
        with closing(self._get_connection()) as conn:
            cur = conn.execute(
                """
                SELECT * FROM food_logs
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            rows = cur.fetchall()
            return [
                BitacoraEntry(
                    id=row["id"],
                    user_id=row["user_id"],
                    child_name=row["child_name"],
                    food_item=row["food_item"],
                    sensory_step=row["sensory_step"],
                    texture_notes=row["texture_notes"],
                    mood_state=row["mood_state"],
                    raw_notes=row["raw_notes"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def add_bambi_score(
        self,
        user_id: int,
        total_score: int,
        refusal_score: int = 0,
        selectivity_score: int = 0,
        disruptive_score: int = 0,
        notes: str = "",
    ) -> dict:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with closing(self._get_connection()) as conn:
            conn.execute(
                """
                INSERT INTO bambi_assessments (
                    user_id, total_score, refusal_score, selectivity_score, disruptive_score, notes, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, total_score, refusal_score, selectivity_score, disruptive_score, notes, now),
            )
            conn.commit()
        return self.get_latest_bambi_score(user_id) or {}

    def get_latest_bambi_score(self, user_id: int) -> Optional[dict]:
        with closing(self._get_connection()) as conn:
            cur = conn.execute(
                """
                SELECT * FROM bambi_assessments
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            data = dict(row)
            data["clinical_flag"] = data["total_score"] >= 34
            return data

    def get_summary_stats(self, user_id: int) -> dict:
        entries = self.get_recent_entries(user_id, limit=100)
        total = len(entries)
        steps_count: dict[str, int] = {}
        unique_foods = set()

        for e in entries:
            steps_count[e.sensory_step] = steps_count.get(e.sensory_step, 0) + 1
            if e.food_item and e.food_item.lower() != "general":
                unique_foods.add(e.food_item.lower())

        return {
            "total_entries": total,
            "unique_foods_count": len(unique_foods),
            "steps_breakdown": steps_count,
        }

    def export_user_csv(self, user_id: int) -> bytes:
        """Exporta todos los registros del usuario en formato CSV con BOM UTF-8 para abrir directo en Excel."""
        entries = self.get_recent_entries(user_id, limit=1000)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "ID",
                "Fecha_UTC",
                "Nombre_Peque",
                "Alimento",
                "Escalera_Sensorial",
                "Textura_Presentacion",
                "Estado_Emocional",
                "Notas_Detalladas",
            ]
        )
        for e in reversed(entries):
            writer.writerow(
                [
                    e.id,
                    e.created_at,
                    e.child_name,
                    e.food_item,
                    e.sensory_step,
                    e.texture_notes,
                    e.mood_state,
                    e.raw_notes,
                ]
            )
        return output.getvalue().encode("utf-8-sig")
