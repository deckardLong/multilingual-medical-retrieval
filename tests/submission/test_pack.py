import hashlib, json, zipfile
import pytest
from pydantic import ValidationError
from submission import SubChunk, SubItem
from submission.pack import make_zip, read_zip, sha256, write_json

ITEMS = [SubItem(id=1, relevant_docs=["3"], relevant_chunks=[SubChunk(doc_id="3", chunk_text="triệu chứng 糖尿病")]),
         SubItem(id=2, relevant_docs=[], relevant_chunks=[])]


def test_write_json_is_valid_utf8_list_and_atomic(tmp_path):
    p = write_json(ITEMS, tmp_path / "sub" / "s.json")
    assert p.read_bytes().decode("utf-8").startswith("[") and "triệu chứng 糖尿病" in p.read_text("utf-8")
    assert json.loads(p.read_text("utf-8"))[1] == {"id": 2, "relevant_docs": [], "relevant_chunks": []}
    assert not list(p.parent.glob("*.tmp"))


def test_zip_has_exactly_one_file_at_the_root_with_the_given_name(tmp_path):
    j = write_json(ITEMS, tmp_path / "deep" / "dir" / "local-name.json")
    z = make_zip(j, tmp_path / "out" / "bai.zip", "submission.json")
    with zipfile.ZipFile(z) as f:
        assert f.namelist() == ["submission.json"]                         # không mang theo đường dẫn thư mục
    assert not list(z.parent.glob("*.tmp"))


def test_read_zip_gives_back_the_same_items(tmp_path):
    z = make_zip(write_json(ITEMS, tmp_path / "s.json"), tmp_path / "b.zip", "s.json")
    assert read_zip(z) == ITEMS


def _zip(path, files):
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return path


@pytest.mark.parametrize("files", [{}, {"a.json": "[]", "b.json": "[]"}, {"dir/a.json": "[]"}, {"dir\\a.json": "[]"}],
                         ids=["rỗng", "hai file", "thư mục con", "thư mục con kiểu windows"])
def test_read_zip_rejects_wrong_layout(tmp_path, files):
    with pytest.raises(ValueError, match="đúng một file ở gốc"):
        read_zip(_zip(tmp_path / "z.zip", files))


def test_read_zip_rejects_wrong_structure(tmp_path):
    with pytest.raises(ValidationError):
        read_zip(_zip(tmp_path / "z.zip", {"s.json": json.dumps([{"id": "1", "relevant_docs": [], "relevant_chunks": []}])}))
    with pytest.raises(ValidationError):
        read_zip(_zip(tmp_path / "z.zip", {"s.json": "{}"}))


def test_make_zip_overwrites_an_existing_zip(tmp_path):
    j = write_json(ITEMS, tmp_path / "s.json")
    z = tmp_path / "b.zip"
    make_zip(j, z, "s.json")
    write_json(ITEMS[:1], j)
    make_zip(j, z, "s.json")
    assert read_zip(z) == ITEMS[:1]


def test_sha256_matches_hashlib(tmp_path):
    p = tmp_path / "x.bin"; p.write_bytes(b"abc")
    assert sha256(p) == hashlib.sha256(b"abc").hexdigest()