import os
import requests
from flask import Flask, request, jsonify
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time

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

        # Flask App
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route("/sync", methods=["POST"])
        def sync_endpoint():
            """API Endpoint to handle file synchronization requests."""
            if request.headers.get("Authorization") != f"Bearer {self.API_KEY}":
                return jsonify({"error": "Unauthorized"}), 401

            data = request.json
            action = data.get("action")
            file_path = data.get("file_path")
            file_content = data.get("file_content")

            if action == "upload":
                # Save the uploaded file to the local sync directory
                local_path = os.path.join(self.LOCAL_SYNC_DIR, file_path)
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, "wb") as f:
                    f.write(file_content.encode())
                print(f"File uploaded: {local_path}")
                return jsonify({"message": "File uploaded successfully"}), 200

            elif action == "delete":
                # Delete the file locally
                local_path = os.path.join(self.LOCAL_SYNC_DIR, file_path)
                if os.path.exists(local_path):
                    os.remove(local_path)
                    print(f"File deleted: {local_path}")
                return jsonify({"message": "File deleted successfully"}), 200

            return jsonify({"error": "Invalid action"}), 400
        
        @self.app.route("/poll", methods=["GET"])
        def poll_remote():
            """Simulate remote changes."""
            if request.headers.get("Authorization") != f"Bearer {self.API_KEY}":
                return jsonify({"error": "Unauthorized"}), 401

            # Mock remote changes
            changes = [
                {"action": "upload", "file_path": "remote_file.txt", "file_content": "Remote content"},
                {"action": "delete", "file_path": "old_file.txt"}
            ]
            return jsonify(changes), 200


    def upload_file(self, file_path):
        """Upload a file to the remote server."""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
        except FileNotFoundError:
            print(f"File not found: {file_path}")
            return

        file_relative_path = os.path.relpath(file_path, self.LOCAL_SYNC_DIR)
        try:
            response = requests.post(
                f"{self.REMOTE_URL}/sync",
                headers={"Authorization": f"Bearer {self.API_KEY}"},
                json={
                    "action": "upload",
                    "file_path": file_relative_path,
                    "file_content": content.decode(),
                },
            )
            if response.status_code != 200:
                print(f"Failed to upload {file_path}: {response.text}")
            else:
                print(f"Uploaded file: {file_relative_path}")
        except requests.exceptions.RequestException as e:
            print(f"Error uploading file {file_path}: {e}")

    def delete_file(self, file_path):
        """Delete a file on the remote server."""
        file_relative_path = os.path.relpath(file_path, self.LOCAL_SYNC_DIR)
        try:
            response = requests.post(
                f"{self.REMOTE_URL}/sync",
                headers={"Authorization": f"Bearer {self.API_KEY}"},
                json={"action": "delete", "file_path": file_relative_path},
            )
            if response.status_code != 200:
                print(f"Failed to delete {file_path}: {response.text}")
            else:
                print(f"Deleted file: {file_relative_path}")
        except requests.exceptions.RequestException as e:
            print(f"Error deleting file {file_path}: {e}")

    class WatchdogHandler(FileSystemEventHandler):
        """Handler for Watchdog events."""

        def __init__(self, service):
            self.service = service

        def on_modified(self, event):
            if not event.is_directory:
                print(f"File modified: {event.src_path}")
                self.service.upload_file(event.src_path)

        def on_created(self, event):
            if not event.is_directory:
                print(f"File created: {event.src_path}")
                self.service.upload_file(event.src_path)

        def on_deleted(self, event):
            if not event.is_directory:
                print(f"File deleted: {event.src_path}")
                self.service.delete_file(event.src_path)

    def start_watchdog(self):
        """Start Watchdog observer."""
        event_handler = self.WatchdogHandler(self)
        observer = Observer()
        observer.schedule(event_handler, path=self.LOCAL_SYNC_DIR, recursive=True)
        observer.start()
        print(f"Watchdog is monitoring the folder: {self.LOCAL_SYNC_DIR}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
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
                    print("Remote changes detected, handling them...")
                    # Handle remote changes here (e.g., downloading new files)
            except Exception as e:
                print(f"Error polling remote: {e}")
            time.sleep(self.POLL_INTERVAL)

    def run_flask(self):
        """Run the Flask app."""
        self.app.run(host="0.0.0.0", port=self.PORT)

    def start(self):
        """Start the synchronization service."""
        # Start Flask app in a separate thread
        flask_thread = threading.Thread(target=self.run_flask)
        flask_thread.daemon = True
        flask_thread.start()

        # Start polling in a separate thread
        polling_thread = threading.Thread(target=self.start_polling_remote)
        polling_thread.daemon = True
        polling_thread.start()

        # Start Watchdog in the main thread
        print("MetaAgent service is starting...")
        self.start_watchdog()


# Main Execution Block
if __name__ == "__main__":
    # Configuration for a Single Instance
    config = {
        "api_key": "your_api_key",  # Replace with your actual API key
        "local_sync_dir": "test_folder/metaagent",  # Replace with your local folder
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
