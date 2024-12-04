        "local_sync_dir": "/Users/wei.ran/Documents/notes/",

        
echo -ne "\033]0;hub/metaagent\007"
cd /usr/local/hub/metaagent
poetry run python metaagent_script_flask/daemon_service.py
