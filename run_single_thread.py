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
    
    try:
        parser.add_argument('--mode', type=str, choices=['test', 'server', 'prod'],
                           required=True,
                           help='Run mode: test (default, no sync), server (handle incoming only), or prod (do full sync)')
        parser.add_argument('--config', type=str, required=True,
                           help='Path to configuration JSON file')
        args = parser.parse_args()
    except SystemExit:
        print("\nExample usage:")
        print("--mode: 'test', 'server', or 'prod'")
        print("--config: config/macbook3_prod_run.json")
        sys.exit(1)

    # Handle termination signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Load configuration from JSON file
    config = load_config(args.config)

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