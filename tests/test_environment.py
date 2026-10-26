"""Smoke tests: the pinned stack imports and exposes the interfaces the conversion relies on."""

from importlib.metadata import version


def test_package_imports():
    import nwb_conversion_demo

    assert nwb_conversion_demo.__version__ == version("nwb-conversion-demo")


def test_openephys_legacy_interface_available():
    from neuroconv.datainterfaces import OpenEphysLegacyRecordingInterface

    assert OpenEphysLegacyRecordingInterface is not None


def test_pinned_versions():
    assert version("neuroconv") == "0.10.2"
    assert version("pynwb") == "4.2.0"
    assert version("nwbinspector") == "0.7.2"
