"""Test Unicode handling for Windows console compatibility."""

from cli.console import _can_encode_unicode, safe_text, safe_print
import sys


def test_encoding_detection():
    """Test that encoding detection works correctly."""
    print("=" * 50)
    print("UNICODE HANDLING TEST")
    print("=" * 50)

    # Test 1: Current console encoding
    current_encoding = sys.stdout.encoding or "utf-8"
    print(f"\nCurrent console encoding: {current_encoding}")

    # Test 2: Check if emoji can be encoded
    emoji = "\u2705"
    can_encode = _can_encode_unicode(emoji)
    safe_print(f"Can encode emoji '{emoji}': {can_encode}")

    # Test 3: Safe text conversion
    test_message = "\u2705 System is healthy."
    safe = safe_text(test_message)
    safe_print(f"\nOriginal:  {test_message}")
    safe_print(f"Safe text: {safe}")

    # Test 4: Multiple emojis
    test_multi = "\u2705 Success, \u274c Error, \u26a0 Warning"
    safe_multi = safe_text(test_multi)
    safe_print(f"\nOriginal:  {test_multi}")
    safe_print(f"Safe text: {safe_multi}")

    # Test 5: All safe symbols
    safe_print("\nAll safe symbol replacements:")
    for unicode_char, ascii_replacement in [
        ("\u2705", "[OK]"),
        ("\u274c", "[X]"),
        ("\u26a0", "[!]"),
        ("\u2139", "[i]"),
        ("\u2713", "[OK]"),
        ("\u2717", "[X]"),
    ]:
        can = _can_encode_unicode(unicode_char)
        converted = safe_text(unicode_char)
        safe_print(f"  {unicode_char} → {converted} (can encode: {can})")

    print("\n" + "=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    test_encoding_detection()
