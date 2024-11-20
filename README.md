# Poetry Setup

```
poetry new metaagent-script-flask
poetry add flask requests watchdog
```

## Run locally

```
poetry shell
python metaagent_script_flask/sync_service.py
```

## Test Upload

```
curl -X POST http://127.0.0.1:5000/sync \
     -H "Authorization: Bearer your_api_key" \
     -H "Content-Type: application/json" \
     -d '{
           "action": "upload",
           "file_path": "test_file.txt",
           "file_content": "This is a test file content."
         }'
```

Verify the file appears.

## Test Deletion

```
curl -X POST http://127.0.0.1:5000/sync \
     -H "Authorization: Bearer your_api_key" \
     -H "Content-Type: application/json" \
     -d '{
           "action": "delete",
           "file_path": "test_file.txt"
         }'
```

Verify the file is removed.
