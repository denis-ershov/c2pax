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

**English** | **[Русский](README.md)**

</div>

---

**c2pax** is a high-level, ergonomic, and strictly-typed Python SDK for inspection, cryptographic verification, provenance DAG graph traversal, semantic diffing, and manifest generation based on the **C2PA (Content Credentials)** standard.

It serves as a developer-friendly DX and Verification layer on top of the official `c2pa-python` (`c2pa-rs`) engine, enforcing a strict boundary between **declarative metadata** and **cryptographic trust**:

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
 "What is declared in the manifest?"                         "Can we trust this claim?"
  (Metadata, Provenance DAG, AI, Identity)                    (Policy, Integrity, TrustStore)
```

---

## Features

- 🔍 **Declarative Inspection (`c2pax.inspect`)**: Instant extraction of title, format, signer identity, AI tools & prompts (`AIProvenance`), and data-mining/training restrictions (`PermissionsInfo`).
- 🛡️ **Cryptographic Verification (`c2pax.verify`)**: Validation of JUMBF/CBOR hash integrity, signature authenticity, local `TrustStore` trust anchors, and customizable `VerificationPolicy` presets (permissive, standard, strict).
- 🌳 **Provenance Graph as DAG (`ProvenanceGraph`)**: Directed Acyclic Graph tracking edits and parent ingredients with hardware cycle protection (`CyclicProvenanceError`) and recursion depth limiters.
- ⚖️ **Semantic Diff Engine (`c2pax.diff`)**: High-level semantic comparison between asset versions (actions, ingredients, signer changes, AI assertions, permissions).
- ✍️ **Fluent Builder & Signer (`c2pax.Builder`, `c2pax.Signer`)**: Intuitive API for creating assertions, embedding AI metadata, attaching ingredients, and signing files with secret-masked private keys.
- 💻 **Rich CLI (`c2pax`)**: Beautiful terminal visualization of provenance trees, summaries, and diff tables with standardized exit codes (0..4) and `--json` support for CI/CD pipelines.
- 🚀 **Ecosystem Integrations**:
  - `c2pax[fastapi]` — Async streaming handlers for `UploadFile` without redundant memory copying;
  - `c2pax[pydantic]` — Strict Pydantic v2 validation models and serializers;
  - Parallel batch verification via `verify_many` and `verify_directory`.

---

## Installation

```bash
# Minimal core SDK (dataclasses and cryptography only)
pip install c2pax

# With Rich CLI support
pip install "c2pax[cli]"

# With Pydantic v2 models
pip install "c2pax[pydantic]"

# With FastAPI streaming helpers
pip install "c2pax[fastapi]"

# Full bundle with all extras
pip install "c2pax[all]"
```

---

## Quick Start

### 1. Declarative Inspection

```python
import c2pax

# Supports file paths, raw bytes, and file streams (BinaryIO)
asset = c2pax.inspect("photo.jpg")

print(f"Has C2PA: {asset.has_c2pa}")
print(f"Signer: {asset.identity.signer_name}")
print(f"AI Generated: {asset.ai.generated}")
if asset.ai.tools:
    print(f"AI Tools: {', '.join(asset.ai.tools)}")

# Traverse provenance DAG ancestors
if asset.provenance:
    for ancestor in asset.provenance.ancestors():
        print(f"  Parent Component: {ancestor.title} ({ancestor.format})")
```

### 2. Cryptographic Verification & TrustStore

```python
from c2pax import verify, TrustStore, VerificationPolicy

# 1. Load trusted root certificates
trust_store = TrustStore.from_pem("trusted_root_ca.pem")

# 2. Verify with standard policy
result = verify(
    "artwork.png",
    policy=VerificationPolicy.standard(),
    trust_store=trust_store,
)

if result.valid:
    print(f"✅ Asset verified! Signer: {result.signer.signer_name}")
else:
    print(f"❌ Verification failed: {result.status}")
    print(result.explain())  # Human-readable diagnostic explanation
```

### 3. Semantic Diff (`c2pax.diff`)

```python
import c2pax

diff = c2pax.diff("original.jpg", "edited_with_ai.jpg")
print(diff.explain())

if diff.signer_changed:
    print(f"Signer changed from '{diff.previous_signer.signer_name}' to '{diff.current_signer.signer_name}'")
```

### 4. Manifest Creation & Signing

```python
from c2pax import Builder, Signer, Relationship

