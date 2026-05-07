from src.speech import extract_style

def test_extract_style_picasso():
    assert extract_style("draw this in picasso style") == "picasso"

def test_extract_style_vangogh():
    assert extract_style("I want van gogh style please") == "van gogh"

def test_extract_style_default():
    assert extract_style("just draw something") == "default"

def test_extract_style_case_insensitive():
    assert extract_style("PICASSO style please") == "picasso"