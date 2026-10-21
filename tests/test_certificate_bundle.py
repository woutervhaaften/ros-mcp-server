"""Offline checks for the installed application's certificate-bundle security floor.

These tests neither start the server nor contact ROS or any network endpoint.
They cover default Requests/HTTPX trust, not custom or operating-system stores.
"""

import hashlib
import ssl
from importlib.metadata import requires, version
from pathlib import Path

import certifi
import httpx
import requests
from packaging.requirements import Requirement
from packaging.version import Version


def test_installed_package_enforces_certificate_security_floor():
    requirements = [Requirement(value) for value in requires("ros-mcp")]
    requirement = next(value for value in requirements if value.name == "certifi")
    assert Version("2026.10.19") in requirement.specifier
    assert Version("2026.10.18") not in requirement.specifier
    assert Version(version("certifi")) >= Version("2026.10.19")


def test_updated_bundle_loads_without_removed_trust_anchors():
    context = ssl.create_default_context(cafile=certifi.where())
    fingerprints = {
        hashlib.sha256(certificate).hexdigest()
        for certificate in context.get_ca_certs(binary_form=True)
    }
    assert fingerprints
    # emSign ECC Root CA - G3: identify the DER certificate, not its display name.
    assert "86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b" not in fingerprints
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname


def test_requests_default_uses_installed_bundle():
    assert Path(requests.certs.where()).resolve() == Path(certifi.where()).resolve()
    assert (
        Path(requests.adapters.DEFAULT_CA_BUNDLE_PATH).resolve() == Path(certifi.where()).resolve()
    )
    with requests.Session() as session:
        session.trust_env = False  # Isolate this default-path test from operator overrides.
        settings = session.merge_environment_settings(
            "https://example.invalid", {}, None, None, None
        )
        assert settings["verify"] is True


def test_httpx_default_loads_installed_bundle(monkeypatch):
    calls = []
    create_context = ssl.create_default_context

    def record_context(*args, **kwargs):
        context = create_context(*args, **kwargs)
        calls.append((kwargs, context))
        return context

    monkeypatch.setattr(ssl, "create_default_context", record_context)
    with httpx.Client(trust_env=False):
        pass  # Construct the client only; never send a request.
    assert calls
    assert all(
        Path(kwargs["cafile"]).resolve() == Path(certifi.where()).resolve() for kwargs, _ in calls
    )
    assert all(context.verify_mode == ssl.CERT_REQUIRED for _, context in calls)
    assert all(context.check_hostname for _, context in calls)
