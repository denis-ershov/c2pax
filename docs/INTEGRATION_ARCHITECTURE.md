# Архитектура интеграций: c2pax Integration Architecture

Документ описывает интеграцию SDK c2pax с экосистемами веб-разработки (FastAPI, Pydantic v2) и пакетной обработки ассетов.

---

## 1. FastAPI интеграция (`c2pax.integrations.fastapi`)

Модуль предоставляет асинхронные потоковые хэндлеры для работы с `fastapi.UploadFile` без избыточного копирования в оперативную память:

```python
from fastapi import FastAPI, UploadFile, Depends
from c2pax.fastapi import inspect_upload, verify_upload
from c2pax.verification import VerificationPolicy, TrustStore

app = FastAPI(title="C2PA Verification Gateway")

@app.post("/api/v1/inspect")
async def inspect_endpoint(file: UploadFile):
    return await inspect_upload(file)

@app.post("/api/v1/verify")
async def verify_endpoint(
    file: UploadFile,
    policy: VerificationPolicy = Depends(VerificationPolicy.standard),
):
    return await verify_upload(file, policy=policy)
```

---

## 2. Pydantic v2 схемы (`c2pax.integrations.pydantic`)

Модуль обеспечивает бесшовную сериализацию и валидацию данных в REST API и микросервисах:
- `AssetInfoSchema`, `AssetMetadataSchema`, `IdentityInfoSchema`, `AIProvenanceSchema`, `PermissionsInfoSchema`.
- `VerificationResultSchema`, `SemanticDiffSchema`.
- Конвертеры `to_pydantic(asset_info)` и валидаторы входных JSON.

---

## 3. Пакетная обработка (`c2pax.integrations.batch`)

- `verify_many(sources: list[AssetSource], policy: VerificationPolicy = ...) -> list[VerificationResult]`
- `verify_directory(dir_path: Path, recursive: bool = True, pattern: str = "*") -> dict[Path, VerificationResult]`
- Параллельное исполнение задач с использованием пула потоков `ThreadPoolExecutor`.
