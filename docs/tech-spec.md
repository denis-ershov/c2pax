Техническое задание: c2pax (v1.0 Final Specification)c2pax — Python-native SDK для инспекции, верификации и работы с графом происхождения (Provenance) стандарта C2PA Content Credentials.1. Позиционирование и архитектурная модельМиссия: Превратить работу с C2PA в Python из манипуляций с низкоуровневыми бинарными контейнерами и assertions в объектно-ориентированный интерфейс уровня requests / rich.Библиотека выступает прикладным DX- и Verification-слоем над официальным движком c2pa-python (c2pa-rs), выстраивая строгое разделение между декларативными данными и криптографическим доверием:Plaintext                  C2PA Ecosystem (Rust core: c2pa-rs)
                                   │
                              c2pa-python (Engine)
                                   │
                                 c2pax (High-Level SDK)
                                   │
     ┌─────────────────────────────┴─────────────────────────────┐
     │                                                           │
c2pax.inspect()                                           c2pax.verify()
"What does the manifest declare?"                         "Can we cryptographically trust it?"
(Declarative: metadata, provenance, ai, identity)          (Policy enforcement: integrity, trust, status)
inspect() — декларативный срез: извлекает задекларированную автором/инструментом информацию. Не гарантирует валидность цифровой подписи или доверие к сертификату.verify() — доверенный срез: осуществляет проверку криптографической целостности хэшей контента, подписи и соответствия сертификата переданному TrustStore на основании VerificationPolicy.2. Входные данные и дистрибуцияУниверсальный AssetSourceПоддерживаются пути файловой системы, сырые байты и файловые потоки:PythonAssetSource = str | Path | bytes | BinaryIO
Адаптер изолирует детали работы с I/O и временным буферизированием для внутренних C/Rust bindings, требующих seek/random access.Модель дистрибуцииПубликуется единый пакет c2pax без тяжелых обязательных зависимостей. Базовые структуры реализованы на dataclasses(slots=True).Bashpip install c2pax             # Core SDK (легковесный)
pip install "c2pax[cli]"       # CLI интерфейс на базе Rich и Click
pip install "c2pax[pydantic]"  # Pydantic v2 адаптеры моделей
pip install "c2pax[fastapi]"   # Zero-overhead streaming хэндлеры для UploadFile
pip install "c2pax[all]"       # Полный набор зависимостей
3. Доменная модель (c2pax.core.models)Структура AssetInfo (Результат inspect())Pythonfrom __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Iterable, Iterator

@dataclass(slots=True)
class AssetMetadata:
    title: str | None = None
    format: str | None = None
    file_size_bytes: int | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None

@dataclass(slots=True)
class IdentityInfo:
    """Задекларированная информация о создателе и подписанте (не проверенная криптографически)."""
    signer_name: str | None = None
    organization: str | None = None
    cert_issuer: str | None = None
    cert_serial: str | None = None

@dataclass(slots=True)
class AIProvenance:
    """Фактологические утверждения о генеративном происхождении."""
    generated: bool | None = None   # True = сгенерировано, None = нет утверждения
    assisted: bool | None = None    # True = использовался при редактировании
    tools: list[str] = field(default_factory=list)
    models: list[dict[str, Any]] = field(default_factory=list)

@dataclass(slots=True)
class PermissionsInfo:
    """Декларации ограничений использования и data-mining (c2pa.data_mining)."""
    data_mining_allowed: bool | None = None
    ai_training_allowed: bool | None = None
    raw_assertions: list[dict[str, Any]] = field(default_factory=list)

@dataclass(slots=True)
class ManifestStatus:
    """Служебный статус наличия контейнера без валидации доверия."""
    present: bool
    format_version: str | None = None
    claim_generator: str | None = None
    has_signature: bool = False

@dataclass(slots=True)
class AssetInfo:
    has_c2pa: bool
    metadata: AssetMetadata = field(default_factory=AssetMetadata)
    identity: IdentityInfo = field(default_factory=IdentityInfo)
    provenance: ProvenanceGraph | None = None
    ai: AIProvenance = field(default_factory=AIProvenance)
    permissions: PermissionsInfo = field(default_factory=PermissionsInfo)
    manifest_status: ManifestStatus = field(default_factory=lambda: ManifestStatus(present=False))
    raw: dict[str, Any] = field(default_factory=dict)
Модель графа происхождения (ProvenanceGraph как DAG)C2PA связывает манифесты в направленный ациклический граф (DAG). Представление в виде дерева используется исключительно на уровне вывода в UI/CLI.Pythonclass Relationship(str, Enum):
    PARENT_OF = "parentOf"
    COMPONENT_OF = "componentOf"
    INPUT_TO = "inputTo"

