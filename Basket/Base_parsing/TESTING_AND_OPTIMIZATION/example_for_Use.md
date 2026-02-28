# Базовая команда
python scraper.py --url http://quotes.toscrape.com --output my_quotes

# С дополнительными параметрами
python scraper.py \
    --url http://quotes.toscrape.com \
    --output quotes \
    --delay 3 \
    --format json csv txt \
    --config custom_config.yaml

# Создание конфигурации по умолчанию
python scraper.py --create-config

# Игнорирование robots.txt
python scraper.py --url http://quotes.toscrape.com --output data --no-robots

# Ограничение количества страниц
python scraper.py --url http://quotes.toscrape.com --max-pages 5