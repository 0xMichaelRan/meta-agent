import json
import signal
import sys
import argparse
from sync_script import FileSyncService


def load_config(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


if __name__ == "__main__":
    def signal_handler(sig, frame):
        print("Shutting down gracefully...")
        sys.exit(0)

    # Add argument parser
    parser = argparse.ArgumentParser(description='Run FileSyncService')
    parser.add_argument('--mode', type=str, choices=['test', 'server', 'prod'],
                       default='test',
                       help='Run mode: test (default, no sync), server (handle incoming only), or prod (do full sync)')
    args = parser.parse_args()

    # Handle termination signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Load configuration from JSON file
    config = load_config("config/macbook3_prod_run.json")

    # Create and start the service
    service = FileSyncService(
        api_key=config["api_key"],
        local_sync_dir=config["local_sync_dir"],
        remote_url=config["remote_url"],
        poll_interval=config["poll_interval"],
        port=config["port"],
        mode=args.mode  # Pass mode parameter instead of test_mode
    )
    
    print(f"Starting synchronization service... ({args.mode.upper()} Mode)")
    service.start() 