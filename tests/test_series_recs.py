import base64
from collections import OrderedDict

from app.series_recs import (
    build_tag_specificity,
    build_taste_profile,
    score_recommendations,
    series_library_item_ids,
)


def _item_id(filename: str) -> str:
    return base64.b64encode(filename.encode("utf-8")).decode("ascii").rstrip("=").replace("+", "-").replace("/", "_")


def _query(**tiers) -> str:
    return "&".join(
        f"{tier}={','.join(_item_id(name.replace(' ', '_') + '.jpg') for name in names)}"
        for tier, names in tiers.items()
    )


def _rows(*tags, source="royalroad", confidence=1.0):
    return [
        {"tag": tag, "source": source, "user_id": "", "confidence": confidence}
        for tag in tags
    ]


class FakeStore:
    def __init__(self, tags):
        self.tags = tags

    def get_all_series_tags(self):
        return self.tags

    def get_all_series_descriptions(self):
        return {}


def _index(*names):
    return [{"seriesName": name} for name in names]


def test_ranking_is_deterministic_across_input_order():
    tags = OrderedDict([
        ("favorite", _rows("fantasy", "time loop")),
        ("alpha", _rows("fantasy", "time loop")),
        ("beta", _rows("fantasy", "time loop")),
        ("gamma", _rows("fantasy", "survival")),
    ])
    query = _query(S=["favorite"])
    series = _index("favorite", "alpha", "beta", "gamma")

    forward = score_recommendations(FakeStore(tags), query, series)
    reversed_tags = OrderedDict(reversed(list(tags.items())))
    backward = score_recommendations(FakeStore(reversed_tags), query, list(reversed(series)))

    assert [row["series_name"] for row in forward] == [row["series_name"] for row in backward]
    assert [row["score"] for row in forward] == sorted(
        [row["score"] for row in forward], reverse=True
    )


def test_rare_taste_signal_beats_tag_stuffing():
    tags = {
        "favorite": _rows("fantasy", "time loop"),
        "precise match": _rows("fantasy", "time loop", source="audible"),
        "tag stuffed": _rows(
            "fantasy", "adventure", "magic", "dragons", "academy", "military",
            "romance", "survival", "humorous", "epic", "progression",
        ),
        "broad one": _rows("fantasy", source="audible"),
        "broad two": _rows("fantasy", source="audible"),
    }
    results = score_recommendations(
        FakeStore(tags),
        _query(S=["favorite"]),
        _index("favorite", "precise match", "tag stuffed", "broad one", "broad two"),
    )

    assert results[0]["series_name"] == "precise match"


def test_opposite_tier_preferences_produce_different_top_results():
    tags = {
        "fire favorite": _rows("fire magic", "fantasy"),
        "ice favorite": _rows("ice magic", "fantasy"),
        "blazing path": _rows("fire magic", "adventure"),
        "frozen path": _rows("ice magic", "adventure"),
        "neutral path": _rows("adventure", "fantasy"),
    }
    store = FakeStore(tags)
    series = _index(*tags.keys())

    fire_user = score_recommendations(
        store,
        _query(S=["fire favorite"], E=["ice favorite"]),
        series,
    )
    ice_user = score_recommendations(
        store,
        _query(S=["ice favorite"], E=["fire favorite"]),
        series,
    )

    assert fire_user[0]["series_name"] == "blazing path"
    assert ice_user[0]["series_name"] == "frozen path"


def test_fresh_mode_requires_every_selected_tag():
    tags = {
        "both": _rows("cultivation", "time loop"),
        "cultivation only": _rows("cultivation"),
        "time loop only": _rows("time loop"),
    }
    results = score_recommendations(
        FakeStore(tags),
        "",
        _index(*tags.keys()),
        boost_tags=["cultivation", "time loop"],
        fresh=True,
    )

    assert [row["series_name"] for row in results] == ["both"]


def test_internal_ranking_fields_never_leak_to_api_payload():
    tags = {
        "favorite": _rows("dungeon core"),
        "candidate": _rows("dungeon core"),
        "background": _rows("unrelated"),
    }
    result = score_recommendations(
        FakeStore(tags),
        _query(S=["favorite"]),
        _index("favorite", "candidate", "background"),
    )[0]

    assert result["score"] == result["match_score"]
    assert not any(key.startswith("_") for key in result)


