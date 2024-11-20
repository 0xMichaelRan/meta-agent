import os
import requests
from flask import Flask, request, jsonify
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time
import logging
from datetime import datetime

class FileSyncService:
    def __init__(self, api_key, local_sync_dir, remote_url, poll_interval, port):
        # Configuration
        self.API_KEY = api_key
        self.LOCAL_SYNC_DIR = local_sync_dir
        self.REMOTE_URL = remote_url
        self.POLL_INTERVAL = poll_interval
        self.PORT = port

        # Ensure the local sync directory exists
        os.makedirs(self.LOCAL_SYNC_DIR, exist_ok=True)

        # Track files being synced to prevent loops
        self.syncing_files = set()
        self.sync_lock = threading.Lock()

        # Setup logging
        self._setup_logging()
        
        # Flask App
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_logging(self):
        """Configure logging with proper formatting."""
        class PortFormatter(logging.Formatter):
            def __init__(self, fmt, port):
                super().__init__(fmt)
                self.port = port

            def format(self, record):
                if not hasattr(record, 'port'):
                    record.port = self.port
                return super().format(record)

        # Create formatter with port number
        formatter = PortFormatter(
            '%(asctime)s - [%(levelname)s] - [Port:%(port)s] %(message)s',
            self.PORT
        )

        # Setup handlers
        file_handler = logging.FileHandler(f'sync_service_{self.PORT}.log')
        file_handler.setFormatter(formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # Setup logger
        self.logger = logging.getLogger(f'FileSyncService_{self.PORT}')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.propagate = False

    def is_file_syncing(self, file_path):
        """Check if a file is currently being synced."""
        with self.sync_lock:
            is_syncing = file_path in self.syncing_files
            self.logger.debug(f"Checking sync status for {file_path}: {'syncing' if is_syncing else 'not syncing'}")
            return is_syncing

    def mark_file_syncing(self, file_path):
        """Mark a file as being synced."""
        with self.sync_lock:
            self.syncing_files.add(file_path)
            self.logger.debug(f"🔒 Marked file as syncing: {file_path}")
            self.logger.debug(f"Currently syncing files: {self.syncing_files}")

    def unmark_file_syncing(self, file_path):
        """Unmark a file as being synced."""
        with self.sync_lock:
            self.syncing_files.discard(file_path)
            self.logger.debug(f"🔓 Unmarked file from syncing: {file_path}")
            self.logger.debug(f"Currently syncing files: {self.syncing_files}")

    def _setup_routes(self):
        @self.app.route("/sync", methods=["POST"])
        def sync_endpoint():
            """Handle incoming sync requests."""
            auth_header = request.headers.get("Authorization")
            if auth_header != f"Bearer {self.API_KEY}":
                self.logger.warning("❌ Unauthorized sync attempt")
                return jsonify({"error": "Unauthorized"}), 401

            data = request.json
            action = data.get("action")
            file_path = data.get("file_path")
            
            self.logger.info(f"📥 Received sync request: {action} for {file_path}")
            
            if not action or not file_path:
                self.logger.error("❌ Invalid sync request data")
                return jsonify({"error": "Invalid data"}), 400

            try:
                self.mark_file_syncing(file_path)
                local_path = os.path.join(self.LOCAL_SYNC_DIR, file_path)

                if action == "upload":
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    with open(local_path, "wb") as f:
                        f.write(data["file_content"].encode())
                    self.logger.info(f"✅ Successfully synced file: {file_path}")
                    return jsonify({"status": "success"}), 200

                elif action == "delete":
                    if os.path.exists(local_path):
                        os.remove(local_path)
                        self.logger.info(f"🗑️ Successfully deleted file: {file_path}")
                    else:
                        self.logger.warning(f"⚠️ File already deleted: {file_path}")
                    return jsonify({"status": "success"}), 200

            except Exception as e:
                self.logger.error(f"❌ Sync error for {file_path}: {str(e)}", exc_info=True)
                return jsonify({"error": str(e)}), 500
            finally:
                self.unmark_file_syncing(file_path)

        @self.app.route("/poll", methods=["GET"])
        def poll_endpoint():
            """Handle polling requests for changes."""
            auth_header = request.headers.get("Authorization")
            if auth_header != f"Bearer {self.API_KEY}":
                self.logger.warning("❌ Unauthorized poll attempt")
                return jsonify({"error": "Unauthorized"}), 401

            # Return empty response if no changes
            return jsonify([]), 200

    def upload_file(self, file_path):
        """Upload a file to remote instance."""
        if self.is_file_syncing(file_path):
            self.logger.debug(f"Skipping upload of syncing file: {file_path}")
            return

        try:
            full_path = os.path.join(self.LOCAL_SYNC_DIR, file_path)
            with open(full_path, 'rb') as f:
                content = f.read()

            response = requests.post(
                f"{self.REMOTE_URL}/sync",
                headers={"Authorization": f"Bearer {self.API_KEY}"},
                json={
                    "action": "upload",
                    "file_path": file_path,
                    "file_content": content.decode('utf-8', errors='ignore')
                },
                timeout=10
            )
            
            if response.status_code != 200:
                self.logger.error(f"Failed to upload {file_path}: {response.text}")

        except Exception as e:
            self.logger.error(f"Error uploading {file_path}: {str(e)}")

    def delete_file(self, file_path):
        """Delete a file from remote instance."""
        if self.is_file_syncing(file_path):
            self.logger.debug(f"Skipping deletion of syncing file: {file_path}")
            return

        try:
            response = requests.post(
                f"{self.REMOTE_URL}/sync",
                headers={"Authorization": f"Bearer {self.API_KEY}"},
                json={
                    "action": "delete",
                    "file_path": file_path
                },
                timeout=10
            )
            
            if response.status_code != 200:
                self.logger.error(f"Failed to delete {file_path}: {response.text}")

        except Exception as e:
            self.logger.error(f"Error deleting {file_path}: {str(e)}")

    class WatchdogHandler(FileSystemEventHandler):
        def __init__(self, service):
            super().__init__()
            self.service = service
            self.service.logger.info("🔍 Watchdog handler initialized")

        def on_modified(self, event):
            if event.is_directory:
                return
            
            relative_path = os.path.relpath(event.src_path, self.service.LOCAL_SYNC_DIR)
            if not self.service.is_file_syncing(relative_path):
                self.service.logger.info(f"📝 File modified: {relative_path}")
                self.service.upload_file(relative_path)
            else:
                self.service.logger.debug(f"⏩ Skipping modified event for syncing file: {relative_path}")

        def on_created(self, event):
            if event.is_directory:
                return
            
            relative_path = os.path.relpath(event.src_path, self.service.LOCAL_SYNC_DIR)
            if not self.service.is_file_syncing(relative_path):
                self.service.logger.info(f"📄 File created: {relative_path}")
                self.service.upload_file(relative_path)
            else:
                self.service.logger.debug(f"⏩ Skipping created event for syncing file: {relative_path}")

        def on_deleted(self, event):
            if event.is_directory:
                return
            
            relative_path = os.path.relpath(event.src_path, self.service.LOCAL_SYNC_DIR)
            if not self.service.is_file_syncing(relative_path):
                self.service.logger.info(f"🗑️ File deleted: {relative_path}")
                self.service.delete_file(relative_path)
            else:
                self.service.logger.debug(f"⏩ Skipping deleted event for syncing file: {relative_path}")

    def start_watchdog(self):
        """Start Watchdog observer."""
        event_handler = self.WatchdogHandler(self)
        observer = Observer()
        observer.schedule(event_handler, path=self.LOCAL_SYNC_DIR, recursive=True)
        observer.start()
        self.logger.info(f"👀 Watchdog monitoring folder: {self.LOCAL_SYNC_DIR}")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            self.logger.info("⏹️ Watchdog observer stopped")
        observer.join()

    def start_polling_remote(self):
        """Poll the remote server for changes."""
        while True:
            try:
                response = requests.get(
                    f"{self.REMOTE_URL}/poll",
                    headers={"Authorization": f"Bearer {self.API_KEY}"},
                )
                if response.status_code == 200:
                    changes = response.json()
                    if changes:
                        self.logger.info(f"Remote changes detected: {changes}")
                        print("Remote changes detected, handling them...")
                        for change in changes:
                            action = change.get("action")
                            file_path = change.get("file_path")
                            file_content = change.get("file_content", "")
                            local_path = os.path.join(self.LOCAL_SYNC_DIR, file_path)

                            if action == "upload":
                                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                                try:
                                    with open(local_path, "wb") as f:
                                        f.write(file_content.encode())
                                    self.logger.info(f"Downloaded and saved file: {local_path}")
                                except Exception as e:
                                    self.logger.error(f"Error saving downloaded file {local_path}: {e}")

                            elif action == "delete":
                                if os.path.exists(local_path):
                                    try:
                                        os.remove(local_path)
                                        self.logger.info(f"Downloaded and deleted file: {local_path}")
                                    except Exception as e:
                                        self.logger.error(f"Error deleting downloaded file {local_path}: {e}")
                elif response.status_code == 204:
                    self.logger.info("No remote changes to poll.")
                else:
                    self.logger.error(f"Failed to poll remote: {response.status_code} {response.text}")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error polling remote: {e}")

            time.sleep(self.POLL_INTERVAL)

    def run_flask(self):
        """Run the Flask app."""
        self.app.run(host="0.0.0.0", port=self.PORT)

    def start(self):
        """Start the synchronization service."""
        self.logger.info("=== Starting Service Components ===")
        
        # Start Flask app in a separate thread
        flask_thread = threading.Thread(target=self.run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        self.logger.info(f"🌐 Flask server started on port {self.PORT}")

        # Start Watchdog in the main thread
        self.logger.info("🚀 MetaAgent service starting...")
        self.start_watchdog()


# Main Execution Block
if __name__ == "__main__":
    # Configuration for a Single Instance
    config = {
        "api_key": "your_api_key",  # Replace with your actual API key
        "local_sync_dir": "sync_folder/metaagent",  # Replace with your local folder
        "remote_url": "http://127.0.0.1:5000",  # Replace with your remote URL
        "poll_interval": 5,  # Interval for polling remote changes (seconds)
        "port": 3459  # Port number for this instance
    }

    # Instantiate and start the FileSyncService
    service = FileSyncService(
        api_key=config["api_key"],
        local_sync_dir=config["local_sync_dir"],
        remote_url=config["remote_url"],
        poll_interval=config["poll_interval"],
        port=config["port"]
    )
    service.start()
