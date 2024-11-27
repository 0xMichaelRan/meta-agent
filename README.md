# How it works

This is a file sync service that allows you to sync files between a local directory and a remote server.

1. Client-to-Server Sync:

    The client detects local file changes using Watchdog and sends these changes to the server via HTTP requests.

    The server processes these requests and updates its local directory accordingly.

2. Server-to-Client Sync:

    The client periodically polls the server for any changes using the /poll endpoint.

    The server responds with a list of changes that the client needs to apply locally.

3. Synchronization State Management:

    The service uses a dictionary (syncing_files) to track files currently being synchronized, preventing duplicate operations and sync loops.

## Setup

```
poetry new metaagent-script-flask
poetry add flask requests watchdog python-dotenv
```

## Run 1 instance

```
poetry shell
python metaagent_script_flask/daemon_service.py
```

Curl test upload: 

```
curl -X POST http://127.0.0.1:3459/sync \
     -H "Authorization: Bearer your_api_key" \
     -H "Content-Type: application/json" \
     -d '{
           "action": "upload",
           "file_path": "single_daemon_service_test_file.txt",
           "file_content": "This is a test file content."
         }'
```

Verify a new file appears. Then Curl test deletion:

```
curl -X POST http://127.0.0.1:3459/sync \
     -H "Authorization: Bearer your_api_key" \
     -H "Content-Type: application/json" \
     -d '{
           "action": "delete",
           "file_path": "single_daemon_service_test_file.txt"
         }'
```

Verify the file is removed.

## Run 2 instances

```
poetry shell
python metaagent_script_flask/run_two_theads.py
```

# Use it in Cloudc:

1. Add remote_url to .env, get it from Cloudflare.

2. Change this line to a local dir:

    ```
    "local_sync_dir": "this_is_line_432_in_daemon_service.py",
    ```

3. Run script like this:

    ```
    poetry run python metaagent_script_flask/daemon_service.py
    ```

## TODO

- All file sync feature is working.
- Client will upload all files to server during startup, no version checking, just replace everything.
- Folder deletion not working.
- Folder rename is working except old folder will remain on master as a empty folder.
