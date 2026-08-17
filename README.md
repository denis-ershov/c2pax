# c2pax

<div align="center">

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![PyPI Version](https://img.shields.io/badge/pypi-v0.1.0-orange.svg)](https://pypi.org/project/c2pax/)
[![CI Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/denis-ershov/c2pax/actions)
[![Type Checked: Mypy Strict](https://img.shields.io/badge/type_checked-mypy_strict-brightgreen.svg)](https://mypy.readthedocs.io/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Security: Hardened](https://img.shields.io/badge/security-hardened-success.svg)](SECURITY.md)
[![C2PA Standard](https://img.shields.io/badge/C2PA-v1.3%20%7C%20v2.0%20Compliant-purple.svg)](https://c2pa.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/denis-ershov/c2pax/pulls)

**[English](README.en.md)** | **Русский**

</div>

---

**c2pax** — это высокоуровневый, эргономичный и строго типизированный Python SDK для инспекции, криптографической верификации, работы с графом происхождения (Provenance DAG), семантического дифференцирования и создания цифровых манифестов стандарта **C2PA (Content Credentials)**.

Библиотека выступает прикладным DX- и Verification-слоем над официальным движком `c2pa-python` (`c2pa-rs`), выстраивая строгое разделение между **декларативными данными** и **криптографическим доверием**:

```
                       C2PA Ecosystem (Rust core: c2pa-rs)
                                        │
                                   c2pa-python
                                        │
                                      c2pax
                                        │
          ┌─────────────────────────────┴─────────────────────────────┐
          │                                                           │
    c2pax.inspect()                                             c2pax.verify()
"Что задекларировано в манифесте?"                          "Можно ли этому доверять?"
 (Metadata, Provenance DAG, AI, Identity)                    (Policy, Integrity, TrustStore)
```

---

## Возможности

- 🔍 **Декларативная инспекция (`c2pax.inspect`)**: мгновенное извлечение метаданных, информации о создателе, промптов и моделей ИИ (`AIProvenance`), ограничений обучения нейросетей (`PermissionsInfo`).
- 🛡️ **Криптографическая верификация (`c2pax.verify`)**: проверка целостности хэшей JUMBF/CBOR, цифровых подписей клейма, локальное хранилище сертификатов `TrustStore` и настраиваемые политики `VerificationPolicy` (permissive, standard, strict).
- 🌳 **Граф происхождения как DAG (`ProvenanceGraph`)**: направленный ациклический граф истории правок и ингредиентов с защитой от циклических зависимостей (`ancestors()`, `descendants()`) и аппаратным лимитом глубины.
- ⚖️ **Семантический diff (`c2pax.diff`)**: сравнение двух версий ассета на уровне бизнес-сущностей (действия, ингредиенты, авторы, ИИ-декларации).
- ✍️ **Fluent Builder & Signer (`c2pax.Builder`, `c2pax.Signer`)**: удобный интерфейс для формирования манифестов, указания AI assertions, добавления ингредиентов и наложения подписи с безопасным маскированием закрытых ключей.
- 💻 **Богатый CLI интерфейс (`c2pax`)**: красивый рендеринг дерева происхождения, сводок и таблиц на базе `Rich`, стандартизированные коды возврата (0..4) и поддержка `--json` для CI/CD.
- 🚀 **Экосистемные интеграции**:
  - `c2pax[fastapi]` — асинхронные потоковые хэндлеры для `UploadFile` без избыточного копирования в память;
  - `c2pax[pydantic]` — строгие Pydantic v2 схемы для валидации и сериализации;
  - Пакетная параллельная обработка `verify_many` и `verify_directory`.

---

## Установка

```bash
# Базовый легковесный SDK (только dataclasses и криптография)
pip install c2pax

# С поддержкой Rich CLI
pip install "c2pax[cli]"

# С поддержкой Pydantic v2
pip install "c2pax[pydantic]"

# Со стриминговыми хэндлерами FastAPI
pip install "c2pax[fastapi]"

# Полный набор зависимостей
pip install "c2pax[all]"
```

---

## Быстрый старт

### 1. Декларативная инспекция

```python
import c2pax

# Поддерживаются пути, байты, потоки (BinaryIO)
asset = c2pax.inspect("photo.jpg")

print(f"Манифест C2PA: {asset.has_c2pa}")
print(f"Подписант: {asset.identity.signer_name}")
print(f"Создано с помощью ИИ: {asset.ai.generated}")
if asset.ai.tools:
    print(f"Инструменты ИИ: {', '.join(asset.ai.tools)}")

# Обход предков в графе происхождения (DAG)
if asset.provenance:
    for ancestor in asset.provenance.ancestors():
        print(f"  Исходный компонент: {ancestor.title} ({ancestor.format})")
```

### 2. Криптографическая верификация и TrustStore

```python
from c2pax import verify, TrustStore, VerificationPolicy

# 1. Загрузка доверенных сертификатов
trust_store = TrustStore.from_pem("trusted_root_ca.pem")

# 2. Проверка со строгой политикой
result = verify(
    "artwork.png",
    policy=VerificationPolicy.standard(),
    trust_store=trust_store,
)

if result.valid:
    print(f"✅ Файл подлинный! Подписант: {result.signer.signer_name}")
else:
    print(f"❌ Верификация не пройдена: {result.status}")
    print(result.explain())  # Человекочитаемое объяснение вердикта
```

### 3. Семантическое сравнение версий (`c2pax.diff`)

```python
import c2pax

diff = c2pax.diff("original.jpg", "edited_with_ai.jpg")
print(diff.explain())

if diff.signer_changed:
    print(f"Автор изменился с '{diff.previous_signer.signer_name}' на '{diff.current_signer.signer_name}'")
```

### 4. Создание и подписание манифеста

```python
from c2pax import Builder, Signer, Relationship

# Загрузка сертификата и ключа
signer = Signer.from_pem(
    certificate="cert.pem",
    private_key="key.pem",
    alg="es256",
    tsa_url="http://timestamp.digicert.com",
)

# Построение манифеста через Fluent API
builder = (
    Builder()
    .set_title("Marketing Campaign 2026")
    .set_format("image/jpeg")
    .add_action("c2pa.created", software="Studio v2.4")
    .add_ai_generation_assertion(tool="Midjourney v6", prompt="Futuristic electric car")
    .add_ai_training_permission(data_mining_allowed=False, ai_training_allowed=False)
    .add_ingredient("source_sketch.png", relationship=Relationship.PARENT_OF)
)

# Подписание файла
builder.sign("input.jpg", "signed_output.jpg", signer=signer)
```

---

## Консольный интерфейс (CLI)

```bash
# Инспекция с красивым выводом дерева Provenance и панелей
c2pax inspect photo.jpg

# Инспекция с выводом JSON для CI/CD
c2pax inspect photo.jpg --json

# Верификация с проверкой TrustStore
c2pax verify photo.jpg --policy strict --trust ./trusted_certs/

# Семантический diff двух файлов
c2pax diff original.jpg edited.jpg

# Быстрая подпись из командной строки
c2pax sign in.jpg out.jpg --cert cert.pem --key key.pem --title "My Photo" --ai-tool "Midjourney"
```

### Коды возврата CLI (Exit Codes)
- `0` — `VALID` (все проверки пройдены)
- `1` — `INVALID` (нарушение целостности хэшей или подписи)
- `2` — `UNTRUSTED` (сертификат отсутствует в TrustStore)
- `3` — `NO_MANIFEST` (манифест C2PA отсутствует)
- `4` — `UNSUPPORTED / ERROR` (неподдерживаемый формат или ошибка)

---

## Интеграция с FastAPI

```python
from fastapi import FastAPI, UploadFile, Depends
from c2pax.fastapi import inspect_upload, verify_upload
from c2pax.verification import VerificationPolicy, TrustStore

app = FastAPI(title="C2PA Verification Gateway")
trust_store = TrustStore.from_directory("./certs")

@app.post("/verify")
async def verify_endpoint(file: UploadFile):
    result = await verify_upload(
        file,
        policy=VerificationPolicy.standard(),
        trust_store=trust_store,
    )
    return result.to_dict()
```

---

## Архитектурная документация

Подробная архитектура компонентов описана в каталоге `docs/`:
- [CORE_ARCHITECTURE.md](docs/CORE_ARCHITECTURE.md) — Доменная модель, FFI буферизация и `AssetSource`.
- [VERIFICATION_ARCHITECTURE.md](docs/VERIFICATION_ARCHITECTURE.md) — Доверие, `TrustStore` и политики `VerificationPolicy`.
- [PROVENANCE_ARCHITECTURE.md](docs/PROVENANCE_ARCHITECTURE.md) — DAG граф происхождения и алгоритм `c2pax.diff`.
- [SIGNING_ARCHITECTURE.md](docs/SIGNING_ARCHITECTURE.md) — `Builder` и `Signer`.
- [CLI_ARCHITECTURE.md](docs/CLI_ARCHITECTURE.md) — CLI и Rich рендеринг.
- [INTEGRATION_ARCHITECTURE.md](docs/INTEGRATION_ARCHITECTURE.md) — FastAPI, Pydantic v2 и Batch.
- [CHANGELOG.md](docs/CHANGELOG.md) — Журнал версий и изменений.

---

## Безопасность

Политика безопасности и правила ответственного сообщения об уязвимостях описаны в [SECURITY.md](SECURITY.md).

---

## Сторонние репозитории и благодарности

Проект **c2pax** опирается на открытые стандарты и надежные библиотеки экосистемы:

| Репозиторий / Проект | Лицензия | Назначение в c2pax |
| :--- | :--- | :--- |
| [contentauth/c2pa-python](https://github.com/contentauth/c2pa-python) / [c2pa-rs](https://github.com/contentauth/c2pa-rs) | Apache-2.0 / MIT | Официальный Rust-движок и FFI-биндинги Coalition for Content Provenance and Authenticity (C2PA) для низкоуровневой работы с JUMBF манифестами |
| [pyca/cryptography](https://github.com/pyca/cryptography) | Apache-2.0 / BSD | Криптографические примитивы, валидация X.509 сертификатов, TrustStore и проверка цифровых подписей |
| [Textualize/rich](https://github.com/Textualize/rich) | MIT | Форматированный консольный рендеринг деревьев происхождения (DAG), таблиц diff и цветных информационных панелей |
| [pallets/click](https://github.com/pallets/click) | BSD-3-Clause | Инфраструктура командной строки CLI c2pax и обработка аргументов |
| [pydantic/pydantic](https://github.com/pydantic/pydantic) | MIT | Схемы данных и строгая валидация доменных моделей для интеграции |
| [fastapi/fastapi](https://github.com/fastapi/fastapi) | MIT | Асинхронные потоковые обработчики для загрузки и верификации файлов через веб-API |

---

## Лицензия

Apache License 2.0 (c) 2026 c2pax team. См. полный текст в файле [LICENSE](LICENSE).
