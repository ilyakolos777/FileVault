from utils.formatters import format_size

def test_format_size_bytes():
    result = format_size(713)
    assert "713" in result
    assert "B" in result

def test_format_size_kilobytes():
    result = format_size(1536)
    assert "1.5" in result
    assert "KB" in result

def test_format_size_megabytes():
    result = format_size(2621440)
    assert "2.5" in result
    assert "MB" in result

def test_format_size_gigabytes():
    result = format_size(3371549245)
    assert "3.1" in result
    assert "GB" in result

def test_format_size_zero():
    result = format_size(0)
    assert "0" in result
    assert "B" in result

def test_format_size_large_tb():
    result = format_size(1319413953331)
    assert "1.2" in result
    assert "TB" in result