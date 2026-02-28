# Create Configuration file
#python production_ready.py --create-config
# Base enouch
python production_ready.py --url http://quotes.toscrape.com
# Advenced enouch
python production_ready.py \
    --url http://quotes.toscrape.com \
    --output my_quotes \
    --delay 2 \
    --format json csv txt \
    --max-pages 5 \
    --verbose
# Use Oun config File
python production_ready.py --config my_config.json