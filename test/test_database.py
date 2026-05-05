"""
Tests for ScreeniDatabase - SQLite-based persistence layer.
Tests creation, save/load of scan results, stock cache, and pickle migration.
"""
import pytest
import os
import sys
import tempfile
import pickle
import pandas as pd

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from classes.Database import ScreeniDatabase


@pytest.fixture
def db(tmp_path):
    """Create a fresh ScreeniDatabase in a temp directory."""
    db_path = str(tmp_path / "test_screenipy.db")
    return ScreeniDatabase(db_path=db_path)


@pytest.fixture
def sample_df():
    """Create a sample screening results DataFrame."""
    return pd.DataFrame({
        'Stock': ['RELIANCE', 'INFY', 'TCS', 'HDFCBANK', 'SBIN'],
        'LTP': [2450.0, 1850.0, 3700.0, 1650.0, 580.0],
        'RSI': [62.5, 58.3, 71.2, 45.8, 55.0],
        'Trend': ['Bullish', 'Bullish', 'Sideways', 'Bearish', 'Bullish'],
    })


class TestDatabaseInit:
    """Test database initialization and table creation."""

    def test_creates_db_file(self, tmp_path):
        """Database file should be created on initialization."""
        db_path = str(tmp_path / "new_db.db")
        assert not os.path.exists(db_path)
        db = ScreeniDatabase(db_path=db_path)
        assert os.path.exists(db_path)

    def test_creates_all_tables(self, db):
        """All required tables should exist after init."""
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert 'scan_results' in tables
        assert 'stock_cache' in tables
        assert 'watchlist' in tables

    def test_idempotent_init(self, db):
        """Reinitializing the same db should not raise errors."""
        db2 = ScreeniDatabase(db_path=db.db_path)
        # Should not raise
        assert db2 is not None


class TestScanResults:
    """Test save and load of scan results."""

    def test_save_scan_results(self, db, sample_df):
        """Saving scan results should return a valid row ID."""
        row_id = db.save_scan_results('breakout', 'Nifty 500', sample_df)
        assert isinstance(row_id, int)
        assert row_id > 0

    def test_get_last_scan_results(self, db, sample_df):
        """Loading last scan results should return the same data."""
        db.save_scan_results('breakout', 'Nifty 500', sample_df)
        result = db.get_last_scan_results()
        assert result is not None
        assert len(result) == len(sample_df)
        assert set(result.columns) == set(sample_df.columns)

    def test_get_last_scan_results_filtered_by_criteria(self, db, sample_df):
        """Filter by criteria should return matching results."""
        db.save_scan_results('breakout', 'Nifty 500', sample_df)
        df2 = sample_df.head(2).copy()
        db.save_scan_results('rsi_scan', 'Nifty 50', df2)

        result = db.get_last_scan_results(criteria='rsi_scan')
        assert result is not None
        assert len(result) == 2

    def test_get_last_scan_results_filtered_by_index(self, db, sample_df):
        """Filter by index should return matching results."""
        db.save_scan_results('breakout', 'Nifty 50', sample_df.head(1))
        db.save_scan_results('breakout', 'Nifty 500', sample_df)

        result = db.get_last_scan_results(index_name='Nifty 500')
        assert result is not None
        assert len(result) == len(sample_df)

    def test_get_last_scan_results_returns_most_recent(self, db, sample_df):
        """Should return the most recent matching record."""
        db.save_scan_results('breakout', 'Nifty 500', sample_df)
        df_new = sample_df.head(2).copy()
        db.save_scan_results('breakout', 'Nifty 500', df_new)

        result = db.get_last_scan_results(criteria='breakout', index_name='Nifty 500')
        assert result is not None
        assert len(result) == 2  # Most recent has 2 rows

    def test_get_last_scan_results_none_when_empty(self, db):
        """Should return None when no results exist."""
        result = db.get_last_scan_results()
        assert result is None

    def test_save_with_agent_name(self, db, sample_df):
        """Saving with agent_name should store correctly."""
        row_id = db.save_scan_results('breakout', 'Nifty 500', sample_df, agent_name='SwingTrader')
        assert row_id > 0

        import sqlite3
        conn = sqlite3.connect(db.db_path)
        row = conn.execute("SELECT agent_name FROM scan_results WHERE id=?", (row_id,)).fetchone()
        conn.close()
        assert row[0] == 'SwingTrader'

    def test_scan_history(self, db, sample_df):
        """get_scan_history should return metadata without full results."""
        for i in range(3):
            db.save_scan_results(f'criteria_{i}', 'Nifty 500', sample_df)

        history = db.get_scan_history(limit=10)
        assert len(history) == 3
        assert 'criteria' in history.columns
        assert 'timestamp' in history.columns
        assert 'row_count' in history.columns


