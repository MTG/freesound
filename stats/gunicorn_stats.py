import json
import logging
import logging.config
import time

import psutil

from freesound.logger import LOGGING

logging.config.dictConfig(LOGGING)

logger = logging.getLogger('monitor')

def find_procs_by_name(name):
    """Return a list of processes matching 'name'."""
    ls = []
    for p in psutil.process_iter(['name']):
        if p.info['name'] == name:
            ls.append(p)
    return ls


def main():
    interval = 60

    while True:
        next_collection_time = time.monotonic() + interval
        
        processes = find_procs_by_name("gunicorn")
        pid_to_percent = {}
        if not processes:
            print("No gunicorn processes found.")
        else:
            for p in processes:
                p.cpu_percent(None)
            
            time.sleep(2)

            for p in processes:
                cpu = p.cpu_percent(None)
                pid_to_percent[p.pid] = cpu

            # Absolute CPU values
            stats = {
                f"gunicorn_cpu_percent_{pid}": cpu
                for pid, cpu in pid_to_percent.items()
            }

            # Histogram of CPU values
            # This will miss items with cpu > 100 (e.g. more than 1 thread per process)
            ranges = [(0, 0), (1, 10), (11, 20), (21, 30), (31, 40), 
                        (41, 50), (51, 60), (61, 70), (71, 80), (81, 90), (91, 100)]

            hist = {f"{start}_{end}": 0 for start, end in ranges}

            for cpu in pid_to_percent.values():
                if cpu == 0:
                    hist["0_0"] += 1
                else:
                    for start, end in ranges:
                        if start <= cpu <= end:
                            hist[f"{start}_{end}"] += 1
            stats.update({
                f"gunicorn_cpu_hist_{range_key}": count
                for range_key, count in hist.items()
            })
            logger.info(f"Monitor ({json.dumps(stats)})")

        while time.monotonic() < next_collection_time:
            time.sleep(1)
                

if __name__ == "__main__":
    main()