def test_taste_profile_counts_unique_liked_series_tags():
    tags = {
        "alpha": _rows("male lead", "time loop") + _rows("male lead", source="audible"),
        "beta": _rows("male lead", "magic"),
        "gamma": _rows("time loop"),
        "disliked": _rows("male lead", "time loop"),
    }
    profile = build_taste_profile(
        FakeStore(tags),
        _query(S=["alpha"], A=["beta"], B=["gamma"], E=["disliked"]),
        _index(*tags.keys()),
    )

    counts = {row["tag"]: row["count"] for row in profile["traits"]}
    assert counts["male lead"] == 2
    assert counts["time loop"] == 2
    assert profile["liked_series_count"] == 3
    assert profile["tier_counts"] == {"S": 1, "A": 1, "B": 1}


def test_taste_profile_bar_length_uses_count_and_hides_catalog_umbrellas():
    tags = {
        "alpha": _rows("male lead", "time loop", "fantasy", "science fiction & fantasy", "action & adventure"),
        "beta": _rows("male lead", "science fiction & fantasy"),
        "gamma": _rows("male lead", "science fiction & fantasy"),
        "delta": _rows("male lead", "science fiction & fantasy"),
        "epsilon": _rows("male lead", "science fiction & fantasy"),
        "zeta": _rows("time loop", "science fiction & fantasy"),
        "eta": _rows("time loop", "science fiction & fantasy"),
    }
    profile = build_taste_profile(
        FakeStore(tags),
        _query(S=["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta"]),
        _index(*tags.keys()),
    )

    traits = {row["tag"]: row for row in profile["traits"]}
    assert traits["male lead"]["count"] == 5
    assert traits["male lead"]["percentage"] == 100.0
    assert traits["time loop"]["count"] == 3
    assert traits["time loop"]["percentage"] == 60.0
    assert "fantasy" not in traits
    assert "science fiction & fantasy" not in traits
    assert "action & adventure" not in traits


def test_specificity_zeroes_universal_and_explicitly_excluded_tags():
    tags = {
        "one": _rows("shared", "fantasy", "action & adventure", "rare"),
        "two": _rows("shared"),
        "three": _rows("shared"),
        "four": _rows("shared"),
        "five": _rows("other"),
    }

    specificity = build_tag_specificity(tags)

    assert specificity["shared"] == 0.0
    assert specificity["fantasy"] == 0.0
    assert specificity["action & adventure"] == 0.0
    assert specificity["rare"] > 0


def test_non_scoring_tags_only_match_when_manually_boosted():
    for broad_tag in ("fantasy", "action & adventure"):
        tags = {
            "favorite": _rows(broad_tag, "private signal"),
            "candidate": _rows(broad_tag),
            "background one": _rows(broad_tag),
            "background two": _rows(broad_tag),
        }
        store = FakeStore(tags)
        series = _index(*tags.keys())

        automatic = score_recommendations(store, _query(S=["favorite"]), series)
        boosted = score_recommendations(
            store,
            _query(S=["favorite"]),
            series,
            boost_tags=[broad_tag],
        )
        fresh = score_recommendations(
            store,
            "",
            series,
            boost_tags=[broad_tag],
            fresh=True,
        )

        assert automatic == []
        assert {row["series_name"] for row in boosted} == {
            "background one", "background two", "candidate"
        }
        assert {row["series_name"] for row in fresh} == set(tags)


def test_series_library_item_ids_are_unique_and_in_reading_order():
    series = [{
        "seriesName": "The Long Path",
        "books": [
            {"libraryItemId": "book-3", "sequence": "3"},
            {"libraryItemId": "book-1", "sequence": "1"},
            {"libraryItemId": "book-2", "seriesSequence": "2"},
            {"libraryItemId": "book-2", "sequence": "2"},
            {"libraryItemId": "special", "sequence": None},
        ],
    }]

    assert series_library_item_ids("the long path", series) == [
        "book-1", "book-2", "book-3", "special"
    ]


def test_recommendation_reports_live_series_book_count():
    tags = {
        "favorite": _rows("time loop"),
        "candidate": _rows("time loop"),
        "background": _rows("survival"),
    }
    series = [
        {"seriesName": "favorite", "books": [{"libraryItemId": "fav-1", "sequence": 1}]},
        {"seriesName": "candidate", "books": [
            {"libraryItemId": "candidate-1", "sequence": 1},
            {"libraryItemId": "candidate-2", "sequence": 2},
        ]},
        {"seriesName": "background", "books": [{"libraryItemId": "background-1", "sequence": 1}]},
    ]

    result = score_recommendations(FakeStore(tags), _query(S=["favorite"]), series)[0]

    assert result["series_name"] == "candidate"
    assert result["book_count"] == 2