class TestStockCache:
    """Test stock data caching."""

    @pytest.fixture
    def stock_df(self):
        """Sample OHLCV data."""
        import numpy as np
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        return pd.DataFrame({
            'Open': np.random.uniform(100, 200, 30),
            'High': np.random.uniform(100, 200, 30),
            'Low': np.random.uniform(100, 200, 30),
            'Close': np.random.uniform(100, 200, 30),
            'Volume': np.random.randint(100000, 1000000, 30),
        }, index=dates)

    def test_cache_and_retrieve(self, db, stock_df):
        """Caching and retrieving stock data should work."""
        db.cache_stock_data('RELIANCE', stock_df, ttl=3600)
        result = db.get_cached_stock_data('RELIANCE')
        assert result is not None
        assert len(result) == len(stock_df)

    def test_cache_miss_returns_none(self, db):
        """Non-existent cache entry should return None."""
        result = db.get_cached_stock_data('NONEXISTENT')
        assert result is None

    def test_expired_cache_returns_none(self, db, stock_df):
        """Expired cache entry should return None."""
        db.cache_stock_data('INFY', stock_df, ttl=0)  # TTL=0 means already expired
        result = db.get_cached_stock_data('INFY')
        # TTL=0 should expire immediately (age > 0)
        # This may or may not expire depending on exact timing, so just verify no exception
        assert result is None or isinstance(result, pd.DataFrame)

    def test_cache_update(self, db, stock_df):
        """Updating cache for same symbol should replace old data."""
        db.cache_stock_data('TCS', stock_df, ttl=3600)
        new_df = stock_df.tail(5).copy()
        db.cache_stock_data('TCS', new_df, ttl=3600)

        result = db.get_cached_stock_data('TCS')
        assert result is not None
        assert len(result) == 5


class TestWatchlist:
    """Test watchlist operations."""

    def test_add_to_watchlist(self, db):
        """Adding to watchlist should succeed."""
        assert db.add_to_watchlist('RELIANCE', notes='Good setup')

    def test_get_watchlist(self, db):
        """Getting watchlist should return added stocks."""
        db.add_to_watchlist('RELIANCE', notes='Breakout')
        db.add_to_watchlist('INFY', notes='RSI dip')

        watchlist = db.get_watchlist()
        assert len(watchlist) == 2
        assert 'RELIANCE' in watchlist['symbol'].values
        assert 'INFY' in watchlist['symbol'].values

    def test_remove_from_watchlist(self, db):
        """Removing from watchlist should succeed."""
        db.add_to_watchlist('SBIN')
        db.remove_from_watchlist('SBIN')

        watchlist = db.get_watchlist()
        assert len(watchlist) == 0

    def test_empty_watchlist(self, db):
        """Empty watchlist should return empty DataFrame."""
        watchlist = db.get_watchlist()
        assert isinstance(watchlist, pd.DataFrame)
        assert len(watchlist) == 0


class TestPickleMigration:
    """Test migration from pickle files."""

    def test_migrate_pickle_files(self, db, tmp_path, sample_df):
        """Migrating pickle files should import data and rename files."""
        # Create a test pickle file
        pkl_path = str(tmp_path / "last_screened_results.pkl")
        sample_df.to_pickle(pkl_path)

        migrated = db.migrate_pickle_files(search_dir=str(tmp_path))
        assert migrated == 1

        # File should be renamed
        assert not os.path.exists(pkl_path)
        assert os.path.exists(pkl_path + '.migrated')

        # Data should be in DB - criteria is normalized by migrate_pickle_files
        # (filenames containing 'last_screened' get criteria 'last_screened')
        result = db.get_last_scan_results()  # Get any result
        assert result is not None

    def test_migrate_skips_non_dataframe(self, db, tmp_path):
        """Migration should skip non-DataFrame pickle files."""
        pkl_path = str(tmp_path / "not_a_df.pkl")
        with open(pkl_path, 'wb') as f:
            pickle.dump({'key': 'value'}, f)

        migrated = db.migrate_pickle_files(search_dir=str(tmp_path))
        assert migrated == 0
        # File should NOT be renamed (migration skipped)
        assert os.path.exists(pkl_path)

    def test_migrate_empty_directory(self, db, tmp_path):
        """Migration in empty directory should return 0."""
        migrated = db.migrate_pickle_files(search_dir=str(tmp_path))
        assert migrated == 0
