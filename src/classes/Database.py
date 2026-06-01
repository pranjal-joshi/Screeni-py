"""
ScreeniDatabase - SQLite-based persistence layer for Screeni-py.
Replaces pickle-based storage with structured SQLite database.
Supports: scan results, stock data cache, watchlist, and pickle migration.
"""
import sqlite3
import json
import os
import glob
import logging
import io
from datetime import datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ScreeniDatabase:
    """
    SQLite-based storage replacing pickle-based persistence in Screeni-py.
    
    Tables:
        scan_results  - Stores screening run results with metadata
        stock_cache   - Caches fetched stock OHLCV data with TTL
        watchlist     - User watchlist with notes
    """

    def __init__(self, db_path: str = "screenipy.db"):
        """
        Initialize the database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        """Create database tables if they don't exist."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS scan_results (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT NOT NULL,
                    criteria    TEXT,
                    index_name  TEXT,
                    results_json TEXT NOT NULL,
                    agent_name  TEXT,
                    row_count   INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_scan_results_timestamp
                    ON scan_results(timestamp DESC);

                CREATE INDEX IF NOT EXISTS idx_scan_results_criteria
                    ON scan_results(criteria, index_name);

                CREATE TABLE IF NOT EXISTS stock_cache (
                    symbol      TEXT PRIMARY KEY,
                    data_json   TEXT NOT NULL,
                    fetched_at  TEXT NOT NULL,
                    ttl_seconds INTEGER DEFAULT 86400
                );

                CREATE TABLE IF NOT EXISTS watchlist (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol      TEXT NOT NULL UNIQUE,
                    added_at    TEXT NOT NULL,
                    notes       TEXT
                );
            """)
            conn.commit()
        finally:
            conn.close()

    # ---- Scan Results ----

    def save_scan_results(
        self,
        criteria: str,
        index_name: str,
        results_df: pd.DataFrame,
        agent_name: Optional[str] = None,
    ) -> int:
        """
        Save scan results to database.
        
        Args:
            criteria: Screening criteria description (e.g., 'breakout', 'rsi_40_60')
            index_name: Market index screened (e.g., 'Nifty 500')
            results_df: DataFrame of screening results
            agent_name: Optional agent persona name that ran the scan
            
        Returns:
            Inserted row ID
        """
        try:
            results_json = results_df.to_json(orient='records', date_format='iso')
            row_count = len(results_df)
        except Exception as e:
            logger.error(f"Failed to serialize scan results: {e}")
            results_json = "[]"
            row_count = 0

        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO scan_results
                   (timestamp, criteria, index_name, results_json, agent_name, row_count)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now().isoformat(),
                    criteria,
                    index_name,
                    results_json,
                    agent_name,
                    row_count,
                ),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_last_scan_results(
        self,
        criteria: Optional[str] = None,
        index_name: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Get the most recent scan results, optionally filtered by criteria and index.
        
        Args:
            criteria: Filter by criteria name
            index_name: Filter by index name
            
        Returns:
            DataFrame of results or None if not found
        """
        conn = self._get_conn()
        try:
            query = "SELECT results_json FROM scan_results WHERE 1=1"
            params = []
            if criteria:
                query += " AND criteria = ?"
                params.append(criteria)
            if index_name:
                query += " AND index_name = ?"
                params.append(index_name)
            query += " ORDER BY timestamp DESC LIMIT 1"

            row = conn.execute(query, params).fetchone()
            if row is None:
                return None
            return pd.read_json(io.StringIO(row['results_json']), orient='records')
        except Exception as e:
            logger.error(f"Failed to load scan results: {e}")
            return None
        finally:
            conn.close()

    def get_scan_history(self, limit: int = 20) -> pd.DataFrame:
        """
        Get the scan history (metadata only, not results).
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            DataFrame with scan metadata
        """
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT id, timestamp, criteria, index_name, agent_name, row_count
                   FROM scan_results ORDER BY timestamp DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            if not rows:
                return pd.DataFrame()
            return pd.DataFrame([dict(r) for r in rows])
        finally:
            conn.close()

    # ---- Stock Cache ----

    def cache_stock_data(
        self,
        symbol: str,
        df: pd.DataFrame,
        ttl: int = 86400,
    ):
        """
        Cache stock OHLCV data in SQLite.
        
        Args:
            symbol: Stock ticker symbol
            df: OHLCV DataFrame to cache
            ttl: Time-to-live in seconds (default: 24 hours)
        """
        try:
            data_json = df.to_json(orient='records', date_format='iso')
        except Exception as e:
            logger.error(f"Failed to serialize stock data for {symbol}: {e}")
            return

        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO stock_cache (symbol, data_json, fetched_at, ttl_seconds)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(symbol) DO UPDATE SET
                   data_json=excluded.data_json,
                   fetched_at=excluded.fetched_at,
                   ttl_seconds=excluded.ttl_seconds""",
                (symbol, data_json, datetime.now().isoformat(), ttl),
            )
            conn.commit()
        finally:
            conn.close()

    def get_cached_stock_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Get cached stock data if not expired.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            DataFrame of stock data or None if not cached / expired
        """
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT data_json, fetched_at, ttl_seconds FROM stock_cache WHERE symbol = ?",
                (symbol,),
            ).fetchone()

            if row is None:
                return None

            # Check TTL
            try:
                fetched_at = datetime.fromisoformat(row['fetched_at'])
                age_seconds = (datetime.now() - fetched_at).total_seconds()
                if age_seconds > row['ttl_seconds']:
                    # Expired
                    conn.execute("DELETE FROM stock_cache WHERE symbol = ?", (symbol,))
                    conn.commit()
                    return None
            except Exception:
                pass

            return pd.read_json(io.StringIO(row['data_json']), orient='records')
        except Exception as e:
            logger.error(f"Failed to load cached data for {symbol}: {e}")
            return None
        finally:
            conn.close()

    # ---- Watchlist ----

    def add_to_watchlist(self, symbol: str, notes: str = "") -> bool:
        """Add a stock to the watchlist."""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO watchlist (symbol, added_at, notes) VALUES (?, ?, ?)"
                " ON CONFLICT(symbol) DO UPDATE SET notes=excluded.notes",
                (symbol.upper(), datetime.now().isoformat(), notes),
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to add {symbol} to watchlist: {e}")
            return False
        finally:
            conn.close()

    def get_watchlist(self) -> pd.DataFrame:
        """Get all watchlist entries."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT symbol, added_at, notes FROM watchlist ORDER BY added_at DESC"
            ).fetchall()
            if not rows:
                return pd.DataFrame(columns=['symbol', 'added_at', 'notes'])
            return pd.DataFrame([dict(r) for r in rows])
        finally:
            conn.close()

    def remove_from_watchlist(self, symbol: str) -> bool:
        """Remove a stock from the watchlist."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.upper(),))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to remove {symbol} from watchlist: {e}")
            return False
        finally:
            conn.close()

    # ---- Pickle Migration ----

    def migrate_pickle_files(self, search_dir: str = ".") -> int:
        """
        Auto-detect .pkl files and import them to SQLite.
        Renames migrated files to *.pkl.migrated.
        
        Args:
            search_dir: Directory to search for .pkl files
            
        Returns:
            Number of files successfully migrated
        """
        migrated = 0
        pkl_files = glob.glob(os.path.join(search_dir, "*.pkl"))

        for pkl_path in pkl_files:
            basename = os.path.basename(pkl_path)
            # Skip already migrated or model files
            if basename.endswith('.migrated') or 'model' in basename.lower():
                continue

            try:
                df = pd.read_pickle(pkl_path)  # nosec
                if not isinstance(df, pd.DataFrame):
                    logger.warning(f"Skipping {basename}: not a DataFrame")
                    continue

                # Determine criteria from filename
                criteria = os.path.splitext(basename)[0]
                if 'unformatted' in criteria:
                    criteria = 'last_screened_unformatted'
                elif 'last_screened' in criteria:
                    criteria = 'last_screened'
                elif 'stock_data' in criteria:
                    # This is a stock data cache pickle - skip or handle separately
                    logger.info(f"Skipping stock data cache: {basename}")
                    continue

                self.save_scan_results(
                    criteria=criteria,
                    index_name='migrated',
                    results_df=df,
                    agent_name='migration',
                )

                # Rename to .migrated
                migrated_path = pkl_path + '.migrated'
                os.rename(pkl_path, migrated_path)
                logger.info(f"Migrated {basename} -> {os.path.basename(migrated_path)}")
                migrated += 1

            except Exception as e:
                logger.error(f"Failed to migrate {basename}: {e}")

        return migrated
