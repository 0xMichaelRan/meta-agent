import os
import requests
from flask import Flask, request, jsonify
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time

# Configuration
API_KEY = "your_api_key"  # Replace with your actual API key
LOCAL_SYNC_DIR = "test_folder/metaagent"  # Replace with your local folder
REMOTE_URL = "http://127.0.0.1:5000"  # Replace with your VPS URL
POLL_INTERVAL = 5  # Interval for polling remote changes (seconds)

# Flask App
app = Flask(__name__)


@app.route("/sync", methods=["POST"])
def sync_endpoint():
    """API Endpoint to handle file synchronization requests."""
    if request.headers.get("Authorization") != f"Bearer {API_KEY}":
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    action = data.get("action")
    file_path = data.get("file_path")
    file_content = data.get("file_content")

    if action == "upload":
        # Save the uploaded file to the local sync directory
        local_path = os.path.join(LOCAL_SYNC_DIR, file_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(file_content.encode())
        return jsonify({"message": "File uploaded successfully"}), 200

    elif action == "delete":
        # Delete the file locally
        local_path = os.path.join(LOCAL_SYNC_DIR, file_path)
        if os.path.exists(local_path):
            os.remove(local_path)
        return jsonify({"message": "File deleted successfully"}), 200

    return jsonify({"error": "Invalid action"}), 400


def upload_file(file_path):
    """Upload a file to the remote server."""
    with open(file_path, "rb") as f:
        content = f.read()

    file_relative_path = os.path.relpath(file_path, LOCAL_SYNC_DIR)
    response = requests.post(
        f"{REMOTE_URL}/sync",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "action": "upload",
            "file_path": file_relative_path,
            "file_content": content.decode(),
        },
    )
    if response.status_code != 200:
        print(f"Failed to upload {file_path}: {response.text}")


class WatchdogHandler(FileSystemEventHandler):
    """Handler for Watchdog events."""

    def on_modified(self, event):
        if not event.is_directory:
            print(f"File modified: {event.src_path}")
            upload_file(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            print(f"File created: {event.src_path}")
            upload_file(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            file_relative_path = os.path.relpath(event.src_path, LOCAL_SYNC_DIR)
            response = requests.post(
                f"{REMOTE_URL}/sync",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={"action": "delete", "file_path": file_relative_path},
            )
            if response.status_code != 200:
                print(f"Failed to delete {event.src_path}: {response.text}")


def start_watchdog():
    """Start Watchdog observer."""
    event_handler = WatchdogHandler()
    observer = Observer()
    observer.schedule(event_handler, path=LOCAL_SYNC_DIR, recursive=True)
    observer.start()
    print("Watchdog is monitoring the local folder...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


# If the remote server is also running the same service and can push updates to this client via the Flask API, polling is not necessary.
# If the remote server does not actively notify the client about changes, polling ensures that local changes are in sync with the remote directory.
def start_polling_remote():
    """Poll the remote server for changes."""
    while True:
        try:
            response = requests.get(
                f"{REMOTE_URL}/poll",
                headers={"Authorization": f"Bearer {API_KEY}"},
            )
            if response.status_code == 200:
                print("Remote changes detected, handling them...")
                # Handle remote changes here (e.g., downloading new files)
        except Exception as e:
            print(f"Error polling remote: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    # Start Flask app in a separate thread
    flask_thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000))
    flask_thread.daemon = True
    flask_thread.start()

    # Start Watchdog in the main thread
    print("MetaAgent service is starting...")
    start_watchdog()