@dataclass(slots=True)
class Action:
    name: str
    software: str | None = None
    timestamp: datetime | None = None
    parameters: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class ProvenanceNode:
    id: str
    title: str
    format: str | None = None
    hash: str | None = None
    actions: list[Action] = field(default_factory=list)

@dataclass(slots=True)
class ProvenanceEdge:
    source_id: str
    target_id: str
    relationship: Relationship | str

@dataclass(slots=True)
class ProvenanceGraph:
    root_id: str
    _nodes: dict[str, ProvenanceNode] = field(default_factory=dict)
    _edges: list[ProvenanceEdge] = field(default_factory=list)

    @property
    def root(self) -> ProvenanceNode:
        return self._nodes[self.root_id]

    @property
    def actions(self) -> list[Action]:
        return self.root.actions

    def nodes(self) -> Iterable[ProvenanceNode]:
        return self._nodes.values()

    def edges(self) -> Iterable[ProvenanceEdge]:
        return tuple(self._edges)

    def ancestors(self, node_id: str | None = None) -> Iterator[ProvenanceNode]:
        """Итератор по всем исходным узлам-предкам в DAG."""
        target_id = node_id or self.root_id
        parent_ids = [e.target_id for e in self._edges if e.source_id == target_id]
        for pid in parent_ids:
            if pid in self._nodes:
                yield self._nodes[pid]
                yield from self.ancestors(pid)
4. Верификация: VerificationStatus, Policy и TrustStoreСтатусы верификации (VerificationStatus)Pythonclass VerificationStatus(str, Enum):
    VALID = "valid"              # Все проверки политики пройдены
    INVALID = "invalid"          # Нарушена криптографическая целостность
    UNTRUSTED = "untrusted"      # Подпись верна, но сертификат не входит в TrustStore
    NO_MANIFEST = "no_manifest"  # Манифест C2PA отсутствует
    UNSUPPORTED = "unsupported"  # Формат не поддерживается
    ERROR = "error"              # Ошибка парсинга или исполнения
Политика проверки (VerificationPolicy)Python@dataclass(slots=True)
class VerificationPolicy:
    require_trusted_signer: bool = False
    require_timestamp: bool = False
    allow_expired_certs: bool = True
    fail_on_warnings: bool = False
    max_clock_skew_seconds: int = 300

    @classmethod
    def permissive(cls) -> VerificationPolicy:
        """Валидно, если сошлась криптография, независимо от наличия в TrustStore."""
        return cls(require_trusted_signer=False, require_timestamp=False, allow_expired_certs=True, fail_on_warnings=False)

    @classmethod
    def strict(cls) -> VerificationPolicy:
        """Требует валидной доверенной подписи, доверенной TSA и отсутствия warnings."""
        return cls(require_trusted_signer=True, require_timestamp=True, allow_expired_certs=False, fail_on_warnings=True)

    @classmethod
    def standard(cls) -> VerificationPolicy:
        """Требует доверенного подписанта, но допускает отсутствие TSA."""
        return cls(require_trusted_signer=True, require_timestamp=False, allow_expired_certs=False, fail_on_warnings=False)
Результат верификации (VerificationResult)Python@dataclass(slots=True)
class VerificationResult:
    status: VerificationStatus
    valid: bool                  # Упрощенный флаг (status == VerificationStatus.VALID)
    integrity: IntegrityStatus   # Хэши и цифровая подпись
    trust: TrustStatus           # Статус сопоставления с TrustStore
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationWarning] = field(default_factory=list)
    signer: IdentityInfo | None = None
    timestamp: datetime | None = None
    policy_applied: VerificationPolicy = field(default_factory=VerificationPolicy.permissive)

    def explain(self) -> str:
        """Формирует человекочитаемое объяснение вердикта валидации."""
        ...
Управление доверием (TrustStore) для v0.1В релизе v0.1 поддерживаются исключительно локальные доверенные хранилища (без автозагрузки по сети):Pythonclass TrustStore:
    @classmethod
    def from_pem(cls, path_or_str: str | Path) -> TrustStore: ...
    
    @classmethod
    def from_directory(cls, dir_path: str | Path) -> TrustStore: ...
    
    def add_claim_signer_pem(self, pem_data: str) -> None: ...
    def add_tsa_pem(self, pem_data: str) -> None: ...
5. Семантический анализ изменений (c2pax.diff)Функция diff выполняет сравнение нормализованных бизнес-сущностей двух ассетов, абстрагируясь от бинарных различий сериализации CBOR/JUMBF:Python@dataclass(slots=True)
class SemanticDiff:
    added_actions: list[Action] = field(default_factory=list)
    added_ingredients: list[ProvenanceNode] = field(default_factory=list)
    signer_changed: bool = False
    previous_signer: IdentityInfo | None = None
    current_signer: IdentityInfo | None = None
    ai_provenance_changed: bool = False
    permissions_changed: bool = False
    metadata_diff: dict[str, tuple[Any, Any]] = field(default_factory=dict)
