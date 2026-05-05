"""
Scheduler for Screeni-py Agent Harness.
APScheduler-based scheduled runs for automated stock screening.
Supports cron-style schedules from screenipy.yaml.
Heartbeat: pings Kite MCP every 5 minutes to verify connectivity.
"""
import asyncio
import logging
import os
import sys
import sqlite3
from datetime import datetime
from typing import Optional

import httpx

_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    _APSCHEDULER_AVAILABLE = True
except ImportError:
    _APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed. Scheduled runs unavailable.")

from agents.llm_config import load_workflow_config, load_kite_config
from agents.agent_loader import AgentLoader

KITE_MCP_URL = "https://mcp.kite.trade/mcp"
HEARTBEAT_LOG_FILE = "screenipy_heartbeat.log"
RESULTS_DB = "screenipy_agent_results.db"


class AgentScheduler:
    """
    APScheduler-based scheduler for automated Screeni-py agent runs.
    Reads schedule from screenipy.yaml and runs configured personas.
    """

    def __init__(self, db_path: str = RESULTS_DB):
        """
        Initialize the scheduler.
        
        Args:
            db_path: Path to SQLite database for storing scheduled run results
        """
        if not _APSCHEDULER_AVAILABLE:
            raise ImportError(
                "APScheduler is required. Install with: pip install apscheduler"
            )

        self.db_path = db_path
        self.scheduler = AsyncIOScheduler()
        self.agent_loader = AgentLoader()
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for scheduled run results."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_at TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    query TEXT,
                    result TEXT,
                    status TEXT DEFAULT 'pending',
                    error TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS heartbeat_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checked_at TEXT NOT NULL,
                    url TEXT NOT NULL,
                    status_code INTEGER,
                    latency_ms REAL,
                    ok INTEGER DEFAULT 0
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def setup_from_config(self):
        """
        Set up scheduled jobs from screenipy.yaml.
        Also adds the heartbeat job.
        """
        config = load_workflow_config()
        kite_cfg = load_kite_config()

        # Heartbeat job: ping Kite MCP every 5 minutes
        heartbeat_url = kite_cfg.get('url', KITE_MCP_URL)
        self.scheduler.add_job(
            self._heartbeat_job,
            'interval',
            minutes=5,
            args=[heartbeat_url],
            id='kite_mcp_heartbeat',
            replace_existing=True,
        )
        logger.info(f"Heartbeat job added for {heartbeat_url}")

        # Add scheduled agent runs from config
        schedules = config.get('schedule', [])
        for i, sched in enumerate(schedules):
            cron_expr = sched.get('cron')
            agent_name = sched.get('agent')
            notify = sched.get('notify')

            if not cron_expr or not agent_name:
                logger.warning(f"Invalid schedule entry {i}: {sched}")
                continue

            # Parse cron expression
            cron_parts = cron_expr.strip().split()
            if len(cron_parts) == 5:
                minute, hour, day, month, day_of_week = cron_parts
                trigger = CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week,
                )
                self.scheduler.add_job(
                    self._run_scheduled_agent,
                    trigger,
                    args=[agent_name],
                    id=f'agent_run_{i}_{agent_name}',
                    replace_existing=True,
                )
                logger.info(f"Scheduled job added: {agent_name} at cron='{cron_expr}'")
            else:
                logger.warning(f"Invalid cron expression: {cron_expr}")

    async def _heartbeat_job(self, url: str):
        """Ping the Kite MCP URL and log result."""
        start = datetime.now()
        status_code = None
        ok = False
        latency_ms = 0.0

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                status_code = resp.status_code
                ok = resp.status_code < 400
                latency_ms = (datetime.now() - start).total_seconds() * 1000
        except Exception as e:
            logger.warning(f"Heartbeat failed for {url}: {e}")
            latency_ms = (datetime.now() - start).total_seconds() * 1000

        # Log to DB
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO heartbeat_log (checked_at, url, status_code, latency_ms, ok) VALUES (?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), url, status_code, latency_ms, int(ok))
            )
            conn.commit()
        finally:
            conn.close()

        status_str = f"{status_code}" if status_code else "TIMEOUT"
        logger.info(f"Heartbeat {url}: {status_str} ({latency_ms:.0f}ms) {'✓' if ok else '✗'}")

    async def _run_scheduled_agent(self, agent_name: str):
        """Run a scheduled agent persona and save results."""
        logger.info(f"Running scheduled agent: {agent_name}")
        run_at = datetime.now().isoformat()

        persona = self.agent_loader.load(agent_name)
        if not persona:
            msg = f"Persona '{agent_name}' not found"
            logger.error(msg)
            self._save_run_result(run_at, agent_name, None, None, 'error', msg)
            return

        try:
            from agents.llm_config import load_llm_config
            from agents.screeni_agent import ScreeniAgent

            llm_cfg = load_llm_config()
            agent = ScreeniAgent(persona, llm_cfg)
            query = f"Run a complete screening as {persona.get('name', agent_name)} for {persona.get('index', 'Nifty 500')}. Identify the top 10 opportunities and explain each setup briefly."
            result = await agent.run(query)
            self._save_run_result(run_at, agent_name, query, result, 'success', None)
            logger.info(f"Scheduled agent '{agent_name}' completed successfully.")
        except Exception as e:
            logger.error(f"Scheduled agent '{agent_name}' failed: {e}")
            self._save_run_result(run_at, agent_name, None, None, 'error', str(e))

    def _save_run_result(self, run_at, agent_name, query, result, status, error):
        """Save a scheduled run result to SQLite."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO scheduled_runs (run_at, agent_name, query, result, status, error) VALUES (?, ?, ?, ?, ?, ?)",
                (run_at, agent_name, query, result, status, error)
            )
            conn.commit()
        finally:
            conn.close()

    def start(self):
        """Start the scheduler (non-blocking for asyncio loops)."""
        self.scheduler.start()
        logger.info("AgentScheduler started.")

    def stop(self):
        """Stop the scheduler gracefully."""
        self.scheduler.shutdown(wait=False)
        logger.info("AgentScheduler stopped.")

    def run_forever(self):
        """Block and run the scheduler (standalone mode)."""
        import asyncio
        loop = asyncio.get_event_loop()
        self.setup_from_config()
        self.start()
        try:
            loop.run_forever()
        except (KeyboardInterrupt, SystemExit):
            self.stop()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    scheduler = AgentScheduler()
    scheduler.run_forever()
