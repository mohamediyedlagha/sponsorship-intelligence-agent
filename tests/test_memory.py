from src.memory.database import Database
from src.utils.hashing import generate_content_hash


def test_article_memory(tmp_path):

    database_path = tmp_path / "test_agent.db"

    db = Database(
        database_path=database_path
    )

    content = (
        "Mistral AI announced "
        "a new enterprise platform."
    )

    content_hash = generate_content_hash(
        company="Mistral AI",
        title="New AI Platform",
        content=content,
    )

    article_id = db.save_article(
        company="Mistral AI",
        title="New AI Platform",
        url="https://example.com/article",
        source="Example",
        content=content,
        content_hash=content_hash,
    )

    assert article_id is not None
    assert db.get_article_count() == 1

    duplicate_id = db.save_article(
        company="Mistral AI",
        title="New AI Platform",
        url="https://example.com/article",
        source="Example",
        content=content,
        content_hash=content_hash,
    )

    assert duplicate_id is None
    assert db.get_article_count() == 1


def test_hash_normalization():

    hash_1 = generate_content_hash(
        company="Mistral AI",
        title="New AI Platform",
        content="A new enterprise AI product.",
    )

    hash_2 = generate_content_hash(
        company="  MISTRAL AI ",
        title="NEW   AI PLATFORM",
        content="A new   enterprise AI product.",
    )

    assert hash_1 == hash_2