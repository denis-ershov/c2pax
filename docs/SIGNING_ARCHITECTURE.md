# Архитектура создания и подписания: c2pax Signing & Builder Architecture

Документ описывает подсистему генерации манифестов, цифровой подписи медиа-файлов и fluent API построителя (`Builder`).

---

## 1. Компоненты подписи

```
                ┌────────────────────────────────┐
                │          Signer (PEM)          │
                │  (Certificate + Private Key)   │
                └───────────────┬────────────────┘
                                │
   ┌────────────────────────────┼────────────────────────────┐
   ▼                                                         ▼
[ Quick Sign: c2pax.sign() ]               [ Fluent Builder: c2pax.Builder() ]
 • Быстрое наложение подписи                 • Добавление кастомных действий (Actions)
 • Базовые метаданные (Title, Creator)       • AI Assertions (генерация, содействие, промпты)
 • Автоопределение MIME-типа                 • Добавление связанных ингредиентов
                                             • Настройка политик обучения ИИ (Permissions)
                                             • Встраивание цифровой подписи в медиа-поток
```

---

## 2. Модель `Signer`

`Signer` инкапсулирует криптографические ключи и сертификаты для формирования цифровой подписи стандарта C2PA:
- **Алгоритмы**: `ES256` (ECDSA P-256 с SHA-256), `PS256` (RSA-PSS с SHA-256), `ED25519`.
- **Источники**:
  - PEM-файлы сертификатов и закрытых ключей (`Signer.from_pem()`);
  - Объекты библиотеки `cryptography` в памяти (`Signer.from_keys()`).
- **Служба меток времени (TSA)**: поддержка RFC 3161 Time-Stamp Authority URL.

---

## 3. Декларативный `Builder` API

```python
builder = (
    Builder()
    .set_title("Официальный релиз")
    .set_format("image/jpeg")
    .add_action("c2pa.created", software="c2pax SDK v0.1")
    .add_ai_generation_assertion(tool="Midjourney v6", prompt="Landscape photo")
    .add_ai_training_permission(data_mining_allowed=False, ai_training_allowed=False)
    .add_ingredient("source.png", relationship=Relationship.PARENT_OF)
)

builder.sign(input_file="input.jpg", output_file="signed.jpg", signer=signer)
```

---

## 4. Поддержка форматов (Tier Matrix)

- **Tier 1 (Core Media)**: `JPEG`, `PNG`, `WebP`, `MP4` — полная поддержка инспекции, верификации и подписи.
- **Tier 2 (Rich Media & Docs)**: `TIFF`, `HEIF`/`HEIC`, `AVIF`, `MOV`, `PDF` — полная инспекция и верификация; подпись в зависимости от возможностей контейнера.
- **Tier 3 (Extended Audio/Docs)**: `M4A`, `MP3`, `WAV`, `DOCX`, `PPTX` — инспекция метаданных, экспериментальная верификация.
