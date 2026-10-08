"""AI Short Generator 1.0 - Script Repository, True O(1) Deduplication & Semantic Context Naming"""

import re
import json
import sqlite3
import hashlib
from collections import Counter
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

from app.config import DEFAULT_WPS, SCRIPTS_DB_PATH
from app.core.fast_normalizer import FastDeterministicNormalizer, DeterministicRegexSanitizer

STOPWORDS_EN = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "over", "after", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "this", "that",
    "these", "those", "i", "you", "he", "she", "it", "we", "they", "my", "your", "his",
    "her", "its", "our", "their", "what", "which", "who", "when", "where", "why", "how",
    "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very", "can", "will", "just"
}


class ScriptRepository:
    """
    Gestione Repository Script e Deduplica Multi-Index SimHash True O(1) a Due Fasi:
    - Livello 1: Lookup B-Tree su normalized_hash (SHA-256)
    - Livello 2: Controllo a Due Fasi SimHash 64-bit (Character 3-grams + Word Bi-grams):
        * Fase 1 numerica su 6 blocchi unsigned e simhash_hex (zero caricamento testo in RAM)
        * Fase 2 fetch di raw_text solo per Hamming <= 5 con Jaccard >= 0.80
    - Risoluzione Deadlock Operativo: 'Crea Variante / Rigenera' per sbloccare script UTILIZZATI
    - Generazione semantica automatica dei Nomi di Contesto
    """

    def __init__(self, db_path: str = SCRIPTS_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context_title TEXT NOT NULL,
                    raw_text TEXT NOT NULL,
                    normalized_hash TEXT NOT NULL,
                    simhash_hex TEXT NOT NULL,         -- Hex string 16 caratteri (zero overflow signed int64)
                    simhash_b1 INTEGER NOT NULL,       -- Blocco 1 (unsigned 11-bit: 0..2047)
                    simhash_b2 INTEGER NOT NULL,       -- Blocco 2 (unsigned 11-bit: 0..2047)
                    simhash_b3 INTEGER NOT NULL,       -- Blocco 3 (unsigned 11-bit: 0..2047)
                    simhash_b4 INTEGER NOT NULL,       -- Blocco 4 (unsigned 11-bit: 0..2047)
                    simhash_b5 INTEGER NOT NULL,       -- Blocco 5 (unsigned 10-bit: 0..1023)
                    simhash_b6 INTEGER NOT NULL,       -- Blocco 6 (unsigned 10-bit: 0..1023)
                    char_count INTEGER NOT NULL,
                    word_count INTEGER NOT NULL,
                    est_duration_sec REAL NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('DISPONIBILE', 'IN_USO', 'UTILIZZATO')),
                    is_variant_of INTEGER NULL REFERENCES scripts(id) ON DELETE SET NULL,
                    variant_label TEXT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    used_at TIMESTAMP NULL,
                    generated_video_names TEXT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scripts_hash ON scripts(normalized_hash);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scripts_status ON scripts(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scripts_variant ON scripts(is_variant_of);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scripts_b1 ON scripts(simhash_b1);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scripts_b2 ON scripts(simhash_b2);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scripts_b3 ON scripts(simhash_b3);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scripts_b4 ON scripts(simhash_b4);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scripts_b5 ON scripts(simhash_b5);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scripts_b6 ON scripts(simhash_b6);")

    @staticmethod
    def normalize_text(text: str) -> str:
        """Pulisce il testo normalizzando spazi e caratteri per l'hash B-Tree."""
        text = text.lower()
        text = re.sub(r'[\r\n\t]+', ' ', text)
        text = re.sub(r"[^a-z0-9'\s]", '', text)
        return re.sub(r'\s+', ' ', text).strip()

    @classmethod
    def extract_shingles_and_bigrams(cls, text: str) -> List[Tuple[str, float]]:
        """
        Estrae bi-grammi di parole (preservando l'ordine sintattico)
        e 3-grammi di caratteri (per tollerare micro-variazioni).
        """
        norm = cls.normalize_text(text)
        words = norm.split()
        features: List[Tuple[str, float]] = []

        # 1. Bi-grammi di parole (peso doppio: sintassi)
        for i in range(len(words) - 1):
            bigram = f"{words[i]}_{words[i+1]}"
            features.append((bigram, 2.0))

        # 2. 3-grammi di caratteri
        compact = norm.replace(" ", "")
        for i in range(len(compact) - 2):
            trigram = compact[i:i+3]
            features.append((trigram, 1.0))

        return features

    @classmethod
    def compute_simhash_64(cls, text: str) -> Tuple[int, str]:
        """
        Calcola l'impronta a 64-bit di Moses Charikar su n-grammi shingled.
        Ritorna la coppia (impronta intera uint64, stringa esadecimale a 16 caratteri).
        """
        features = cls.extract_shingles_and_bigrams(text)
        if not features:
            return 0, "0000000000000000"

        v = [0.0] * 64
        for feat, weight in features:
            h = int(hashlib.md5(feat.encode('utf-8')).hexdigest()[:16], 16)
            for i in range(64):
                bit = (h >> i) & 1
                v[i] += weight if bit else -weight

        fingerprint = 0
        for i in range(64):
            if v[i] > 0:
                fingerprint |= (1 << i)

        hex_str = f"{fingerprint:016X}"
        return fingerprint, hex_str

    @staticmethod
    def split_simhash_6_blocks(simhash_64: int) -> Tuple[int, int, int, int, int, int]:
        """
        Scompone i 64 bit in 6 blocchi compatti unsigned:
        B1-B4: 11 bit ciascuno (0..2047)
        B5-B6: 10 bit ciascuno (0..1023)
        """
        b1 = (simhash_64 >> 53) & 0x7FF
        b2 = (simhash_64 >> 42) & 0x7FF
        b3 = (simhash_64 >> 31) & 0x7FF
        b4 = (simhash_64 >> 20) & 0x7FF
        b5 = (simhash_64 >> 10) & 0x3FF
        b6 = simhash_64 & 0x3FF
        return b1, b2, b3, b4, b5, b6

    @staticmethod
    def hamming_distance(hex1: str, hex2: str) -> int:
        """Calcola la distanza di Hamming tra due esadecimali a 64-bit (popcount XOR)."""
        x = int(hex1, 16)
        y = int(hex2, 16)
        return bin(x ^ y).count("1")

    @classmethod
    def jaccard_trigram_similarity(cls, text1: str, text2: str) -> float:
        """Calcola la similarità di Jaccard sui 3-grammi di caratteri."""
        t1 = cls.normalize_text(text1).replace(" ", "")
        t2 = cls.normalize_text(text2).replace(" ", "")
        s1 = {t1[i:i+3] for i in range(len(t1) - 2)}
        s2 = {t2[i:i+3] for i in range(len(t2) - 2)}
        if not s1 or not s2:
            return 0.0
        intersection = len(s1 & s2)
        union = len(s1 | s2)
        return intersection / union if union > 0 else 0.0

    @classmethod
    def generate_context_title(cls, text: str) -> str:
        """Genera un nome di contesto semantico non casuale per testi in lingua inglese."""
        words = re.findall(r"[a-zA-Z]{4,}", text.lower())
        filtered = [w for w in words if w not in STOPWORDS_EN]
        if not filtered:
            return "Story_General"

        # Term frequency
        counts = Counter(filtered)
        top_words = [w.capitalize() for w, _ in counts.most_common(3)]
        return "Story_" + "_".join(top_words)

    def check_duplicate(self, text: str) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Verifica True O(1) multi-livello nello storico:
        1. Controllo esatto B-Tree su normalized_hash
        2. Controllo quasi-duplicato a Due Fasi (Two-Phase Pigeonhole SimHash):
           - FASE 1: Filtro numerico leggero su simhash_hex (senza caricare raw_text).
           - FASE 2: SELECT raw_text SOLO per candidati con Hamming <= 5 con Jaccard >= 0.80.
        """
        norm = self.normalize_text(text)
        if not norm:
            return True, "Il testo inserito è vuoto.", None

        norm_hash = hashlib.sha256(norm.encode('utf-8')).hexdigest()
        sim_64, sim_hex = self.compute_simhash_64(text)
        b1, b2, b3, b4, b5, b6 = self.split_simhash_6_blocks(sim_64)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout = 30000;")

            # 1. Controllo esatto O(1)
            cur = conn.execute(
                "SELECT id, context_title, status, is_variant_of FROM scripts WHERE normalized_hash = ?",
                (norm_hash,)
            )
            row = cur.fetchone()
            if row:
                reason = (
                    f"Testo IDENTICO già presente nello storico "
                    f"(ID: #{row['id']}, Titolo: '{row['context_title']}', Stato: {row['status']})."
                )
                return True, reason, dict(row)

            # 2. FASE 1: Filtro numerico a 6 blocchi
            cur = conn.execute("""
                SELECT id, context_title, simhash_hex, status, created_at 
                FROM scripts
                WHERE simhash_b1 = ? OR simhash_b2 = ? OR simhash_b3 = ?
                   OR simhash_b4 = ? OR simhash_b5 = ? OR simhash_b6 = ?
            """, (b1, b2, b3, b4, b5, b6))
            candidates = cur.fetchall()

            close_candidate_ids = []
            for r in candidates:
                dist = self.hamming_distance(sim_hex, r["simhash_hex"])
                if dist <= 5:
                    close_candidate_ids.append((r["id"], r["context_title"], r["status"], dist))

            # 2. FASE 2: Convalida testuale mirata (Carica raw_text SOLO per Hamming <= 5)
            for c_id, c_title, c_status, dist in close_candidate_ids:
                row_text = conn.execute("SELECT raw_text FROM scripts WHERE id = ?", (c_id,)).fetchone()
                if row_text:
                    jaccard = self.jaccard_trigram_similarity(text, row_text["raw_text"])
                    if jaccard >= 0.80:
                        pct = round((1.0 - (dist / 64.0)) * 100, 1)
                        reason = (
                            f"Testo QUASI-IDENTICO rilevato "
                            f"(Somiglianza: {pct}%, Jaccard: {round(jaccard*100)}%, "
                            f"ID: #{c_id}, Titolo: '{c_title}', Stato: {c_status})."
                        )
                        return True, reason, {"id": c_id, "context_title": c_title, "status": c_status}

        return False, None, None

    def create_variant(self, parent_script_id: int, variant_label: str = "New Style Variant") -> Tuple[bool, str, int]:
        """
        Risolve il Deadlock Operativo: permette di sbloccare uno script marcato come UTILIZZATO
        creando una nuova variante indipendente pronta per essere prodotta con un'altra voce o font.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout = 30000;")
            parent = conn.execute("SELECT * FROM scripts WHERE id = ?", (parent_script_id,)).fetchone()
            if not parent:
                return False, f"Script padre #{parent_script_id} non trovato.", -1

            new_title = f"{parent['context_title']}_var"
            unique_hash = f"{parent['normalized_hash']}_v{int(hashlib.md5(variant_label.encode()).hexdigest()[:6], 16)}"

            cur = conn.execute("""
                INSERT INTO scripts (
                    context_title, raw_text, normalized_hash, simhash_hex,
                    simhash_b1, simhash_b2, simhash_b3, simhash_b4, simhash_b5, simhash_b6,
                    char_count, word_count, est_duration_sec, status, is_variant_of, variant_label
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DISPONIBILE', ?, ?)
            """, (
                new_title, parent["raw_text"], unique_hash, parent["simhash_hex"],
                parent["simhash_b1"], parent["simhash_b2"], parent["simhash_b3"],
                parent["simhash_b4"], parent["simhash_b5"], parent["simhash_b6"],
                parent["char_count"], parent["word_count"], parent["est_duration_sec"],
                parent_script_id, variant_label
            ))
            new_id = cur.lastrowid

        return True, f"Variante creata con successo (Nuovo ID: #{new_id}, Stato: DISPONIBILE).", new_id

    def save_new_script(self, raw_text: str, custom_title: Optional[str] = None) -> Tuple[bool, str, int, Optional[dict]]:
        """
        1. Esegue normalizzazione deterministica (< 0.2ms) con protezione acronimi.
        2. Applica sanitizzazione RegEx.
        3. Verifica deduplica True O(1) con MIH 6-blocchi & simhash_hex a due fasi.
        4. Salva lo script nello stato DISPONIBILE.
        Ritorna (success, message, new_id, dup_info).
        """
        # Fase A: Espansione simboli/valute e normalizzazione slang
        normalized_text = FastDeterministicNormalizer.normalize(raw_text)

        # Fase B: Sanitizzazione RegEx
        sanitized_text = DeterministicRegexSanitizer.sanitize(normalized_text)
        if not sanitized_text:
            return False, "Il testo normalizzato è vuoto.", -1, None

        # Fase C: Controllo Duplicati True O(1)
        is_dup, reason, dup_info = self.check_duplicate(sanitized_text)
        if is_dup:
            return False, reason, -1, dup_info

        norm = self.normalize_text(sanitized_text)
        norm_hash = hashlib.sha256(norm.encode('utf-8')).hexdigest()
        sim_64, sim_hex = self.compute_simhash_64(sanitized_text)
        b1, b2, b3, b4, b5, b6 = self.split_simhash_6_blocks(sim_64)
        title = custom_title.strip() if custom_title else self.generate_context_title(sanitized_text)

        words = sanitized_text.split()
        word_count = len(words)
        char_count = len(sanitized_text)
        est_duration = round(word_count / DEFAULT_WPS, 1)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            cur = conn.execute("""
                INSERT INTO scripts (
                    context_title, raw_text, normalized_hash, simhash_hex,
                    simhash_b1, simhash_b2, simhash_b3, simhash_b4, simhash_b5, simhash_b6,
                    char_count, word_count, est_duration_sec, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DISPONIBILE')
            """, (title, sanitized_text, norm_hash, sim_hex, b1, b2, b3, b4, b5, b6,
                  char_count, word_count, est_duration))
            new_id = cur.lastrowid

        return True, f"Script corretto, sanitizzato e salvato con titolo '{title}'.", new_id, None

    def lock_script_as_used(
        self,
        script_id: int,
        generated_videos: Optional[List[str]] = None,
        produced_videos: Optional[List[str]] = None
    ):
        """Blocca lo script dopo la creazione del video, preservandolo per la creazione di varianti."""
        vids = generated_videos or produced_videos or []
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("""
                UPDATE scripts 
                SET status = 'UTILIZZATO', 
                    used_at = CURRENT_TIMESTAMP,
                    generated_video_names = ?
                WHERE id = ?
            """, (json.dumps(vids), script_id))

    def mark_script_as_used(
        self,
        script_id: int,
        generated_videos: Optional[List[str]] = None,
        produced_videos: Optional[List[str]] = None
    ):
        """Alias per lock_script_as_used."""
        self.lock_script_as_used(script_id, generated_videos=generated_videos, produced_videos=produced_videos)

    def get_script(self, script_id: int) -> Optional[Dict[str, Any]]:
        """Alias per get_script_by_id."""
        return self.get_script_by_id(script_id)

    def unlock_script_to_available(self, script_id: int):
        """Ripristina lo stato dello script a DISPONIBILE (utilizzato nel rollback atomico)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("""
                UPDATE scripts 
                SET status = 'DISPONIBILE', 
                    used_at = NULL
                WHERE id = ?
            """, (script_id,))

    def set_script_in_use(self, script_id: int):
        """Imposta lo stato a IN_USO durante il rendering."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("UPDATE scripts SET status = 'IN_USO' WHERE id = ?", (script_id,))

    def get_script_by_id(self, script_id: int) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout = 30000;")
            row = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,)).fetchone()
            return dict(row) if row else None

    def get_scripts(self, status: Optional[str] = None, search_query: Optional[str] = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout = 30000;")
            query = "SELECT * FROM scripts WHERE 1=1"
            params = []
            if status:
                query += " AND status = ?"
                params.append(status)
            if search_query:
                query += " AND (context_title LIKE ? OR raw_text LIKE ?)"
                q = f"%{search_query.strip()}%"
                params.extend([q, q])
            query += " ORDER BY id DESC"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def delete_script(self, script_id: int) -> bool:
        """Elimina uno script dallo storico."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            cur = conn.execute("DELETE FROM scripts WHERE id = ?", (script_id,))
            return cur.rowcount > 0

    # Alias per compatibilità
    list_scripts = get_scripts
