"""
Unit tests for fletx.utils.version_checker module.
Covers: VersionInfo, CompatibilityResult, VersionChecker methods.
"""

import pytest
from unittest.mock import patch, Mock

from fletx.utils.version_checker import (
    VersionInfo,
    CompatibilityResult,
    VersionChecker,
)


# ===================== VersionInfo =====================

class TestVersionInfo:

    def test_str(self):
        vi = VersionInfo("1.2.3", "MyPkg")
        assert str(vi) == "MyPkg v1.2.3"

    def test_repr(self):
        vi = VersionInfo("1.2.3", "MyPkg")
        assert repr(vi) == "VersionInfo(MyPkg, 1.2.3)"

    def test_version_parsed(self):
        vi = VersionInfo("0.1.4", "FletX")
        assert vi.version.major == 0
        assert vi.version.minor == 1
        assert vi.version.micro == 4


# ===================== CompatibilityResult =====================

class TestCompatibilityResult:

    def test_str_compatible(self):
        fletx_v = VersionInfo("0.1.4", "FletX")
        flet_v = VersionInfo("0.28.5", "Flet")
        cr = CompatibilityResult(True, fletx_v, flet_v)
        text = str(cr)
        assert "✅" in text
        assert "compatible" in text

    def test_str_incompatible(self):
        fletx_v = VersionInfo("0.1.4", "FletX")
        flet_v = VersionInfo("0.20.0", "Flet")
        cr = CompatibilityResult(False, fletx_v, flet_v)
        text = str(cr)
        assert "❌" in text
        assert "incompatible" in text

    def test_suggestions_default_empty(self):
        fletx_v = VersionInfo("0.1.4", "FletX")
        flet_v = VersionInfo("0.28.5", "Flet")
        cr = CompatibilityResult(True, fletx_v, flet_v)
        assert cr.suggestions == []


# ===================== VersionChecker =====================

class TestVersionChecker:

    def test_get_python_version(self):
        vc = VersionChecker()
        py_v = vc.get_python_version()
        assert py_v.package_name == "Python"
        assert py_v.version_str  # not empty

    def test_version_matches_same_minor(self):
        vc = VersionChecker()
        assert vc._version_matches("0.1.4", "0.1.0") is True
        assert vc._version_matches("0.1.4-rc1", "0.1.3") is True

    def test_version_matches_different_minor(self):
        vc = VersionChecker()
        assert vc._version_matches("0.2.0", "0.1.0") is False

    def test_version_matches_different_major(self):
        vc = VersionChecker()
        assert vc._version_matches("1.0.0", "0.1.0") is False

    def test_version_matches_invalid(self):
        vc = VersionChecker()
        assert vc._version_matches("invalid", "0.1.0") is False

    def test_normalize_version_strips_prerelease(self):
        vc = VersionChecker()
        result = vc._normalize_version_for_matrix("0.1.4rc1")
        assert result == "0.1.4"

    def test_normalize_version_stable(self):
        vc = VersionChecker()
        result = vc._normalize_version_for_matrix("0.1.4")
        assert result == "0.1.4"

    def test_get_compatibility_requirements_known(self):
        vc = VersionChecker()
        reqs = vc._get_compatibility_requirements("0.1.4")
        assert reqs is not None
        assert "flet" in reqs
        assert "python" in reqs

    def test_get_compatibility_requirements_unknown(self):
        vc = VersionChecker()
        reqs = vc._get_compatibility_requirements("99.99.99")
        assert reqs is None

    def test_generate_message_compatible(self):
        vc = VersionChecker()
        fletx_v = VersionInfo("0.1.4", "FletX")
        flet_v = VersionInfo("0.28.5", "Flet")
        python_v = VersionInfo("3.12.0", "Python")
        reqs = {"flet": ">=0.28.3,<0.30.0", "python": ">=3.12,<3.14"}

        msg, suggestions = vc._generate_compatibility_message(
            fletx_v, flet_v, python_v, True, True, reqs
        )
        assert "compatible" in msg
        assert suggestions == []

    def test_generate_message_flet_incompatible(self):
        vc = VersionChecker()
        fletx_v = VersionInfo("0.1.4", "FletX")
        flet_v = VersionInfo("0.20.0", "Flet")
        python_v = VersionInfo("3.12.0", "Python")
        reqs = {"flet": ">=0.28.3,<0.30.0", "python": ">=3.12,<3.14"}

        msg, suggestions = vc._generate_compatibility_message(
            fletx_v, flet_v, python_v, False, True, reqs
        )
        assert "not compatible" in msg
        assert len(suggestions) > 0

    def test_generate_message_python_incompatible(self):
        vc = VersionChecker()
        fletx_v = VersionInfo("0.1.4", "FletX")
        flet_v = VersionInfo("0.28.5", "Flet")
        python_v = VersionInfo("3.10.0", "Python")
        reqs = {"flet": ">=0.28.3,<0.30.0", "python": ">=3.12,<3.14"}

        msg, suggestions = vc._generate_compatibility_message(
            fletx_v, flet_v, python_v, True, False, reqs
        )
        assert "Python" in msg
        assert len(suggestions) > 0

    def test_generate_message_both_incompatible(self):
        vc = VersionChecker()
        fletx_v = VersionInfo("0.1.4", "FletX")
        flet_v = VersionInfo("0.20.0", "Flet")
        python_v = VersionInfo("3.10.0", "Python")
        reqs = {"flet": ">=0.28.3,<0.30.0", "python": ">=3.12,<3.14"}

        msg, suggestions = vc._generate_compatibility_message(
            fletx_v, flet_v, python_v, False, False, reqs
        )
        assert "Flet" in msg
        assert "Python" in msg
        assert len(suggestions) >= 2

    def test_get_fletx_version_caches(self):
        vc = VersionChecker()
        v1 = vc.get_fletx_version()
        v2 = vc.get_fletx_version()
        assert v1 is v2

    def test_get_python_version_caches(self):
        vc = VersionChecker()
        v1 = vc.get_python_version()
        v2 = vc.get_python_version()
        assert v1 is v2

    def test_get_flet_version(self):
        vc = VersionChecker()
        flet_v = vc.get_flet_version()
        assert flet_v.package_name == "Flet"
        assert flet_v.version_str  # not empty

    def test_get_flet_version_caches(self):
        vc = VersionChecker()
        v1 = vc.get_flet_version()
        v2 = vc.get_flet_version()
        assert v1 is v2

    def test_get_package_version_not_found(self):
        vc = VersionChecker()
        with pytest.raises(ImportError, match="Could not determine version"):
            vc._get_package_version("nonexistent_package_xyz_12345")

    def test_check_compatibility_returns_result(self):
        vc = VersionChecker()
        result = vc.check_compatibility()
        assert isinstance(result, CompatibilityResult)
        assert result.fletx_version is not None
        assert result.flet_version is not None

    def test_check_compatibility_unknown_version(self):
        vc = VersionChecker()
        vc._fletx_version = VersionInfo("99.99.99", "FletX")
        result = vc.check_compatibility()
        assert result.is_compatible is False
        assert "Unknown" in result.message

    def test_check_compatibility_exception_handling(self):
        """When check_compatibility encounters an error creating fallback VersionInfo,
        the exception propagates (bug in source: 'unknown' is not a valid version)."""
        from packaging.version import InvalidVersion
        vc = VersionChecker()
        with patch.object(vc, 'get_fletx_version', side_effect=Exception("test error")):
            with pytest.raises(InvalidVersion):
                vc.check_compatibility()