# Load signing certificate and private key
signer = Signer.from_pem(
    certificate="cert.pem",
    private_key="key.pem",
    alg="es256",
    tsa_url="http://timestamp.digicert.com",
)

# Build manifest via fluent interface
builder = (
    Builder()
    .set_title("Marketing Campaign 2026")
    .set_format("image/jpeg")
    .add_action("c2pa.created", software="Studio v2.4")
    .add_ai_generation_assertion(tool="Midjourney v6", prompt="Futuristic electric car")
    .add_ai_training_permission(data_mining_allowed=False, ai_training_allowed=False)
    .add_ingredient("source_sketch.png", relationship=Relationship.PARENT_OF)
)

# Sign asset
builder.sign("input.jpg", "signed_output.jpg", signer=signer)
```

---

## Command Line Interface (CLI)

```bash
# Inspect asset with rich provenance tree and metadata panels
c2pax inspect photo.jpg

# Inspect asset with JSON output for CI/CD
c2pax inspect photo.jpg --json

# Verify asset against trusted roots
c2pax verify photo.jpg --policy strict --trust ./trusted_certs/

# Semantic diff between two assets
c2pax diff original.jpg edited.jpg

# Quick signing from CLI
c2pax sign in.jpg out.jpg --cert cert.pem --key key.pem --title "My Photo" --ai-tool "Midjourney"
```

### CLI Exit Codes
- `0` — `VALID` (all policy checks passed)
- `1` — `INVALID` (cryptographic hash or signature mismatch)
- `2` — `UNTRUSTED` (signing certificate missing from TrustStore)
- `3` — `NO_MANIFEST` (no C2PA manifest found)
- `4` — `UNSUPPORTED / ERROR` (unsupported format or internal error)

---

## FastAPI Integration

```python
from fastapi import FastAPI, UploadFile
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

## Architecture Documentation

Detailed component specifications are available in the `docs/` folder:
- [CORE_ARCHITECTURE.md](docs/CORE_ARCHITECTURE.md) — Domain models, FFI stream buffering, and `AssetSource`.
- [VERIFICATION_ARCHITECTURE.md](docs/VERIFICATION_ARCHITECTURE.md) — Trust validation, `TrustStore`, and `VerificationPolicy`.
- [PROVENANCE_ARCHITECTURE.md](docs/PROVENANCE_ARCHITECTURE.md) — Provenance DAG graph and `c2pax.diff` algorithm.
- [SIGNING_ARCHITECTURE.md](docs/SIGNING_ARCHITECTURE.md) — `Builder` and `Signer`.
- [CLI_ARCHITECTURE.md](docs/CLI_ARCHITECTURE.md) — CLI commands and Rich renderers.
- [INTEGRATION_ARCHITECTURE.md](docs/INTEGRATION_ARCHITECTURE.md) — FastAPI, Pydantic v2, and Batch processing.
- [CHANGELOG.md](docs/CHANGELOG.md) — Release notes and change history.

---

## Security

Security policies, threat model, and vulnerability reporting procedures are documented in [SECURITY.md](SECURITY.md).

---

## Third-Party Dependencies & Acknowledgements

**c2pax** is built on open standards and leverages key libraries across the open-source ecosystem:

| Repository / Project | License | Role in c2pax |
| :--- | :--- | :--- |
| [contentauth/c2pa-python](https://github.com/contentauth/c2pa-python) / [c2pa-rs](https://github.com/contentauth/c2pa-rs) | Apache-2.0 / MIT | Official Rust core and Python FFI bindings by the Coalition for Content Provenance and Authenticity (C2PA) for low-level JUMBF parsing & signing |
| [pyca/cryptography](https://github.com/pyca/cryptography) | Apache-2.0 / BSD | Cryptographic primitives, X.509 certificate validation, TrustStore management, and digital signature checks |
| [Textualize/rich](https://github.com/Textualize/rich) | MIT | Rich terminal formatting for provenance DAG trees, diff tables, and info panels |
| [pallets/click](https://github.com/pallets/click) | BSD-3-Clause | Command Line Interface framework and CLI argument handling |
| [pydantic/pydantic](https://github.com/pydantic/pydantic) | MIT | Pydantic v2 domain schemas and data validation |
| [fastapi/fastapi](https://github.com/fastapi/fastapi) | MIT | Async streaming handlers for file upload verification via web APIs |

---

## License

Apache License 2.0 (c) 2026 c2pax team. See [LICENSE](LICENSE) for details.