6. Создание и подписание (Signing & Builder)Pythonfrom c2pax import Builder, Signer, sign

signer = Signer.from_pem(certificate="cert.pem", private_key="key.pem")

# Быстрая подпись
sign(
    input_file="input.jpg",
    output_file="signed.jpg",
    creator="Media Studio",
    title="Official Release",
    signer=signer,
)

# Builder API для сложных цепочек
builder = (
    Builder()
    .set_title("Marketing Asset")
    .add_action("c2pa.created")
    .add_ai_generation_assertion(tool="Midjourney v6")
    .add_ingredient("source.png", relationship="parentOf")
)
builder.sign("input.jpg", "output.jpg", signer=signer)
7. Матрица поддержки форматовTierФорматыInspectVerifySignTier 1 (Core Media)JPEG, PNG, WebP, MP4ПолнаяПолнаяПолнаяTier 2 (Rich Media & Docs)TIFF, HEIF/HEIC, AVIF, MOV, PDFПолнаяПолнаяВ зависимости от backendTier 3 (Extended Audio/Docs)M4A, MP3, WAV, DOCX, PPTXMetadata onlyЭкспериментальнаяЗависит от контейнера8. CLI и интеграцииCLIc2pax inspect <file> — рендеринг DAG provenance в виде дерева, сводки по AI и Identity через Rich.c2pax verify <file> [--policy strict|standard|permissive] [--trust <path>] — проверка со статусными exit codes:0 — VALID1 — INVALID (нарушение целостности)2 — UNTRUSTED (не доверен)3 — NO_MANIFEST4 — UNSUPPORTED / ERRORc2pax diff <file1> <file2> — семантическое сравнение двух файлов.c2pax inspect <file> --json — JSON-сериализация для CI/CD скриптов.FastAPI интеграция (c2pax[fastapi])Pythonfrom fastapi import FastAPI, UploadFile
from c2pax.fastapi import inspect_upload, verify_upload
from c2pax.verification import VerificationPolicy

app = FastAPI()

@app.post("/verify")
async def verify_endpoint(file: UploadFile):
    return await verify_upload(file, policy=VerificationPolicy.standard())
9. Структура репозиторияPlaintextc2pax/
├── src/
│   └── c2pax/
│       ├── __init__.py
│       ├── api.py            # inspect, verify, diff, sign
│       ├── core/
│       │   ├── models.py     # AssetInfo, Metadata, IdentityInfo, AIProvenance, PermissionsInfo
│       │   ├── provenance.py # ProvenanceGraph (DAG), Node, Edge, Action
│       │   └── exceptions.py # Иерархия исключений
│       ├── verification/
│       │   ├── policy.py     # VerificationPolicy
│       │   ├── trust.py      # TrustStore (локальный)
│       │   └── result.py     # VerificationResult, VerificationStatus, explain()
│       ├── diff/
│       │   └── semantic.py   # SemanticDiff logic
│       ├── signing/
│       │   ├── builder.py    # Builder API
│       │   └── signer.py     # Signer (PEM)
│       ├── backend/
│       │   ├── base.py       # BaseC2paBackend
│       │   └── c2pa_rs.py    # Адаптер к c2pa-python
│       ├── cli/
│       │   ├── main.py
│       │   └── renderers.py  # Rich TreeRenderer
│       └── integrations/
│           ├── pydantic.py   # Схемы Pydantic v2
│           └── fastapi.py    # Хэндлеры для UploadFile
├── tests/
├── pyproject.toml
└── README.md
10. Поэтапный план реализации (Roadmap)v0.1 — Core Inspection & Verification (MVP Scope):AssetSource (Path, bytes, BinaryIO).inspect() с разделением на metadata, identity, ai, manifest_status, raw.verify() с VerificationStatus, VerificationPolicy и TrustStore.from_pem().Базовый CLI (inspect, verify) с Rich-рендерингом и --json.Полная поддержка форматов Tier-1 (JPEG, PNG, WebP, MP4).v0.2 — Provenance Graph DAG & Semantic Diff:Полноценная реализация ProvenanceGraph (DAG, узлы, ребра, ancestors()).Реализация c2pax.diff() (семантический diff).Выделение asset.permissions (data mining, training flags).v0.3 — Signing & Builder:Реализация Signer.from_pem().Builder API для добавления actions, assertions, AI metadata и ingredients.Функция c2pax.sign().Поддержка Tier-2 форматов (PDF, HEIC, AVIF).v0.4 — Production Ecosystem:Модули c2pax[fastapi] и c2pax[pydantic].Пакетная обработка (verify_many, verify_directory).CI/CD Actions и pre-commit хуки.