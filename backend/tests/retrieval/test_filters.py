def test_메타데이터_필터가_워크스페이스와_문서조건을_만든다() -> None:
    from backend.app.retrieval.filters import RetrievalFilter, build_qdrant_filter

    qdrant_filter = build_qdrant_filter(
        RetrievalFilter(
            workspace_id="workspace-alpha",
            document_ids=["doc-1", "doc-2"],
            security_levels=["internal", "restricted"],
        ),
    )

    assert len(qdrant_filter.must) == 2
    assert qdrant_filter.must[0].key == "workspace_id"
    assert qdrant_filter.must[0].match.value == "workspace-alpha"
    assert len(qdrant_filter.must[1].should) == 2
    assert qdrant_filter.must[1].should[0].key == "security_level"
    assert qdrant_filter.must[1].should[0].match.value == "internal"
    assert qdrant_filter.must[1].should[1].match.value == "restricted"
    assert len(qdrant_filter.should) == 2
    assert qdrant_filter.should[0].key == "document_id"
    assert qdrant_filter.should[0].match.value == "doc-1"
    assert qdrant_filter.should[1].match.value == "doc-2"
