from schemas.query import QueryRequest


def test_source_gets_pdf_extension_appended_when_missing():
    request = QueryRequest(question="hi", source="sample")
    assert request.source == "sample.pdf"


def test_source_left_unchanged_when_already_has_extension():
    request = QueryRequest(question="hi", source="sample.pdf")
    assert request.source == "sample.pdf"


def test_source_left_as_none_when_omitted():
    request = QueryRequest(question="hi")
    assert request.source is None
