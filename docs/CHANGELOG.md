# Changelog

Все значимые изменения в проекте c2pax документируются в этом файле в соответствии с правилами `user_global` (#2).

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/), проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

---

## [0.1.0] - 2026-08-17

### Добавлено
- Инициализация архитектуры проекта и модульной структуры c2pax (Python 3.10+).
- **Core Models (`c2pax.core.models`)**: Реализация легковесных моделей со `slots=True`: `AssetMetadata`, `IdentityInfo`, `AIProvenance`, `PermissionsInfo`, `ManifestStatus`, `AssetInfo`.
- **Provenance DAG Engine (`c2pax.core.provenance`)**: Реализация ориентированного ациклического графа (`ProvenanceGraph`, `ProvenanceNode`, `ProvenanceEdge`, `Action`, `Relationship`) с обходом предков `ancestors()` и защитой от циклов.
- **Universal AssetSource (`c2pax.core.source`)**: Потокобезопасный адаптер источников данных (`str`, `Path`, `bytes`, `BinaryIO`, `SpooledTemporaryFile`) с zero-copy и контекстной буферизацией для C/Rust FFI bindings.
- **Backend Abstraction (`c2pax.backend`)**: Слой абстракции `BaseC2paBackend`, адаптер к `c2pa-python` (`C2paRsBackend`) и изолированный `MockC2paBackend` для детерминированного тестирования.
- **Verification System (`c2pax.verification`)**: `VerificationStatus`, настраиваемые политики `VerificationPolicy` (permissive, standard, strict), локальное хранилище сертификатов `TrustStore` (PEM, каталоги, TSA) и генератор понятных вердиктов `VerificationResult.explain()`.
- **Декларативная инспекция и верификация (`c2pax.api`)**: Фасадные методы `inspect()` и `verify()`.
- **Semantic Diff Engine (`c2pax.diff`)**: Нормализованное семантическое сравнение ассетов `c2pax.diff()` (`SemanticDiff`).
- **Signing & Builder API (`c2pax.signing`)**: `Signer` (X.509 + private key), декларативный `Builder` с fluent interface и функция быстрого подписания `c2pax.sign()`.
- **Rich CLI (`c2pax.cli`)**: Команды `inspect` (дерево DAG, панели Identity/AI/Permissions), `verify` (стандартизированные exit codes 0..4), `diff` и `sign` с поддержкой `--json`.
- **Интеграции (`c2pax.integrations`)**: Pydantic v2 схемы (`c2pax.integrations.pydantic`), асинхронные потоковые хэндлеры FastAPI (`c2pax.integrations.fastapi`) и пакетная валидация `verify_many`/`verify_directory`.
- **Архитектурная документация**: `CORE_ARCHITECTURE.md`, `VERIFICATION_ARCHITECTURE.md`, `PROVENANCE_ARCHITECTURE.md`, `SIGNING_ARCHITECTURE.md`, `INTEGRATION_ARCHITECTURE.md`, `CLI_ARCHITECTURE.md`.
- **Лицензирование**: Установлена лицензия **Apache License 2.0** (`LICENSE`, `pyproject.toml`, `README.md`).
- **Безопасность и защита репозитория (`user_global` #32)**:
  - Создана политика безопасности [SECURITY.md](SECURITY.md) с регламентом Vulnerability Reporting и моделью угроз C2PA.
  - Настроен защищенный [.gitignore](.gitignore) для предотвращения утечки приватных ключей (`*.key`, `*.pem`, `*.pfx`), секретов и кэш-файлов в публичный репозиторий.
  - Реализовано маскирование приватных ключей (`***REDACTED***`) в `Signer.__repr__` и `__str__` для защиты от логирования секретов.
  - Внедрено ограничение максимальной глубины (`max_depth`) и защита от переполнения стека при обходе DAG в `ProvenanceGraph`.
  - Добавлены GitHub Actions workflows для CI тестирования (`.github/workflows/ci.yml`) и автоматического аудита безопасности (`.github/workflows/security.yml` с Bandit и pip-audit).
- **Документация и интернационализация**:
  - Добавлена англоязычная версия документации [README.en.md](README.en.md) с двусторонней навигацией.
  - Добавлен расширенный набор бейджей в `README.md` и `README.en.md` (License, Python 3.10+, PyPI, CI, Mypy Strict, Ruff, Security Hardened, C2PA Compliant, PRs Welcome).
  - Добавлен раздел «Сторонние репозитории и благодарности» с указанием всех используемых библиотек (`c2pa-python`, `c2pa-rs`, `cryptography`, `rich`, `click`, `pydantic`, `fastapi`) и их лицензий.
- **CI/CD и исправления безопасности**:
  - Обновлены workflows [ci.yml](.github/workflows/ci.yml) и [security.yml](.github/workflows/security.yml): принудительное обновление `setuptools>=83.0.0` для устранения уязвимости `PYSEC-2026-3447` в раннерах GitHub Actions.
  - Проведено форматирование всей кодовой базы с помощью `ruff format` (`src/c2pax/backend/c2pa_rs.py`).
- **Тестовый комплекс**: Юнит-, интеграционные и security-тесты на поврежденные/поддельные ассеты.
