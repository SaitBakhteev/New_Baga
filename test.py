import pytest
from script import cipher_text

def test_basic_encrypt():
    assert cipher_text("abc", 1, "encrypt") == "bcd"

def test_wrap_around():
    assert cipher_text("xyz", 3, "encrypt") == "abc"

def test_mixed_case():
    assert cipher_text("AbCd", 1, "encrypt") == "BcDe"

def test_non_letters_unchanged():
    assert cipher_text("Hello, World! 123", 5, "encrypt") == "Mjqqt, Btwqi! 123"

def test_decrypt_reverse():
    original = "SecretMessage"
    encrypted = cipher_text(original, 10, "encrypt")
    decrypted = cipher_text(encrypted, 10, "decrypt")
    assert decrypted == original

def test_large_shift():
    assert cipher_text("abc", 27, "encrypt") == "bcd"  # 27 % 26 = 1

def test_negative_shift():
    assert cipher_text("bcd", -1, "encrypt") == "abc"

def test_invalid_mode():
    with pytest.raises(ValueError):
        cipher_text("abc", 1, "invalid")

def test_invalid_shift_type():
    with pytest.raises(TypeError):
        cipher_text("abc", "1", "encrypt")

def test_empty_string():
    assert cipher_text("", 5, "encrypt") == ""
