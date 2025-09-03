### Запуск без виртуального окружения
python -m uvicorn src.app:app --reload --port 8000

### Запуск с виртуальным окружением
poetry install
poetry run python -m uvicorn src.app:app --reload --port 8000