import asyncio
from monitoring.adaptive_boolean_monitor import AdaptiveBooleanMonitor

async def main():
    configs = [
        'data/monitors/configs/surveillance_fisa_monitor.yaml',
        'data/monitors/configs/special_operations_monitor.yaml',
        'data/monitors/configs/immigration_enforcement_monitor.yaml'
    ]

    for config in configs:
        print(f"\n{'='*60}")
        print(f"Testing: {config}")
        print('='*60)
        monitor = AdaptiveBooleanMonitor(config)
        await monitor.run()

asyncio.run(main())
