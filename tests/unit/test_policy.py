"""Тесты политик верификации VerificationPolicy."""

from c2pax.verification.policy import VerificationPolicy


def test_policy_presets() -> None:
    perm = VerificationPolicy.permissive()
    assert perm.require_trusted_signer is False
    assert perm.allow_expired_certs is True
    assert perm.fail_on_warnings is False

    std = VerificationPolicy.standard()
    assert std.require_trusted_signer is True
    assert std.allow_expired_certs is False
    assert std.require_timestamp is False

    strict = VerificationPolicy.strict()
    assert strict.require_trusted_signer is True
    assert strict.require_timestamp is True
    assert strict.fail_on_warnings is True


def test_policy_to_dict() -> None:
    std = VerificationPolicy.standard()
    d = std.to_dict()
    assert d["require_trusted_signer"] is True
    assert d["max_clock_skew_seconds"] == 300
