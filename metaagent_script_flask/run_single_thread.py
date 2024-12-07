import json
import signal
import sys
import argparse
from daemon_service import FileSyncService


def load_config(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


if __name__ == "__main__":
    def signal_handler(sig, frame):
        print("Shutting down gracefully...")
        sys.exit(0)

    # Add argument parser
    parser = argparse.ArgumentParser(description='Run FileSyncService')
    parser.add_argument('-t', '--test', action='store_true', 
                       help='Run in test mode (no file sync)')
    args = parser.parse_args()

    # Handle termination signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Load configuration from JSON file
    config = load_config("macbook_single_thread_run.json")

    # Create and start the service
    service = FileSyncService(
        api_key=config["api_key"],
        local_sync_dir=config["local_sync_dir"],
        remote_url=config["remote_url"],
        poll_interval=config["poll_interval"],
        port=config["port"],
        test_mode=args.test  # Pass test mode parameter
    )
    
    print(f"Starting synchronization service... {'(Test Mode)' if args.test else ''}")
    service.start() 