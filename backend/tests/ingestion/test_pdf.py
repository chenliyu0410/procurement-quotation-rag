from pathlib import Path

from app.ingestion.pdf import chunk_pages, extract_pages


def test_extracts_one_based_pages_and_chinese_text():
    path = Path(__file__).parents[1] / "fixtures" / "procurement_manual_excerpt.pdf"
    pages = extract_pages(path.read_bytes())
    assert [page.page_number for page in pages] == [1, 2]
    assert "採購" in pages[0].text
    assert "決標金額" in pages[1].text


def test_chunks_remain_on_their_source_page_and_keep_order():
    path = Path(__file__).parents[1] / "fixtures" / "procurement_manual_excerpt.pdf"
    chunks = chunk_pages(extract_pages(path.read_bytes()), max_chars=12, overlap_chars=3)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.page_number in (1, 2) for chunk in chunks)
    assert not any("預算" in chunk.text and "第二頁" in chunk.text for chunk in chunks)
