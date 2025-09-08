# PG SQL Advisor MVP — VTB

Проект состоит из двух частей:

- Backend (`pg-sql-advisor-mvp/`) — FastAPI‑сервис, который принимает SQL, делает EXPLAIN, извлекает признаки, применяет правила и возвращает рекомендации и риск.
- Frontend (`front/`) — SPA на React + Vite для интерактивного анализа запросов (на текущем этапе использует мок‑данные).

## Содержание

- Описание
- Архитектура
- Быстрый старт
  - Backend
  - Frontend
- Конфигурация окружения
- REST API (backend)
- Разработка и тестирование
- Структура репозитория

## Описание

MVP помощника по оптимизации PostgreSQL‑запросов. Сервис принимает SQL, строит план выполнения (`EXPLAIN`), извлекает признаки, прогоняет их через набор Yaml‑правил и формирует рекомендации с оценкой риска.

## Архитектура

- `FastAPI` приложение (`src/app.py`):
  - `/health` — проверка здоровья
  - `/advise` — совет по заранее извлеченным фичам (низкоуровневый)
  - `/advise/sql` — основной эндпоинт: принимает сырой SQL, делает `EXPLAIN`, нормализует фичи, тянет контекст (статистику/настройки), применяет правила и возвращает рекомендации и риск
  - `/sql/run`, `/sql/explain` — утилитарные эндпоинты для отладки
  - `/debug/*` — служебные эндпоинты для диагностики
- Извлечение признаков: `src/analyzer/extract.py`
- Правила и движок правил: `src/advisor/rule_engine.py`, `src/advisor/rules_loader.py`, правила `src/rules/ruleset-v1/*.yaml`
- Оценка риска: `src/advisor/risk_score.py`
- Работа с БД/EXPLAIN: `src/db/pg.py`
- Модели схемы: `src/models.py`
- Презентация/рендер отчета: `src/presentation/formatter.py`, `src/advisor/explainer.py`

## Быстрый старт

### Требования

- Python 3.10+
- Node.js 20+ и Yarn (для фронтенда)
- Доступный PostgreSQL (локально или по `DATABASE_URL`)

### Backend

Перейдите в каталог backend и запустите сервис.

Вариант 1 — без poetry:

```bash
cd pg-sql-advisor-mvp
python -m uvicorn src.app:app --reload --port 8000
```

Вариант 2 — с poetry:

```bash
cd pg-sql-advisor-mvp
poetry install
poetry run python -m uvicorn src.app:app --reload --port 8000
```

Сервис поднимется на `http://localhost:8000`.
Проверка здоровья:

```bash
curl http://localhost:8000/health
```

### Frontend

Запустите SPA для UI.

```bash
cd front
# если нет yarn: npm install -g yarn
npm install yarn
yarn
yarn dev
```

UI поднимется на `http://localhost:5173` (порт Vite по умолчанию).

Примечание: текущий фронтенд работает на мок‑данных (`front/src/mock`), интеграцию с backend можно добавить позднее, указав API‑базу и вызовы к `/advise/sql`.

## Конфигурация окружения (Backend)

Backend читает параметры подключения к БД из переменных окружения или `.env` (подхватывается через `dotenv`):

- `DATABASE_URL` — полный URL подключения. Если задан, имеет приоритет.
  Пример: `postgresql://user:password@localhost:5432/dbname`
- Либо по отдельности:
  - `DB_HOST` (default `localhost`)
  - `DB_PORT` (default `5432`)
  - `DB_NAME` (default `pagila`)
  - `DB_USER` (default `postgres`)
  - `DB_PASSWORD` (default задан в `src/db/pg.py`, переопределите!)

Выполнение запросов и EXPLAIN выполняется в search_path `public` по умолчанию и с таймаутами, управляемыми параметрами эндпоинтов.

## REST API (Backend)

База: `http://localhost:8000`

- `GET /health`

  - Ответ: `{ "ok": true }`

- `POST /advise`

  - Вход: `AdviseInput` (низкоуровневый, если у вас уже есть фичи)
  - Выход: `AdviseResponse` (risk, recommendations, explain_md)

- `POST /advise/sql`
  - Назначение: основной сценарий анализа сырого SQL
  - Query‑параметры:
    - `out_format` = `json|md` (default `json`)
    - `verbosity` = `short|full` (default `short`)
    - `include_plan` = `true|false` (default `true`)
    - `include_features` = `true|false` (default `true`)
  - Тело запроса:

```json
{
  "sql": "SELECT * FROM film ORDER BY random() LIMIT 10",
  "analyze": false,
  "timeout_ms": 5000,
  "searchPath": "public"
}
```

- Пример запроса:

```bash
curl -s "http://localhost:8000/advise/sql?out_format=json&verbosity=short&include_plan=true&include_features=true" \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT * FROM film ORDER BY random() LIMIT 10","analyze":false,"timeout_ms":5000,"searchPath":"public"}' | jq .
```

- Ответ: JSON с полями `risk`, `recommendations`, `explain_md`, опционально `plan`, `features`, `dbSettings`.

- `POST /sql/run`

  - Выполняет произвольный SQL (по умолчанию только SELECT).

- `POST /sql/explain`

  - Возвращает план выполнения в формате JSON или текст.

- `GET /debug/db_source`, `GET /debug/rules`, `POST /debug/*`
  - Отладочные/диагностические эндпоинты.

Открыть интерактивную документацию Swagger:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Разработка и тестирование

### Backend

Зависимости описаны в `pyproject.toml` (Poetry). Основной запуск через Uvicorn (см. выше).

Тесты (smoke):

```bash
cd pg-sql-advisor-mvp
python -m pytest -q
```

### Frontend

Скрипты:

- `yarn dev` — локальная разработка
- `yarn build` — билд
- `yarn preview` — предпросмотр билда
- `yarn lint` — ESLint
- `yarn format` / `yarn format:check` — Prettier

## Структура репозитория

- `pg-sql-advisor-mvp/` — backend (FastAPI, правила, анализатор)
  - `src/app.py` — приложение и REST API
  - `src/analyzer/` — извлечение признаков из плана/SQL
  - `src/advisor/` — правило‑движок, загрузка правил, риск‑скор
  - `src/presentation/` — форматирование отчёта
  - `src/db/` — подключение к PostgreSQL, EXPLAIN
  - `src/rules/ruleset-v1/*.yaml` — набор правил
  - `tests/` — базовые тесты
- `front/` — SPA на React + Vite (на мок‑данных)
  - `src/pages/Analyzer.tsx`, `src/pages/History.tsx` — основные страницы
  - `src/components/analyzer/*` — UI‑компоненты анализатора
  - `src/mock/*` — мок‑данные

## Примечания

- В `src/db/pg.py` по умолчанию выставлен пароль для локальной разработки — обязательно переопределите через переменные окружения/`.env`.
- Dockerfile и docker‑compose для backend в репозитории зарезервированы; при необходимости можно добавить контейнеризацию под ваш стенд.

### Примечение по подключению к БД

> Если вы запускаете и бэк, и фронт на одном устройстве, то возможно для корректного соединения с БД вам придётся изменить файл pg_hba.conf. Нужно задать следующие правила:

```conf
# IPv4 local connections:
host all all 127.0.0.1/32 scram-sha-256
# IPv6 local connections:
host all all ::1/128 scram-sha-256
```

> То есть изменить для IPv4 и для IPv6 настройку METHOD с trust на scram-sha-256.
>
> Узнать расположение файла можно сделав следующие SQL запросы:

```sql
SHOW hba_file;

SELECT current_setting('hba_file');
```
