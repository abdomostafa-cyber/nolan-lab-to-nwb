"""Smoke tests: the pinned stack imports and exposes the interfaces the conversion relies on."""

from importlib.metadata import version


def test_package_imports():
    import nolan_lab_to_nwb

    assert nolan_lab_to_nwb.__version__ == version("nolan-lab-to-nwb")


def test_openephys_legacy_interface_available():
    from neuroconv.datainterfaces import OpenEphysLegacyRecordingInterface

    assert OpenEphysLegacyRecordingInterface is not None


def test_pinned_versions():
    assert version("neuroconv") == "0.10.2"
    assert version("pynwb") == "4.2.0"
    assert version("nwbinspector") == "0.7.2"
