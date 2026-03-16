from testsprite import TestSprite

def test_add_bookmark():
    sprite = TestSprite()
    sprite.add_bookmark("Example Title", "http://example.com")
    assert sprite.get_bookmark("Example Title") == "http://example.com"

def test_remove_bookmark():
    sprite = TestSprite()
    sprite.add_bookmark("Example Title", "http://example.com")
    sprite.remove_bookmark("Example Title")
    assert sprite.get_bookmark("Example Title") is None

def test_list_bookmarks():
    sprite = TestSprite()
    sprite.add_bookmark("Example Title", "http://example.com")
    assert sprite.list_bookmarks() == {"Example Title": "http://example.com"}