import json
import threading
import time
from sync_service import FileSyncService
import signal
import sys

def load_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def run_instance(api_key, local_sync_dir, remote_url, poll_interval, port):
    service = FileSyncService(
        api_key=api_key,
        local_sync_dir=local_sync_dir,
        remote_url=remote_url,
        poll_interval=poll_interval,
        port=port,
    )
    service.start()

if __name__ == "__main__":
    def signal_handler(sig, frame):
        print("Shutting down gracefully...")
        sys.exit(0)

    # Handle termination signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Load configurations from JSON files
    instance1_config = load_config('instance1_config.json')
    instance2_config = load_config('instance2_config.json')

    # Start Instance 1 in a separate thread
    thread1 = threading.Thread(
        target=run_instance,
        args=(
            instance1_config["api_key"],
            instance1_config["local_sync_dir"],
            instance1_config["remote_url"],
            instance1_config["poll_interval"],
            instance1_config["port"],
        ),
    )
    thread1.daemon = True
    thread1.start()

    # Start Instance 2 in a separate thread
    thread2 = threading.Thread(
        target=run_instance,
        args=(
            instance2_config["api_key"],
            instance2_config["local_sync_dir"],
            instance2_config["remote_url"],
            instance2_config["poll_interval"],
            instance2_config["port"],
        ),
    )
    thread2.daemon = True
    thread2.start()

    print("Starting both synchronization instances...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down synchronization services...")
        sys.exit(0)
