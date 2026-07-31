from datetime import UTC, datetime

from suanming.pipelines.tarot.data import DECK, SPREADS
from suanming.runtime import run_pipeline


def test_tarot_deck_is_complete_and_unique() -> None:
    assert len(DECK) == 78
    assert len({card.id for card in DECK}) == 78
    assert sum(card.arcana == "major" for card in DECK) == 22
    assert sum(card.arcana == "minor" for card in DECK) == 56


def test_nine_spreads_are_available() -> None:
    assert len(SPREADS) == 9
    assert len(SPREADS["celtic_cross"]) == 10


def test_seed_reproduces_the_same_draw() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    first = run_pipeline(
        "tarot",
        {"spread": "three_card"},
        seed="repeatable",
        now=now,
    )
    second = run_pipeline(
        "tarot",
        {"spread": "three_card"},
        seed="repeatable",
        now=now,
    )
    assert first.result["cards"] == second.result["cards"]
    assert len({card["card_id"] for card in first.result["cards"]}) == 3
