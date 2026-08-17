# Архитектура ядра: c2pax Core Architecture

Документ описывает структуру базового слоя SDK c2pax, доменную модель, обработку входных потоков данных и взаимодействие с низкоуровневым движком C2PA.

---

## 1. Концептуальная модель

Библиотека `c2pax` выстраивает четкую границу между **декларативным представлением** (что заявлено в манифесте) и **криптографическим доверием** (насколько данным можно доверять):

```
       Plaintext / Media File (JPEG, PNG, WebP, MP4, PDF, etc.)
                                 │
                          [AssetSource]
                                 │
                       [BaseC2paBackend]
                                 │
                   ┌─────────────┴─────────────┐
                   ▼                           ▼
            c2pax.inspect()             c2pax.verify()
       (Декларативный срез)          (Доверенный срез)
         • AssetMetadata               • VerificationStatus
         • IdentityInfo (unverified)   • TrustStore matching
         • AIProvenance                • Hash / Signature audit
         • PermissionsInfo             • Policy enforcement
         • ProvenanceGraph (DAG)       • VerificationResult.explain()
```

---

## 2. Структура модулей ядра

```
src/c2pax/
├── api.py            # Публичный фасад (inspect, verify, diff, sign)
├── core/
│   ├── models.py     # Модели данных на dataclass(slots=True)
│   ├── provenance.py # Граф происхождения DAG
│   ├── source.py     # Адаптер входных данных AssetSource
│   └── exceptions.py # Иерархия исключений
└── backend/
    ├── base.py       # Абстрактный интерфейс к C2PA engine
    ├── c2pa_rs.py    # Адаптер к c2pa-python (c2pa-rs FFI)
    └── mock.py       # Mock-бэкенд для детерминированного тестирования
```

---

## 3. Адаптер входных данных (`AssetSource`)

Адаптер `AssetSource` унифицирует работу с:
- Путями файловой системы (`str`, `pathlib.Path`);
- Байтами в памяти (`bytes`, `bytearray`, `memoryview`);
- Потоками ввода-вывода (`io.BytesIO`, `io.BufferedReader`, `typing.BinaryIO`, `tempfile.SpooledTemporaryFile`).

### Особенности работы с C/Rust FFI bindings:
1. Низкоуровневый `c2pa-rs` требует seekable доступ к медиаконтейнеру (`seek(0)` и `tell()`).
2. Для не-seekable потоков `AssetSource` организует безопасный контекстный временный буфер.
3. Обеспечивается детерминированное закрытие дескрипторов и освобождение памяти через протокол контекстных менеджеров `with`.

---

## 4. Доменная модель (`c2pax.core.models`)

Все модели данных спроектированы на `dataclasses(slots=True)`:
- Минимальное потребление памяти (отсутствие `__dict__`).
- Быстрый доступ к атрибутам.
- Строгая типизация и совместимость со схемами Pydantic v2.

### Ключевые сущности:
- `AssetMetadata`: технические свойства контейнера (размер, MIME-тип, дата создания/модификации).
- `IdentityInfo`: информация о заявителе и подписанте (сертификат, организация, эмитент).
- `AIProvenance`: факты генерации или содействия ИИ (инструменты, модели, промпты).
- `PermissionsInfo`: декларации разрешений обучения и data-mining (`c2pa.data_mining`).
- `ManifestStatus`: статус присутствия C2PA контейнера и версия генератора.
- `AssetInfo`: агрегированный результат вызова `inspect()`.

---

## 5. Иерархия исключений (`c2pax.core.exceptions`)

```
C2PAError (базовое исключение SDK)
├── AssetError
│   ├── AssetNotFoundError
│   └── UnsupportedFormatError
├── ManifestError
│   ├── ManifestNotFoundError
│   ├── CorruptedManifestError
│   └── CyclicProvenanceError
├── VerificationError
│   ├── IntegrityError
│   ├── UntrustedSignerError
│   └── PolicyViolationError
└── SigningError
    ├── KeyPairMismatchError
    └── CertificateError
```

---

## 6. Безопасность и надежность (Security by Design)

- **Безопасность FFI**: изолирование паник Rust-движка и преобразование их в типизированные исключения Python.
- **Предотвращение DoS**: защита от сжатых бомб (zip/container bombs), ограничение максимального размера считываемых манифестов.
- **Изоляция секретов**: `Signer` не сохраняет закрытые ключи в открытых логах и исключениях.
