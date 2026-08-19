from aipshield.engines import get_engine


def test_v01_production_engine_is_explicit_native_engine():
    engine = get_engine("blind-native")
    assert engine.name == "blind-watermark-native-adaptive"
