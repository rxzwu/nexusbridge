# NexusBridgeHub — документация (RU)

[![PyPI version](https://img.shields.io/pypi/v/nexusbridgehub)](https://pypi.org/project/nexusbridgehub/)
[![Python 3.11–3.14](https://img.shields.io/pypi/pyversions/nexusbridgehub?label=python)](https://pypi.org/project/nexusbridgehub/)
[![Tests](https://github.com/rxzwu/nexusbridgehub/actions/workflows/ci.yml/badge.svg)](https://github.com/rxzwu/nexusbridgehub/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Универсальный мост для распределённого управления ботами: **бот → сервер → воркер пользователя**.

Тонкий слой поверх твоего проекта: вся тяжёлая логика остаётся локально, а команды приходят удалённо через центральный сервер.

> English docs: [README.md](README.md) · **Деплой на VPS:** [docs/DEPLOY.ru.md](docs/DEPLOY.ru.md) · **Проверка:** [docs/TESTING.ru.md](docs/TESTING.ru.md)

## Версии Python

| Версия | Статус |
|--------|--------|
| **3.10 и ниже** | Не поддерживается — `pip` откажется ставить пакет |
| **3.11 – 3.14** | Полная поддержка — каждый релиз прогоняется в CI на 3.11, 3.12, 3.13 и 3.14 |

Нужен **Python 3.11+**. Проверка: `python --version`.

## Архитектура

```
┌─────────────┐   JWT controller  ┌──────────────┐   JWT worker   ┌─────────────────┐
│ Telegram    │ ────────────────► │NexusBridgeHub│ ◄───────────── │ Worker на ПК    │
│ Bot / API   │                   │   Server     │                │ пользователя    │
└─────────────┘                   └──────────────┘                └─────────────────┘
```

| Компонент | Роль |
|-----------|------|
| **Server** | Маршрутизирует команды от бота к нужному воркеру |
| **BridgeClient** | Встраивается в проект на машине пользователя |
| **BridgeController** | Вызывает удалённые функции из бота или API |
| **WorkerApp** | Тонкий клиент; подключается по pair-коду без секретов в бинарнике |

## Установка

```bash
pip install nexusbridgehub
```

Из исходников (для разработки):

```bash
pip install -e ".[dev]"
```

## Быстрый старт (≈5 минут)

### 1. Сгенерируй секретный ключ

```bash
# Linux / macOS
openssl rand -hex 32

# PowerShell
-join ((48..57) + (65..70) | Get-Random -Count 32 | ForEach-Object {[char]$_})
```

Минимум **32 символа**.

### 2. Запусти сервер

**bash:**

```bash
export NEXUSBRIDGEHUB_JWT_SECRET="твой_длинный_секрет_32plus"
nexusbridgehub-server --host 0.0.0.0 --port 8765
```

**PowerShell:**

```powershell
$env:NEXUSBRIDGEHUB_JWT_SECRET = "твой_длинный_секрет_32plus"
nexusbridgehub-server --host 0.0.0.0 --port 8765
```

В логах должно появиться сообщение о запуске на порту `8765`.

**Прод на VPS (Hetzner / Contabo):** пошаговый гайд — [docs/DEPLOY.ru.md](docs/DEPLOY.ru.md) (systemd, TLS/WSS, firewall).

### 3. Минимальный тест (два воркера: RU + EN)

Готовые скрипты лежат в [`examples/minimal/`](examples/minimal/).

Подробная пошаговая инструкция: [`docs/TESTING.ru.md`](docs/TESTING.ru.md).

Кратко:

1. Сгенерируй JWT: `python examples/minimal/generate_tokens.py`
2. Запусти `worker_ru.py` и/или `worker_en.py`
3. Запусти `controller_ru.py` → ожидай `Привет, Мир!`
4. Запусти `controller_en.py` → ожидай `Hello, World!`

### 4. Встрой воркер в свой проект

```python
from nexusbridgehub import BridgeClient

bridge = BridgeClient(
    server_url="wss://bridge.example.com:8765",
    token=user_jwt,
    project_id="taskrelay",
    user_id=str(user_id),
)
bridge.register("run_task", run_task)
bridge.register("worker_status", get_worker_status)
await bridge.run()
```

### 5. Управляй из бота (контроллер)

```python
from nexusbridgehub import AuthManager, BridgeController
from nexusbridgehub.protocol import Role

auth = AuthManager(os.environ["NEXUSBRIDGEHUB_JWT_SECRET"])

# Pair-код для пользователя (показать в Telegram)
code = auth.create_pair_code(project_id="taskrelay", user_id=str(user_id))

# Вызов удалённой функции
bot_jwt = auth.create_token(
    role=Role.CONTROLLER,
    project_id="taskrelay",
    user_id=str(user_id),
)
ctrl = BridgeController(
    server_url="wss://bridge.example.com:8765",
    token=bot_jwt,
    project_id="taskrelay",
    user_id=str(user_id),
)
result = await ctrl.invoke("run_task", {"job_id": "job-42"})
```

### 6. Сборка standalone-бинарника для пользователей

Собери готовый исполняемый файл для распространения (Python не нужен на машине пользователя):

```bash
# Установи с зависимостями для сборки
pip install nexusbridgehub[builder]

# Собери воркер с зашифрованным URL сервера
nexusbridgehub --server-url wss://bridge.example.com:8765

# Сборка с кастомными хендлерами
nexusbridgehub \
    --server-url wss://bridge.example.com:8765 \
    --register-code handlers.py \
    --icon app.ico \
    --name myapp-worker
```

**Результат:** Один исполняемый файл в `./dist/` (Windows: `.exe`, macOS/Linux: бинарник)

**Возможности:**
- Зашифрованный URL сервера (AES-256-GCM + machine fingerprint)
- Встроенные кастомные команды
- Не требует установки Python
- Кросс-платформенность: Windows, macOS, Linux

Подробности: [docs/BUILD.md](docs/BUILD.md), автоматическая сборка для всех платформ: [docs/CI-CD.md](docs/CI-CD.md).

## Безопасность

- **JWT** — воркер и контроллер аутентифицируются токенами, секреты не зашиты в клиент
- **Pair-коды** — бот генерирует код, пользователь вводит в воркер → получает JWT
- **Шифрование URL** — AES-256-GCM + PBKDF2, адрес сервера не хранится открытым текстом в `.exe`

## Ошибки и логи

- Ошибка в **handler** (`run_task`, `say_hello`, …) не роняет воркер — возвращается `ok: false`, воркер продолжает слушать команды
- **Автопереподключение** при обрыве WebSocket (`BridgeClient`, `WorkerApp`)
- **Невалидные сообщения** логируются и пропускаются, сессия не падает
- Уровень логов: `NEXUSBRIDGEHUB_LOG_LEVEL=DEBUG` (по умолчанию `INFO`)

```bash
export NEXUSBRIDGEHUB_LOG_LEVEL=DEBUG
nexusbridgehub-server --host 0.0.0.0 --port 8765
```

## Протокол (WebSocket, JSON)

| Тип | Направление | Назначение |
|-----|-------------|------------|
| `register` | клиент → сервер | Регистрация воркера или контроллера |
| `invoke` | контроллер → воркер | Вызов зарегистрированной функции |
| `result` | воркер → контроллер | Ответ или ошибка |
| `pair_request` | воркер → сервер | Обмен pair-кода на JWT |

## FAQ

### Как получить токен для воркера?

Через `AuthManager.create_pair_code()` на стороне бота. Пользователь вводит код в воркер — сервер выдаёт JWT.

Для локального теста без pair-кода используй [`examples/minimal/generate_tokens.py`](examples/minimal/generate_tokens.py).

### Безопасно ли это?

JWT, pair-коды, шифрование URL. Сервер не хранит аккаунты и прокси пользователей — только маршрутизирует команды.

### Как задеплоить сервер в прод?

Пошаговая инструкция: [docs/DEPLOY.ru.md](docs/DEPLOY.ru.md) — VPS, systemd, Caddy/Nginx, WSS.

### Как обновить библиотеку?

```bash
pip install --upgrade nexusbridgehub
```

### Где пример интеграции в проект?

- Минимальный тест: [`examples/minimal/`](examples/minimal/)
- Шаблон воркера (EN): [`examples/worker_integration.py`](examples/worker_integration.py)
- Шаблон воркера (RU): [`examples/worker_integration.ru.py`](examples/worker_integration.ru.py)

## Разработка

```bash
pip install -e ".[dev]"
pytest
python -m build
python -m twine check dist/*
```

**Публикация на PyPI:** [docs/PUBLISH.ru.md](docs/PUBLISH.ru.md)

## Лицензия

MIT
