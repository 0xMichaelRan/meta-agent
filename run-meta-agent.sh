echo -ne "\033]0;hub/MetaAgent\007"
cd /usr/local/hub/metaagent
poetry run python run_single_thread.py --mode test --config config/macbook3_prod_run.json
