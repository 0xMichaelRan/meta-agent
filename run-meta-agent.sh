echo -ne "\033]0;hub/MetaAgent\007"
cd /usr/local/hub/metaagent
poetry run python metaagent_script_flask/run_single_thread.py -t
