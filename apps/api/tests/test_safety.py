from app.safety import screen_text


def test_high_severity_self_harm():
    a = screen_text("Honestly sometimes I just want to die")
    assert a is not None
    assert a.severity == "high"
    assert a.category == "self-harm"


def test_medium_severity_distress():
    a = screen_text("I feel so hopeless lately")
    assert a is not None
    assert a.severity == "medium"


def test_no_flag_on_ordinary_message():
    assert screen_text("I had a lovely cup of tea with my neighbour") is None


def test_empty():
    assert screen_text("") is None
    assert screen_text(None) is None
