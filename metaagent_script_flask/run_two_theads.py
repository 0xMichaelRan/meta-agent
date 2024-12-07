import json
import threading
import time
from daemon_service import FileSyncService
import signal
import sys


def load_config(file_path):
    with open(file_path, "r") as file:
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
    client_config = load_config("config/thread_client_config.json")
    master_config = load_config("config/thread_master_config.json")

    # Start Instance 1 in a separate thread
    thread1 = threading.Thread(
        target=run_instance,
        args=(
            client_config["api_key"],
            client_config["local_sync_dir"],
            client_config["remote_url"],
            client_config["poll_interval"],
            client_config["port"],
        ),
    )
    thread1.daemon = True
    thread1.start()

    # Start Instance 2 in a separate thread
    thread2 = threading.Thread(
        target=run_instance,
        args=(
            master_config["api_key"],
            master_config["local_sync_dir"],
            master_config["remote_url"],
            master_config["poll_interval"],
            master_config["port"],
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
