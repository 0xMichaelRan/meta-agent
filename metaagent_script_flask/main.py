import threading
import time
from sync_service import FileSyncService

def run_instance(api_key, local_sync_dir, remote_url, poll_interval, port):
    service = FileSyncService(
        api_key=api_key,
        local_sync_dir=local_sync_dir,
        remote_url=remote_url,
        poll_interval=poll_interval,
        port=port
    )
    service.start()

if __name__ == "__main__":
    # Configuration for Instance 1
    instance1_config = {
        "api_key": "test_api_key",
        "local_sync_dir": "test_folder/metaagent1",
        "remote_url": "http://127.0.0.1:3461",  # Points to Instance 2
        "poll_interval": 5,
        "port": 3459
    }

    # Configuration for Instance 2
    instance2_config = {
        "api_key": "test_api_key",
        "local_sync_dir": "test_folder/metaagent2",
        "remote_url": "http://127.0.0.1:3459",  # Points to Instance 1
        "poll_interval": 5,
        "port": 3461
    }

    # Start Instance 1 in a separate thread
    thread1 = threading.Thread(
        target=run_instance,
        args=(
            instance1_config["api_key"],
            instance1_config["local_sync_dir"],
            instance1_config["remote_url"],
            instance1_config["poll_interval"],
            instance1_config["port"]
        )
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
            instance2_config["port"]
        )
    )
    thread2.daemon = True
    thread2.start()

    # Keep the main thread alive to allow both instances to run
    print("Starting both synchronization instances...")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("Shutting down synchronization services...") 