#!/usr/bin/env python3
"""
Monitor Scheduler - Automated execution of Boolean monitors.

This module provides scheduling functionality for running monitors at
specified intervals (daily, hourly, etc.).
"""

import asyncio
import logging
from pathlib import Path
from typing import List
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import sys

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from monitoring.adaptive_boolean_monitor import AdaptiveBooleanMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger('MonitorScheduler')


class MonitorScheduler:
    """
    Scheduler for running Boolean monitors automatically.

    Supports various schedule types:
    - daily_6am: Every day at 6:00 AM
    - hourly: Every hour
    - every_30min: Every 30 minutes
    - manual: No automatic execution
    """

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.monitors: List[AdaptiveBooleanMonitor] = []
        logger.info("MonitorScheduler initialized")

    def add_monitor(self, config_path: str):
        """
        Add a monitor to the scheduler.

        Args:
            config_path: Path to monitor configuration file
        """
        try:
            monitor = AdaptiveBooleanMonitor(config_path)

            if not monitor.config.enabled:
                logger.info(f"Monitor '{monitor.config.name}' is disabled, skipping")
                return

            self.monitors.append(monitor)

            # Parse schedule and add job
            schedule = monitor.config.schedule.lower()

            if schedule == "manual":
                logger.info(f"Monitor '{monitor.config.name}' set to manual - no automatic scheduling")
                return

            elif schedule == "daily_6am":
                # Every day at 6:00 AM
                trigger = CronTrigger(hour=6, minute=0)
                self.scheduler.add_job(
                    self._run_monitor,
                    trigger,
                    args=[monitor],
                    id=f"monitor_{monitor.config.name}",
                    name=monitor.config.name
                )
                logger.info(f"Scheduled '{monitor.config.name}' - Daily at 6:00 AM")

            elif schedule == "hourly":
                # Every hour
                trigger = IntervalTrigger(hours=1)
                self.scheduler.add_job(
                    self._run_monitor,
                    trigger,
                    args=[monitor],
                    id=f"monitor_{monitor.config.name}",
                    name=monitor.config.name
                )
                logger.info(f"Scheduled '{monitor.config.name}' - Hourly")

            elif schedule == "every_30min":
                # Every 30 minutes
                trigger = IntervalTrigger(minutes=30)
                self.scheduler.add_job(
                    self._run_monitor,
                    trigger,
                    args=[monitor],
                    id=f"monitor_{monitor.config.name}",
                    name=monitor.config.name
                )
                logger.info(f"Scheduled '{monitor.config.name}' - Every 30 minutes")

            elif schedule.startswith("daily_"):
                # daily_HHam or daily_HHpm format
                try:
                    time_part = schedule.replace("daily_", "")
                    if time_part.endswith("am"):
                        hour = int(time_part.replace("am", ""))
                    elif time_part.endswith("pm"):
                        hour = int(time_part.replace("pm", "")) + 12
                    else:
                        raise ValueError(f"Invalid daily schedule format: {schedule}")

                    trigger = CronTrigger(hour=hour, minute=0)
                    self.scheduler.add_job(
                        self._run_monitor,
                        trigger,
                        args=[monitor],
                        id=f"monitor_{monitor.config.name}",
                        name=monitor.config.name
                    )
                    logger.info(f"Scheduled '{monitor.config.name}' - Daily at {hour}:00")

                except ValueError as e:
                    # Invalid schedule format - skip this monitor
                    logger.error(f"Invalid schedule format '{schedule}' for monitor '{monitor.config.name}': {e}", exc_info=True)

            else:
                logger.warning(f"Unknown schedule format '{schedule}' for monitor '{monitor.config.name}'")

        except Exception as e:
            logger.error(f"Failed to add monitor from {config_path}: {str(e)}")

    async def _run_monitor(self, monitor: AdaptiveBooleanMonitor):
        """
        Run a monitor (called by scheduler).

        Args:
            monitor: AdaptiveBooleanMonitor instance to run
        """
        try:
            logger.info(f"Executing scheduled monitor: {monitor.config.name}")
            await monitor.run()
            logger.info(f"Completed scheduled monitor: {monitor.config.name}")
        except Exception as e:
            logger.error(f"Error running monitor '{monitor.config.name}': {str(e)}", exc_info=True)

    def start(self):
        """Start the scheduler."""
        if not self.monitors:
            logger.warning("No monitors configured")
            return

        logger.info(f"Starting scheduler with {len(self.monitors)} monitors")
        self.scheduler.start()
        logger.info("Scheduler started successfully")

    def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping scheduler...")
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

    def list_jobs(self):
        """List all scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        if not jobs:
            logger.info("No jobs scheduled")
            return

        logger.info(f"Scheduled jobs ({len(jobs)}):")
        for job in jobs:
            # Get next run time - APScheduler 4.x uses trigger.get_next_fire_time()
            try:
                next_run = str(job.trigger)
            except:
                next_run = "unknown"
            logger.info(f"  - {job.name}: {next_run}")


async def main():
    """
    Example usage: Run scheduler with all monitors in configs directory.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Boolean Monitor Scheduler")
    parser.add_argument(
        "--config-dir",
        default="data/monitors/configs",
        help="Directory containing monitor configuration files"
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run all monitors once and exit (no scheduling)"
    )
    args = parser.parse_args()

    # Find all config files
    config_dir = Path(args.config_dir)
    if not config_dir.exists():
        logger.error(f"Config directory not found: {config_dir}")
        return

    config_files = list(config_dir.glob("*.yaml"))
    if not config_files:
        logger.error(f"No configuration files found in {config_dir}")
        return

    logger.info(f"Found {len(config_files)} configuration files")

    if args.run_once:
        # Run all monitors once and exit
        logger.info("Running all monitors once (no scheduling)")
        for config_file in config_files:
            try:
                monitor = AdaptiveBooleanMonitor(str(config_file))
                if monitor.config.enabled:
                    logger.info(f"Running monitor: {monitor.config.name}")
                    await monitor.run()
                else:
                    logger.info(f"Skipping disabled monitor: {monitor.config.name}")
            except Exception as e:
                # Monitor execution error - continue with other monitors
                logger.error(f"Error running {config_file.name}: {str(e)}", exc_info=True)

        logger.info("All monitors completed")
    else:
        # Start scheduler
        scheduler = MonitorScheduler()

        for config_file in config_files:
            scheduler.add_monitor(str(config_file))

        scheduler.start()
        scheduler.list_jobs()

        logger.info("Scheduler running. Press Ctrl+C to exit.")

        try:
            # Keep the script running
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
