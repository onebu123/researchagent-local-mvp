from __future__ import annotations

from scripts.validate_v1 import is_npm_audit_network_failure


def test_npm_audit_network_failure_is_offline_fallback_only() -> None:
    network_output = (
        "npm warn audit request to https://registry.npmjs.org/-/npm/v1/security/audits/quick "
        "failed, reason: Client network socket disconnected before secure TLS connection was established\n"
        "npm error audit endpoint returned an error"
    )
    vulnerability_output = (
        "found 1 high severity vulnerability\n"
        "Run `npm audit fix` to fix them, or `npm audit` for details."
    )

    assert is_npm_audit_network_failure(network_output) is True
    assert is_npm_audit_network_failure(vulnerability_output) is False
