import json
import os
import random
import tempfile
import unittest

from app import game_auth
from app import game_rules as R
from app.game_store import GameError, GameStore, clean_look

LOOK = {"ancestry": "dwarf", "skin": 1, "hair": "bald", "hairColor": 3, "beard": "braided", "face": "grumpy", "accent": 0}
LAUNCH = 1_800_000_000
BEFORE, AFTER = LAUNCH - 86400, LAUNCH + 86400


def item(slot="Weapon", rarity="Rare", n=1):
    raw = {"item_id": f"x{slot}{n}", "item_name": f"{rarity} {slot} {n}", "slot": slot, "rarity": rarity,
           "str": 16, "mag": 8, "def": 12, "hp": 10, "flavor_text": "", "series_tag": "", "icon": "/icons/x.png"}
    return R.item_view(raw)


CATALOG = [{"item_id": f"c{r}{s}", "item_name": f"{r} {s}", "slot": s, "rarity": r, "str": 8, "mag": 8, "def": 6, "hp": 10,
            "flavor_text": "", "series_tag": "", "icon": ""} for r in R.RARITIES for s in R.SLOTS]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = GameStore(os.path.join(self.tmp.name, "state.db"), now=LAUNCH)

    def tearDown(self):
        self.tmp.cleanup()

    def player(self, uid="u1", look=True, cls="brawler"):
        self.store.ensure_player(uid, uid)
        self.store.take_notices(uid)
        if look:
            self.store.set_look(uid, LOOK)
        if cls:
            self.store.set_class(uid, cls)
        return uid

    def bookmarks(self, uid="u1"):
        return self.store.get_player(uid)["bookmarks"]

    def badge_count(self, uid="u1"):
        return sum(1 for a in self.store.achievements(uid) if a["earned_at"])

    def give(self, uid, it):
        with self.store._conn() as c:
            return self.store._give_item(c, uid, it)


class PlayerTests(Base):
    def test_new_player_gets_welcome_chest_and_notice(self):
        self.store.ensure_player("u1", "reader")
        p = self.store.get_player("u1")
        self.assertEqual((p["level"], p["xp"], p["bookmarks"], p["bag_capacity"]), (1, 0, R.WELCOME_CHEST, 12))
        self.assertEqual(self.store.take_notices("u1"), [{"kind": "welcome", "bookmarks": R.WELCOME_CHEST}])
        self.assertEqual(self.store.take_notices("u1"), [])
        self.store.ensure_player("u1", "reader")  # second login: no second chest
        self.assertEqual(self.bookmarks(), R.WELCOME_CHEST)

    def test_first_look_and_class_free_then_cost(self):
        self.player(look=False, cls=None)
        self.store.set_look("u1", LOOK)
        self.store.set_class("u1", "ranger")
        self.assertEqual(self.bookmarks(), 50)
        self.store.set_look("u1", LOOK)  # unchanged: free
        self.assertEqual(self.bookmarks(), 50)
        self.store.set_look("u1", {**LOOK, "face": "cheerful"})
        self.store.set_class("u1", "paladin")
        self.assertEqual(self.bookmarks(), 50 - R.LOOK_CHANGE_COST - R.CLASS_CHANGE_COST)

    def test_cannot_spend_what_you_do_not_have(self):
        self.player(cls="ranger")
        self.store.set_class("u1", "paladin")   # 25
        self.store.set_class("u1", "brawler")   # 25 -> 0 left
        with self.assertRaises(GameError):
            self.store.set_class("u1", "hexcaster")
        self.assertEqual(self.store.get_player("u1")["cls"], "brawler")

    def test_look_validation(self):
        for bad in ({**LOOK, "ancestry": "gnome"}, {**LOOK, "skin": 9}, {**LOOK, "accent": True}, {**LOOK, "face": "<script>"}, "nope"):
            with self.assertRaises(ValueError):
                clean_look(bad)
        self.assertEqual(clean_look({**LOOK, "ancestry": "elf", "skin": 0, "beard": "full"})["beard"], "none")


class BookBonusTests(Base):
    def test_only_books_finished_after_launch_pay(self):
        self.player()
        self.store.sync_dungeons("u1", [("old", "Old Book", "", 10, BEFORE), ("new", "New Book", "", 10, AFTER), ("nodate", "No Date", "", 5, 0)])
        self.assertEqual(self.bookmarks(), 50 + R.BOOK_FINISHED_BONUS)
        self.assertEqual(self.store.take_notices("u1"), [{"kind": "book_finished", "title": "New Book", "item_id": "new", "bookmarks": 25, "series": []}])
        self.store.sync_dungeons("u1", [("new", "New Book", "", 10, AFTER)])  # paid once
        self.assertEqual(self.bookmarks(), 75)
        self.assertEqual(self.store.dungeon_counts("u1")["open"], 3)  # every finished book is a dungeon

    def test_books_finished_before_first_login_pay_at_first_login(self):
        self.store.sync_dungeons("u2", [("new", "New Book", "", 10, AFTER)])
        self.store.ensure_player("u2", "late")
        self.assertEqual(self.bookmarks("u2"), 50 + 25)


class InventoryTests(Base):
    def test_empty_slot_is_equipped_then_bag_then_pending(self):
        self.player()
        self.assertEqual(self.give("u1", item("Weapon", n=0)), "equipped")
        for n in range(12):
            self.assertEqual(self.give("u1", item("Weapon", n=n + 1)), "bag")
        self.assertEqual(self.give("u1", item("Weapon", n=99)), "pending")
        self.assertEqual(len(self.store.bag("u1")), 12)
        self.assertEqual(len(self.store.pending_loot("u1")), 1)

    def test_equip_swaps_into_bag(self):
        self.player()
        self.give("u1", item("Head", "Common", 1))
        self.give("u1", item("Head", "Epic", 2))
        epic = self.store.bag("u1")[0]
        self.store.equip("u1", epic["id"])
        self.assertEqual(self.store.equipped("u1")["Head"]["rarity"], "Epic")
        self.assertEqual([i["rarity"] for i in self.store.bag("u1")], ["Common"])

    def test_equip_best_wears_the_strongest_and_keeps_the_bag_size(self):
        self.player()
        self.give("u1", item("Head", "Common", 1))
        self.give("u1", item("Weapon", "Common", 1))
        strong = {**item("Head", "Epic", 2), "atk": 9, "def": 4, "hp": 40}
        self.give("u1", strong)
        self.give("u1", item("Ring", "Rare", 3))   # empty slot: _give_item already wears it
        before = len(self.store.bag("u1"))
        put_on = self.store.equip_best("u1")
        self.assertEqual([i["name"] for i in put_on], [strong["name"]])
        self.assertEqual(self.store.equipped("u1")["Head"]["name"], strong["name"])
        self.assertEqual(len(self.store.bag("u1")), before)
        self.assertEqual(self.store.equip_best("u1"), [])   # already best: nothing moves

    def test_best_loadout_depends_on_class(self):
        hp_ring = {"slot": "Ring", "atk": 0, "def": 0, "hp": 22, "id": 1}
        atk_ring = {"slot": "Ring", "atk": 5, "def": 0, "hp": 0, "id": 2}
        pick = lambda cls: R.best_loadout(cls, 5, {}, [hp_ring, atk_ring])["Ring"]["id"]
        self.assertEqual(pick("brawler"), 2)     # sturdy: attack first
        self.assertEqual(pick("hexcaster"), 1)   # frail: health first

    def test_better_marker_agrees_with_best(self):
        worn = {"Ring": {"slot": "Ring", "atk": 0, "def": 0, "hp": 0, "id": 9}}
        bag = [{"slot": "Ring", "atk": 0, "def": 0, "hp": 22, "id": 1}, {"slot": "Ring", "atk": 0, "def": 0, "hp": 0, "id": 2}]
        self.assertEqual(R.better_than_worn("hexcaster", 5, {}, worn, bag), [1])

    def test_equip_best_needs_a_class(self):
        self.player(cls=None)
        with self.assertRaises(GameError):
            self.store.equip_best("u1")

    def test_scrap_lock_and_ownership(self):
        self.player()
        self.give("u1", item("Ring", "Common", 1))
        self.give("u1", item("Ring", "Epic", 2))
        epic = self.store.bag("u1")[0]
        self.store.set_locked("u1", epic["id"], True)
        with self.assertRaises(GameError):
            self.store.scrap("u1", epic["id"])
        self.store.set_locked("u1", epic["id"], False)
        self.assertEqual(self.store.scrap("u1", epic["id"]), R.SCRAP_VALUE["Epic"])
        self.assertEqual(self.bookmarks(), 50 + 5)
        worn = self.store.equipped("u1")["Ring"]
        with self.assertRaises(GameError):
            self.store.scrap("u1", worn["id"])  # must take it off first
        self.player("u2")
        with self.assertRaises(GameError):
            self.store.equip("u2", worn["id"])  # not yours

    def test_pending_loot_take_or_scrap(self):
        self.player()
        for n in range(14):
            self.give("u1", item("Neck", "Rare", n))
        pend = self.store.pending_loot("u1")[0]
        with self.assertRaises(GameError):
            self.store.take_pending("u1", pend["pending_id"])
        self.store.scrap("u1", self.store.bag("u1")[0]["id"])
        self.store.take_pending("u1", pend["pending_id"])
        self.assertEqual(self.store.pending_loot("u1"), [])

    def test_battle_ready_ranks_levels_and_cap(self):
        self.player()
        with self.store._conn() as c:
            c.execute("UPDATE game_players SET bookmarks=5000, level=4 WHERE user_id='u1'")
        with self.assertRaises(GameError):
            self.store.buy_upgrade("u1", "battle_ready")  # rank 1 needs level 5
        with self.store._conn() as c:
            c.execute("UPDATE game_players SET level=50 WHERE user_id='u1'")
        for _ in range(2):  # a brawler's bar holds 3; Battle Ready stops one short
            self.store.buy_upgrade("u1", "battle_ready")
        with self.assertRaises(GameError):
            self.store.buy_upgrade("u1", "battle_ready")
        self.store.set_class("u1", "runeblade")  # bar of 5 reopens it, up to 4
        for _ in range(2):
            self.store.buy_upgrade("u1", "battle_ready")
        self.assertEqual(self.bookmarks(), 5000 - (100 + 250 + 500 + 800) - R.CLASS_CHANGE_COST + R.BADGE_BOOKMARKS * self.badge_count())  # level + spending badges pay
        with self.assertRaises(GameError):
            self.store.buy_upgrade("u1", "battle_ready")

    def test_gear_is_stamped_with_your_level(self):
        self.player()
        with self.store._conn() as c:
            c.execute("UPDATE game_players SET level=30 WHERE user_id='u1'")
        raw = item("Weapon", "Legendary")
        self.give("u1", dict(raw))
        worn = self.store.equipped("u1")["Weapon"]
        self.assertEqual(worn["ilvl"], 30)
        self.assertEqual(worn["atk"], round(raw["atk"] * R.item_level_mult(30)))
        self.assertGreater(worn["atk"], raw["atk"])

    def test_old_gear_keeps_its_stats_when_levels_arrive(self):
        self.player()
        raw = item("Chest", "Epic")
        with self.store._conn() as c:  # an item from before item levels
            c.execute("UPDATE game_players SET level=12 WHERE user_id='u1'")
            c.execute("INSERT INTO game_items(user_id, item_json, acquired_at) VALUES('u1', ?, 0)", (json.dumps(raw),))
        GameStore(self.store.db_path)  # startup migration
        it = self.store.bag("u1")[0]
        self.assertEqual((it["ilvl"], it["atk"], it["hp"]), (12, raw["atk"], raw["hp"]))

    def test_level_beats_rarity_eventually(self):
        early_legendary = R.item_level_mult(7) * 7.1   # average Legendary attack
        late_common = R.item_level_mult(50) * 1.4      # average Common attack
        self.assertLess(abs(early_legendary - late_common), 3)

    def test_bag_upgrades(self):
        self.player()
        self.assertEqual(self.store.buy_bag_upgrade("u1"), 16)
        self.assertEqual(self.bookmarks(), R.WELCOME_CHEST - R.BAG_UPGRADE_COSTS[0])
        with self.assertRaises(GameError):
            self.store.buy_bag_upgrade("u1")  # the next one costs more than what's left


class RunTests(Base):
    def setUp(self):
        super().setUp()
        self.player()
        self.store.sync_dungeons("u1", [("b1", "Book One", "DCC #1", 13.6, BEFORE), ("b2", "Epic Tome", "", 25, BEFORE)])

    def test_changing_class_mid_run_restarts_it_without_penalty(self):
        with self.store._conn() as c:
            c.execute("UPDATE game_players SET supplies_json=? WHERE user_id='u1'", ('{"potion": 1}',))
        run = self.store.start_run("u1", "b1", now=LAUNCH)
        self.assertEqual(run["cls"], "brawler")
        with self.assertRaises(GameError):
            self.store.set_class("u1", "ranger")  # must confirm the restart
        self.store.set_class("u1", "ranger", restart_run=True)
        self.assertIsNone(self.store.active_run("u1"))
        d = self.store.get_dungeon("u1", "b1")
        self.assertEqual((d["status"], d["attempts"]), ("waiting", 0))
        self.assertEqual(self.store.get_player("u1")["supplies"], {"potion": 1})  # packed supplies came back
        again = self.store.start_run("u1", "b1", now=LAUNCH + 50)
        self.assertEqual(again["cls"], "ranger")

    def test_a_run_from_an_old_class_is_restarted(self):
        self.store.start_run("u1", "b1", now=LAUNCH)
        with self.store._conn() as c:  # class changed before the restart prompt existed
            c.execute("UPDATE game_players SET cls='necromancer' WHERE user_id='u1'")
        self.assertIsNone(self.store.active_run("u1"))
        self.assertEqual(self.store.get_dungeon("u1", "b1")["status"], "waiting")

    def test_clear_awards_xp_bookmarks_and_loot(self):
        run = self.store.start_run("u1", "b1", now=LAUNCH)
        res = self.store.finish_run("u1", run["run_id"], {"outcome": "exit", "floors": 3, "kills": 6, "elites": 1}, CATALOG,
                                    now=LAUNCH + 200, rng=random.Random(1))
        self.assertEqual(res["bookmarks"], R.run_bookmarks(3, True, False))
        self.assertEqual(res["xp"], R.run_xp(1, 6, 1, False, 3, True, 13.6, 0, False))
        self.assertEqual(len(res["loot"]), 1)
        self.assertEqual(self.store.get_dungeon("u1", "b1")["status"], "cleared")
        with self.assertRaises(GameError):
            self.store.start_run("u1", "b1")

    def test_long_book_drops_two_rare_or_better(self):
        run = self.store.start_run("u1", "b2", now=LAUNCH)
        res = self.store.finish_run("u1", run["run_id"], {"outcome": "boss", "kills": 7}, CATALOG, now=LAUNCH + 200, rng=random.Random(3))
        self.assertEqual(len(res["loot"]), 2)
        self.assertTrue(all(R.RARITIES.index(i["rarity"]) >= 2 for i in res["loot"]))

    def test_death_sends_book_to_fallen_and_revive_costs(self):
        run = self.store.start_run("u1", "b1", now=LAUNCH)
        res = self.store.finish_run("u1", run["run_id"], {"outcome": "dead", "floors": 2, "kills": 4, "elites": 0}, CATALOG, now=LAUNCH + 200)
        self.assertEqual(res["loot"], [])
        self.assertEqual(res["xp"], R.run_xp(1, 4, 0, False, 2, False, 13.6, 0, True))
        self.assertEqual(self.store.get_dungeon("u1", "b1")["status"], "fallen")
        with self.assertRaises(GameError):
            self.store.start_run("u1", "b1")
        before = self.bookmarks()
        self.assertEqual(self.store.revive("u1", "b1"), R.revive_cost(13.6))
        self.assertEqual(self.bookmarks(), before - R.revive_cost(13.6))
        self.store.start_run("u1", "b1")

    def test_report_is_capped_to_what_a_run_can_produce(self):
        run = self.store.start_run("u1", "b1", now=LAUNCH)
        res = self.store.finish_run("u1", run["run_id"], {"outcome": "exit", "floors": 99, "kills": 999, "elites": 999}, CATALOG, now=LAUNCH + 200)
        self.assertEqual(res["xp"], R.run_xp(1, R.MAX_KILLS, R.MAX_KILLS, False, 3, True, 13.6, 0, False))

    def test_too_fast_and_double_finish_rejected(self):
        run = self.store.start_run("u1", "b1", now=LAUNCH)
        with self.assertRaises(GameError):
            self.store.finish_run("u1", run["run_id"], {"outcome": "exit"}, CATALOG, now=LAUNCH + 5)
        self.store.finish_run("u1", run["run_id"], {"outcome": "exit"}, CATALOG, now=LAUNCH + 60)
        with self.assertRaises(GameError):
            self.store.finish_run("u1", run["run_id"], {"outcome": "exit"}, CATALOG, now=LAUNCH + 90)

    def test_one_open_run_that_can_be_resumed(self):
        run = self.store.start_run("u1", "b1", now=LAUNCH)
        with self.assertRaises(GameError) as ctx:
            self.store.start_run("u1", "b2", now=LAUNCH + 100)
        self.assertIn("Resume it or give up", str(ctx.exception))
        self.store.save_progress("u1", run["run_id"], {"floor": 1, "step": 2, "hp": 40})
        active = self.store.active_run("u1")
        self.assertEqual((active["run_id"], active["title"], active["progress"]["floor"]), (run["run_id"], "Book One", 1))
        self.assertEqual(self.store.get_dungeon("u1", "b1")["status"], "waiting")  # leaving isn't a fall
        self.store.finish_run("u1", run["run_id"], {"outcome": "exit"}, CATALOG, now=LAUNCH + 3600)
        self.assertIsNone(self.store.active_run("u1"))
        with self.assertRaises(GameError):
            self.store.save_progress("u1", run["run_id"], {})

    def test_giving_up_counts_as_a_fall(self):
        run = self.store.start_run("u1", "b1", now=LAUNCH)
        self.store.save_progress("u1", run["run_id"], {"floor": 1, "kills": 3, "elites": 1})
        res = self.store.abandon_run("u1", run["run_id"], now=LAUNCH + 2)
        self.assertTrue(res["abandoned"])
        self.assertEqual(res["xp"], R.run_xp(1, 3, 1, False, 2, False, 13.6, 0, True))  # same as dying there
        self.assertEqual(res["bookmarks"], R.run_bookmarks(2, False, False))
        self.assertEqual(self.store.get_dungeon("u1", "b1")["status"], "fallen")
        self.assertIsNone(self.store.active_run("u1"))
        self.store.start_run("u1", "b2")

    def test_progress_size_is_limited(self):
        run = self.store.start_run("u1", "b1", now=LAUNCH)
        with self.assertRaises(ValueError):
            self.store.save_progress("u1", run["run_id"], {"junk": "x" * 9000})

    def test_level_up_carries_xp(self):
        with self.store._conn() as c:
            c.execute("UPDATE game_players SET xp=45 WHERE user_id='u1'")
        run = self.store.start_run("u1", "b1", now=LAUNCH)
        res = self.store.finish_run("u1", run["run_id"], {"outcome": "boss", "kills": 7, "elites": 1}, CATALOG, now=LAUNCH + 200)
        p = self.store.get_player("u1")
        self.assertGreaterEqual(res["levels_gained"], 1)
        self.assertEqual(p["level"], res["level"])
        self.assertLess(p["xp"], p["xp_next"])

    def test_pending_loot_blocks_new_runs(self):
        with self.store._conn() as c:
            c.execute("INSERT INTO game_pending_loot(user_id, item_json, created_at) VALUES('u1','{}',0)")
        with self.assertRaises(GameError):
            self.store.start_run("u1", "b1")


class StoreTests(Base):
    def setUp(self):
        super().setUp()
        self.player()
        books = [(f"b{i}", f"Book {i}", "", 13.6, BEFORE) for i in range(12)]
        self.store.sync_dungeons("u1", books)
        with self.store._conn() as c:
            c.execute("UPDATE game_players SET bookmarks=1000 WHERE user_id='u1'")

    def clear(self, n):
        with self.store._conn() as c:
            c.execute(f"UPDATE game_dungeons SET status='cleared' WHERE user_id='u1' AND item_id IN ({','.join('?' * n)})",
                      [f"b{i}" for i in range(n)])

    def test_store_locked_until_ten_clears(self):
        self.clear(9)
        self.assertFalse(self.store.store_view("u1", CATALOG)["unlocked"])
        for buy in (lambda: self.store.buy_crate("u1", CATALOG), lambda: self.store.buy_supply("u1", "potion"),
                    lambda: self.store.buy_stock("u1", 0, CATALOG)):
            with self.assertRaises(GameError):
                buy()
        self.clear(10)
        self.assertTrue(self.store.store_view("u1", CATALOG)["unlocked"])

    def stock_with_legendary(self):
        """A day whose stock has a Legendary (they're rare, so search for one)."""
        day = next(d for d in range(LAUNCH, LAUNCH + 4000 * 86400, 86400)
                   if R.store_stock(R.day_key(d), CATALOG)[-1]["item"]["rarity"] == "Legendary")
        return day + 3 * 3600

    def test_daily_stock_is_shared_first_come_first_served(self):
        self.clear(10)
        self.player("u2", cls="ranger")
        self.store._require_store = lambda uid: None   # u2 hasn't cleared 10 dungeons; skip the lock
        now = LAUNCH + 3 * 3600
        view = self.store.store_view("u1", CATALOG, now=now)
        self.assertEqual(len(view["stock"]), 5)
        self.assertIsNone(view["stock"][0]["sold"])
        self.assertTrue(all(o["upgrade"] for o in view["stock"]))   # wearing nothing: everything is an upgrade
        self.store.buy_stock("u1", 0, CATALOG, now=now)
        with self.assertRaises(GameError):   # gone for everyone, not just u1
            self.store.buy_stock("u2", 0, CATALOG, now=now)
        self.assertEqual(self.store.store_view("u2", CATALOG, now=now)["stock"][0]["sold"], {"by": "u1", "you": False})
        self.assertTrue(self.store.store_view("u1", CATALOG, now=now)["stock"][0]["sold"]["you"])
        tomorrow = R.next_day_start(now) + 3600
        self.assertIsNone(self.store.store_view("u2", CATALOG, now=tomorrow)["stock"][0]["sold"])   # midnight restock

    def test_not_enough_bookmarks_leaves_it_for_sale(self):
        self.clear(10)
        now = self.stock_with_legendary()
        with self.store._conn() as c:
            c.execute("UPDATE game_players SET bookmarks=100 WHERE user_id='u1'")
        with self.assertRaises(GameError):
            self.store.buy_stock("u1", 4, CATALOG, now=now)
        self.assertIsNone(self.store.store_view("u1", CATALOG, now=now)["stock"][4]["sold"])

    def test_legendary_is_rare_and_expensive(self):
        days = [R.day_key(LAUNCH + d * 86400) for d in range(3650)]
        legendary = sum(R.store_stock(k, CATALOG)[-1]["item"]["rarity"] == "Legendary" for k in days)
        self.assertTrue(3 <= legendary <= 20, legendary)   # about once a year over ten years
        self.clear(10)
        now = self.stock_with_legendary()
        offer = self.store.store_view("u1", CATALOG, now=now)["stock"][4]
        self.assertEqual((offer["item"]["rarity"], offer["price"]), ("Legendary", R.STORE_PRICES["Legendary"]))
        got = self.store.buy_stock("u1", 4, CATALOG, now=now)
        self.assertTrue(got["store_only"])
        self.assertEqual(self.bookmarks(), 1000 - R.STORE_PRICES["Legendary"] + R.BADGE_BOOKMARKS * self.badge_count())
        self.assertTrue(any("bought the Legendary" in f["payload"]["text"] for f in self.store.list_feed()))

    def test_crate_gives_an_item(self):
        self.clear(10)
        got = self.store.buy_crate("u1", CATALOG, rng=random.Random(2))
        self.assertIn(got["placed"], ("equipped", "bag"))
        self.assertEqual(self.bookmarks(), 1000 - R.CRATE_COST + R.BADGE_BOOKMARKS * self.badge_count())

    def test_supplies_carry_limit_and_packing(self):
        self.clear(10)
        for k in ("potion", "lantern", "coin"):
            self.store.buy_supply("u1", k)
        with self.assertRaises(GameError):
            self.store.buy_supply("u1", "smoke")
        run = self.store.start_run("u1", "b11", now=LAUNCH)
        self.assertEqual(run["supplies"], {"potion": 1, "lantern": 1, "coin": 1})
        self.assertEqual(self.store.get_player("u1")["supplies"], {})  # packed
        res = self.store.finish_run("u1", run["run_id"], {"outcome": "exit", "supplies_used": {"potion": 1}}, CATALOG,
                                    now=LAUNCH + 100, rng=random.Random(4))
        self.assertTrue(res["coin_used"])
        self.assertEqual(res["supplies_returned"], {"lantern": 1})
        self.assertEqual(self.store.get_player("u1")["supplies"], {"lantern": 1})

    def test_unused_supplies_come_back_after_a_death(self):
        self.clear(10)
        self.store.buy_supply("u1", "coin")
        run = self.store.start_run("u1", "b11", now=LAUNCH)
        res = self.store.finish_run("u1", run["run_id"], {"outcome": "dead"}, CATALOG, now=LAUNCH + 100)
        self.assertFalse(res["coin_used"])
        self.assertEqual(self.store.get_player("u1")["supplies"], {"coin": 1})


class ShelfTests(Base):
    def test_shelf_sorts_newest_longest_random(self):
        self.player()
        self.store.sync_dungeons("u1", [("a", "Short new", "", 3, 300), ("b", "Long old", "", 30, 100)])
        self.assertEqual([d["item_id"] for d in self.store.list_dungeons("u1", sort="new")], ["a", "b"])
        self.assertEqual([d["item_id"] for d in self.store.list_dungeons("u1", sort="long")], ["b", "a"])
        self.assertEqual(sorted(d["item_id"] for d in self.store.list_dungeons("u1", sort="random")), ["a", "b"])


class BadgeTests(Base):
    def play(self, uid, item_id, outcome, feats=None, kills=3, t=0):
        run = self.store.start_run(uid, item_id, now=LAUNCH + t)
        return self.store.finish_run(uid, run["run_id"], {"outcome": outcome, "floors": 3 if outcome != "dead" else 1,
                                                          "kills": kills, "elites": 0, "feats": feats or {}},
                                     CATALOG, now=LAUNCH + t + 100, rng=random.Random(1))

    def keys(self, uid="u1"):
        return {a["key"] for a in self.store.achievements(uid) if a["earned_at"]}

    def test_first_clear_and_boss_badges_with_notice_and_feed(self):
        self.player()
        self.store.sync_dungeons("u1", [("b1", "Book", "", 5, BEFORE)])
        res = self.play("u1", "b1", "boss", {"no_potion": True, "clutch": True})
        got = {b["key"] for b in res["badges"]}
        self.assertTrue({"first_blood", "first_clear", "first_boss", "no_potion_boss", "clutch"} <= got)
        self.assertNotIn("stairs_5", got)
        notices = self.store.take_notices("u1")
        self.assertIn("First Blood", [n.get("name") for n in notices if n["kind"] == "achievement"])
        self.assertIn("achievement", [f["kind"] for f in self.store.list_feed()])
        self.assertEqual(len(self.store.achievements("u1")), 45)

    def test_each_badge_pays_bookmarks_once(self):
        self.player()
        self.store.sync_dungeons("u1", [("b1", "Book", "", 5, BEFORE), ("b2", "B2", "", 5, BEFORE)])
        before = self.bookmarks()
        res = self.play("u1", "b1", "exit")
        earned = len(res["badges"])
        self.assertGreater(earned, 0)
        self.assertEqual(self.bookmarks(), before + res["bookmarks"] + R.BADGE_BOOKMARKS * earned)
        mid = self.bookmarks()
        res2 = self.play("u1", "b2", "exit", t=500)
        self.assertEqual(self.bookmarks(), mid + res2["bookmarks"] + R.BADGE_BOOKMARKS * len(res2["badges"]))
        self.assertTrue(all(b["bookmarks"] == R.BADGE_BOOKMARKS for b in res["badges"]))

    def test_badges_awarded_once(self):
        self.player()
        self.store.sync_dungeons("u1", [("b1", "Book", "", 5, BEFORE), ("b2", "Book 2", "", 5, BEFORE)])
        self.play("u1", "b1", "exit")
        res = self.play("u1", "b2", "exit", t=500)
        self.assertNotIn("first_clear", {b["key"] for b in res["badges"]})

    def test_floor_one_death_and_comeback(self):
        self.player()
        self.store.sync_dungeons("u1", [("s1", "One", "Saga #1", 5, BEFORE)])
        self.play("u1", "s1", "dead", kills=0)
        self.assertIn("floor_one", self.keys())
        self.store.revive("u1", "s1")
        self.play("u1", "s1", "exit", t=500)
        self.assertIn("comeback", self.keys())

    def test_abandon_is_not_a_floor_one_death(self):
        self.player()
        self.store.sync_dungeons("u1", [("b1", "Book", "", 5, BEFORE)])
        run = self.store.start_run("u1", "b1", now=LAUNCH)
        self.store.abandon_run("u1", run["run_id"], now=LAUNCH + 5)
        self.assertNotIn("floor_one", self.keys())

    def test_class_badges_only_count_for_that_class(self):
        self.player(cls="brawler")
        self.store.sync_dungeons("u1", [("b1", "Book", "", 5, BEFORE), ("b2", "B2", "", 5, BEFORE)])
        self.play("u1", "b1", "boss", {"pets": ["wolf", "hawk", "bear", "skeleton", "ghoul", "wraith"], "overcharge_boss": True})
        self.assertFalse({"full_menagerie", "overcharge_boss", "full_crypt"} & self.keys())
        self.store.set_class("u1", "beastmaster")
        self.play("u1", "b2", "exit", {"pets": ["wolf", "hawk", "bear", "dragon"]}, t=500)
        self.assertIn("full_menagerie", self.keys())
        self.assertNotIn("full_crypt", self.keys())

    def test_spending_and_legendary(self):
        self.player()
        with self.store._conn() as c:
            c.execute("UPDATE game_players SET bookmarks=600 WHERE user_id='u1'")
            self.store._spend(c, "u1", 500)
        self.give("u1", item(rarity="Legendary"))
        self.assertTrue({"big_spender", "legendary"} <= self.keys())


class PracticeAndPartyTests(Base):
    def test_practice_config_scales_and_pays_nothing(self):
        self.player()
        self.store.sync_dungeons("u1", [("b1", "Book", "", 5, BEFORE)])
        easy = self.store.practice_config("u1", "easy", 2)
        hard = self.store.practice_config("u1", "hard", 1)
        self.assertTrue(easy["practice"])
        self.assertEqual(easy["monsters"]["tier"], 2)
        self.assertLess(easy["enemy_scale"]["hp"], 1)
        self.assertGreater(hard["enemy_scale"]["hp"], 1)
        self.assertEqual(easy["supplies"], {})
        self.assertIsNone(self.store.active_run("u1"))  # nothing saved
        with self.assertRaises(ValueError):
            self.store.practice_config("u1", "nightmare", 1)
        with self.assertRaises(ValueError):
            self.store.practice_config("u1", "easy", 9)

    def test_party_lists_finished_characters_by_level(self):
        self.player("u1")
        self.player("u2", cls="ranger")
        self.player("u3", look=False, cls=None)  # still building: hidden
        with self.store._conn() as c:
            c.execute("UPDATE game_players SET level=4 WHERE user_id='u2'")
        self.give("u2", item())
        party = self.store.party()
        self.assertEqual([m["username"] for m in party], ["u2", "u1"])
        self.assertIn("Weapon", party[0]["gear"])
        self.assertEqual(party[1]["badges"], 0)
        self.assertEqual(party[0]["stats"], R.player_stats("ranger", 4, list(party[0]["gear"].values()), {}))  # gear counted


class SeriesRewardTests(Base):
    """Finishing a series: 5 bookmarks a book (new books only when catching up).
    5+ book series also get a chest: Epic once, then Rare when new books arrive."""
    def library(self, n, extra=()):
        items = [{"libraryItemId": f"s{i}", "seriesName": f"Saga #{i}"} for i in range(1, n + 1)] + list(extra)
        self.store.series_index, self.store.item_series = R.build_series_index(items)
        return items

    def setUp(self):
        super().setUp()
        self.player()

    def clear(self, *ids, t=0):
        res = None
        for n, i in enumerate(ids):
            self.store.sync_dungeons("u1", [(i, i, "Saga", 5, BEFORE)])
            res = BadgeTests.play(self, "u1", i, "exit", t=t + 500 * n)
        return res

    def test_parse_and_index(self):
        self.assertEqual(R.parse_series("Ark Royal #4, Warspite #1"), [("ark royal", "Ark Royal", 4.0), ("warspite", "Warspite", 1.0)])
        idx, _ = R.build_series_index([{"libraryItemId": f"b{i}", "seriesName": f"X #{i}"} for i in (1, 2, 3, 4, 6)])
        self.assertFalse(idx["x"]["qualifies"])  # book 5 missing blocks it
        idx, _ = R.build_series_index([{"libraryItemId": f"b{i}", "seriesName": f"Y #{i}"} for i in (1, 2, 3, 4)])
        self.assertFalse(idx["y"]["qualifies"])  # too short

    def test_finale_epic_once_then_caught_up_rare(self):
        self.library(5, [{"libraryItemId": "nov", "seriesName": "Saga #2.5"}, {"libraryItemId": "s3b", "seriesName": "Saga #3"}])
        res = self.clear("s1", "s2", "s3", "s4")
        self.assertIsNone(res["series_reward"])
        self.store.sync_dungeons("u1", [("s5", "s5", "Saga", 5, BEFORE)])
        preview = {d["item_id"]: d["series_reward"] for d in self.store.list_dungeons("u1")}
        self.assertEqual(preview["s5"]["kind"], "finale")  # shelf shows it before you play
        res = BadgeTests.play(self, "u1", "s5", "exit", t=5000)
        self.assertEqual(res["series_reward"]["kind"], "finale")
        self.assertIn(res["loot"][0]["rarity"], ("Epic", "Legendary"))
        self.assertIn("series_done", {a["key"] for a in self.store.achievements("u1") if a["earned_at"]})
        self.assertTrue(any("finished all 5 books of Saga" in f["payload"]["text"] for f in self.store.list_feed()))
        # the novella and the second edition of book 3 were never needed
        # A sixth book comes out: catching up again pays a Rare, not a second Epic.
        self.library(6)
        self.store.sync_dungeons("u1", [("s6", "s6", "Saga", 5, BEFORE)])
        res = BadgeTests.play(self, "u1", "s6", "exit", t=9000)
        self.assertEqual(res["series_reward"]["kind"], "caught_up")
        self.assertIn(res["loot"][0]["rarity"], ("Rare", "Epic", "Legendary"))

    def test_short_series_pays_bookmarks_and_a_popup_but_no_chest(self):
        self.library(3)
        self.clear("s1", "s2")
        self.store.take_notices("u1")
        self.store.sync_dungeons("u1", [("s3", "s3", "Saga", 5, BEFORE)])
        preview = {d["item_id"]: d["series_reward"] for d in self.store.list_dungeons("u1")}
        self.assertEqual((preview["s3"]["bookmarks"], preview["s3"]["chest"]), (15, False))
        before = self.bookmarks()
        res = BadgeTests.play(self, "u1", "s3", "exit", t=5000)
        self.assertEqual(res["series_bookmarks"], 15)   # 3 books × 5
        badge_pay = sum(n.get("bookmarks", 0) for n in self.store.take_notices("u1") if n["kind"] == "achievement")
        self.assertEqual(self.bookmarks() - before, res["bookmarks"] + 15 + badge_pay)
        self.assertNotIn("series_done", {a["key"] for a in self.store.achievements("u1") if a["earned_at"]})  # that badge is for 5+ books

    def test_finale_popup_and_caught_up_pays_new_books(self):
        self.library(5)
        self.clear("s1", "s2", "s3", "s4")
        self.store.take_notices("u1")
        res = self.clear("s5", t=5000)
        self.assertEqual(res["series_bookmarks"], 25)
        pop = [n for n in self.store.take_notices("u1") if n["kind"] == "series_complete"]
        self.assertEqual(len(pop), 1)
        self.assertEqual((pop[0]["outcome"], pop[0]["books"], pop[0]["bookmarks"]), ("finale", 5, 25))
        self.assertIn(pop[0]["chest_rarity"], ("Epic", "Legendary"))
        self.library(7)
        self.store.sync_dungeons("u1", [("s6", "s6", "Saga", 5, BEFORE)])
        self.clear("s6", t=9000)   # book 7 still to go: not caught up yet
        res = self.clear("s7", t=12000)
        self.assertEqual((res["series_reward"]["kind"], res["series_bookmarks"]), ("caught_up", 10))   # 2 new books

    def test_no_second_reward_without_new_books(self):
        self.library(5, [{"libraryItemId": "s5b", "seriesName": "Saga #5"}])
        self.clear("s1", "s2", "s3", "s4", "s5")
        res = self.clear("s5b", t=9000)  # another edition of the last book
        self.assertIsNone(res["series_reward"])

    def test_gap_in_library_blocks_it(self):
        self.library(6)
        self.store.series_index, self.store.item_series = R.build_series_index(
            [{"libraryItemId": f"s{i}", "seriesName": f"Saga #{i}"} for i in (1, 2, 3, 4, 5, 7)])
        res = self.clear("s1", "s2", "s3", "s4", "s5", "s7")
        self.assertIsNone(res["series_reward"])

    def test_fallen_book_doesnt_count(self):
        self.library(5)
        self.clear("s1", "s2", "s3")
        self.store.sync_dungeons("u1", [("s4", "s4", "Saga", 5, BEFORE), ("s5", "s5", "Saga", 5, BEFORE)])
        BadgeTests.play(self, "u1", "s4", "dead", t=3000)
        res = BadgeTests.play(self, "u1", "s5", "exit", t=4000)
        self.assertIsNone(res["series_reward"])


class ArenaTests(Base):
    def setUp(self):
        super().setUp()
        self.player("u1", cls="brawler")
        self.player("u2", cls="paladin")
        self.player("u3", cls="hexcaster")
        with self.store._conn() as c:
            c.execute("UPDATE game_players SET level=20 WHERE user_id='u3'")
            c.execute("UPDATE game_players SET level=8 WHERE user_id='u2'")

    def duel(self, uid, foe, outcome, t=0, **pct):
        d = self.store.start_duel(uid, foe, now=LAUNCH + t)
        return d, self.store.finish_duel(uid, d["duel_id"], {"outcome": outcome, **pct}, now=LAUNCH + t + 60)

    def test_ladder_starts_by_level_and_ghost_uses_real_stats(self):
        view = self.store.arena_view("u1", now=LAUNCH)
        self.assertEqual([r["username"] for r in view["ladder"]], ["u3", "u2", "u1"])
        d = self.store.start_duel("u1", "u3", now=LAUNCH)
        self.assertEqual(d["ghost"]["stats"], R.player_stats("hexcaster", 20, [], {}))
        self.assertEqual(d["ghost"]["moves"], R.GHOST_MOVES["hexcaster"][0])
        with self.assertRaises(GameError):
            self.store.start_duel("u1", "u1", now=LAUNCH)

    def test_win_swaps_places_and_pays(self):
        before = self.bookmarks("u1")
        _, res = self.duel("u1", "u3", "win")
        self.assertEqual((res["won"], res["moved"], res["rank_before"], res["rank_after"]), (True, True, 3, 1))
        self.assertEqual([r["username"] for r in self.store.arena_view("u1", now=LAUNCH)["ladder"]], ["u1", "u2", "u3"])
        earned = {a["key"] for a in self.store.achievements("u1") if a["earned_at"]}
        self.assertTrue({"duel_win", "giant_slayer", "arena_top"} <= earned)
        self.assertEqual(self.bookmarks("u1") - before, R.DUEL_WIN_BOOKMARKS + R.BADGE_BOOKMARKS * 3)
        note = [n for n in self.store.take_notices("u3") if n["kind"] == "duel"][0]
        self.assertEqual((note["challenger"], note["ghost_won"]), ("u1", False))

    def test_loss_pays_the_defender_and_keeps_ranks(self):
        before = self.bookmarks("u3") + R.BADGE_BOOKMARKS * 2   # u3's level 5 and 10 badges are checked too
        _, res = self.duel("u1", "u3", "lose")
        self.assertFalse(res["won"])
        self.assertEqual([r["username"] for r in self.store.arena_view("u1", now=LAUNCH)["ladder"]], ["u3", "u2", "u1"])
        self.assertEqual(self.bookmarks("u3") - before, R.DUEL_DEFEND_BOOKMARKS)
        view = self.store.arena_view("u1", now=LAUNCH)
        self.assertEqual({r["username"]: (r["wins"], r["losses"]) for r in view["ladder"]}["u3"], (1, 0))

    def test_beating_someone_below_you_doesnt_drop_you(self):
        _, res = self.duel("u3", "u1", "win")
        self.assertFalse(res["moved"])
        self.assertEqual(res["rank_after"], 1)

    def test_time_limit_goes_to_more_health_left(self):
        _, res = self.duel("u1", "u2", "time", my_pct=40, ghost_pct=35)
        self.assertTrue(res["won"])
        _, res = self.duel("u1", "u2", "time", t=100, my_pct=10, ghost_pct=35)
        self.assertFalse(res["won"])

    def test_daily_limit_and_no_double_finish(self):
        for i in range(R.DUEL_DAILY_LIMIT):
            d, _ = self.duel("u1", "u2", "lose", t=i * 100)
        with self.assertRaises(GameError):
            self.store.start_duel("u1", "u2", now=LAUNCH + 1000)
        with self.assertRaises(GameError):
            self.store.finish_duel("u1", d["duel_id"], {"outcome": "win"}, now=LAUNCH + 2000)
        tomorrow = R.next_day_start(LAUNCH) + 3600
        self.store.start_duel("u1", "u2", now=tomorrow)   # a new day, new challenges

    def test_too_fast_is_rejected(self):
        d = self.store.start_duel("u1", "u2", now=LAUNCH)
        with self.assertRaises(GameError):
            self.store.finish_duel("u1", d["duel_id"], {"outcome": "win"}, now=LAUNCH + 2)

    def test_month_end_crowns_the_champion(self):
        self.store.arena_view("u1", now=LAUNCH)            # this month starts
        self.duel("u1", "u3", "win", t=60)                 # u1 takes #1
        next_month = LAUNCH + 40 * 86400
        self.store.arena_view("u2", now=next_month)
        self.assertIn("arena_champion", {a["key"] for a in self.store.achievements("u1") if a["earned_at"]})
        self.assertEqual(self.store.arena_view("u2", now=next_month)["champions"][0]["username"], "u1")


class ArenaWeekTests(ArenaTests):
    MONDAY = R.week_start(LAUNCH) + 7 * 86400 + 3600      # a fresh week to play in

    def play_week(self):
        self.store.settle_arena_week(CATALOG, now=self.MONDAY)   # this week's row exists

    def test_active_number_one_gets_an_epic_and_top_winner_a_rare(self):
        self.play_week()
        t = self.MONDAY - LAUNCH
        self.duel("u3", "u1", "win", t=t + 100)    # u3 (#1) fights this week
        self.duel("u2", "u1", "win", t=t + 200)
        self.duel("u2", "u1", "win", t=t + 300)    # u2: most wins (2)
        next_week = self.MONDAY + 7 * 86400
        self.store.settle_arena_week(CATALOG, now=next_week, rng=random.Random(1))
        champ = [n for n in self.store.take_notices("u3") if n["kind"] == "arena_week"][0]
        climb = [n for n in self.store.take_notices("u2") if n["kind"] == "arena_week"][0]
        self.assertEqual(champ["prize"], "champion")
        self.assertIn(champ["item"]["rarity"], ("Epic", "Legendary"))
        self.assertEqual((climb["prize"], climb["item"]["rarity"]), ("climber", "Rare"))
        self.store.settle_arena_week(CATALOG, now=next_week + 3600)   # only once
        self.assertEqual([n for n in self.store.take_notices("u3") if n["kind"] == "arena_week"], [])
        view = self.store.arena_view("u1", now=next_week)
        self.assertEqual(view["last_week"], {"champion": "u3", "climber": "u2"})

    def test_idle_number_one_gets_nothing(self):
        self.play_week()
        self.duel("u1", "u2", "win", t=self.MONDAY - LAUNCH + 100)   # u1 climbs past u2, but #1 (u3) never fights
        self.store.settle_arena_week(CATALOG, now=self.MONDAY + 7 * 86400)
        self.assertEqual([n for n in self.store.take_notices("u3") if n["kind"] == "arena_week"], [])
        self.assertEqual([n["prize"] for n in self.store.take_notices("u1") if n["kind"] == "arena_week"], ["climber"])

    def test_tied_winners_get_no_rare(self):
        self.play_week()
        t = self.MONDAY - LAUNCH
        self.duel("u1", "u3", "win", t=t + 100)    # u1 takes #1 (and fought)
        self.duel("u2", "u3", "win", t=t + 200)
        self.duel("u3", "u2", "win", t=t + 300)    # u2 and u3: one win each
        self.store.settle_arena_week(CATALOG, now=self.MONDAY + 7 * 86400)
        prizes = {u: [n["prize"] for n in self.store.take_notices(u) if n["kind"] == "arena_week"] for u in ("u1", "u2", "u3")}
        self.assertEqual(prizes, {"u1": ["champion"], "u2": [], "u3": []})


class ThemeTests(Base):
    def test_pick_theme(self):
        cases = {("Science Fiction & Fantasy",): "dungeon", ("Science Fiction & Fantasy:Science Fiction:Space Opera",): "station",
                 ("science fiction", "fantasy"): "dungeon",  # a weak tag alone isn't enough
                 ("paranormal", "paranormal & urban", "epic"): "dungeon", ("urban fantasy", "paranormal"): "city",
                 ("post-apocalyptic", "science fiction"): "ruins", ("cultivation", "fantasy"): "sect",
                 ("horror", "dark fantasy"): "crypt", ("vrmmo", "litrpg"): "digital", ("monster tamer", "dragons & mythical creatures"): "wilds",
                 ("magic academy",): "academy", (): "dungeon"}
        for tags, want in cases.items():
            self.assertEqual(R.pick_theme(tags), want, tags)

    def test_runs_and_shelf_carry_the_theme(self):
        self.player()
        self.store.sync_dungeons("u1", [("b1", "Book", "Saga #1", 5, BEFORE)])
        self.store.genre_tags = lambda item_id, series: (["cultivation"], "") if series.startswith("Saga") else ([], "")
        self.assertEqual(self.store.list_dungeons("u1")[0]["theme"], "sect")
        self.assertEqual(self.store.start_run("u1", "b1", now=LAUNCH)["theme"], "sect")
        # the description only helps when the tags say nothing
        self.store.genre_tags = lambda *_: (["fantasy"], "Expelled from the magic academy, Ted must survive.")
        self.assertEqual(self.store.theme_for("b1", "Saga #1"), "academy")
        self.store.genre_tags = lambda *_: (["post-apocalyptic"], "A starship crashes.")
        self.assertEqual(self.store.theme_for("b1", "Saga #1"), "ruins")
        self.assertEqual(self.store.theme_for("x", "Dungeon Crawler Carl #3"), "dcc")  # series looks beat genre
        self.assertEqual(self.store.theme_for("x", "Ark Royal #4, The Primal Hunter #1"), "primal")
        self.assertEqual(self.store.theme_for("x", "Beware of Chicken #3"), "chicken")
        self.store.genre_tags = lambda *_: 1 / 0  # a broken tag source falls back to the stone dungeon
        self.assertEqual(self.store.theme_for("b1", "Saga #1"), "dungeon")


class OldRunTests(Base):
    def test_run_from_an_older_build_can_resume(self):
        """Runs saved before monsters/supplies/looks were stored get them filled in."""
        self.player(cls="necromancer")
        self.store.sync_dungeons("u1", [("b1", "Book of the Dead 2", "Book of the Dead #2", 12, BEFORE)])
        run = self.store.start_run("u1", "b1", now=LAUNCH)
        with self.store._conn() as c:
            snap = {k: v for k, v in self.store.active_run("u1").items() if k in ("stats", "level", "cls", "look", "enemy_scale", "enemy_tier", "floors", "hours", "title", "series")}
            c.execute("UPDATE game_runs SET snapshot_json=? WHERE id=?", (json.dumps(snap), run["run_id"]))
        resumed = self.store.active_run("u1")
        self.assertTrue(resumed["monsters"]["boss"]["id"])
        self.assertEqual((resumed["supplies"], resumed["theme"]), ({}, "bookdead"))
        self.assertEqual(self.store.active_run("u1")["monsters"]["boss"]["id"], resumed["monsters"]["boss"]["id"])  # saved, stable
        res = self.store.finish_run("u1", run["run_id"], {"outcome": "boss", "kills": 7}, CATALOG, now=LAUNCH + 300)
        self.assertEqual(res["outcome"], "boss")


class BestiaryTests(Base):
    def test_only_met_monsters_are_revealed(self):
        self.player()
        self.store.sync_dungeons("u1", [("b1", "Book", "", 5, BEFORE), ("b2", "B2", "", 5, BEFORE)])
        b = self.store.bestiary("u1")
        self.assertEqual(b["found"], 0)
        self.assertTrue(all(not e["seen"] and "name" not in e for e in b["entries"]))
        run = self.store.start_run("u1", "b1", now=LAUNCH)
        self.store.finish_run("u1", run["run_id"], {"outcome": "exit", "floors": 3, "kills": 2, "elites": 0,
                                                    "feats": {"seen": {"goblin": 2, "rat": 0, "made_up": 5, "unwritten_king": 3}}},
                              CATALOG, now=LAUNCH + 100)
        by = {e["id"]: e for e in self.store.bestiary("u1")["entries"]}
        self.assertEqual((by["goblin"]["seen"], by["goblin"]["defeated"], by["goblin"]["name"]), (True, 2, "Goblin Scavenger"))
        self.assertTrue(by["rat"]["seen"]); self.assertEqual(by["rat"]["defeated"], 0)
        self.assertNotIn("death", by["rat"])            # lore unlocks after a win
        self.assertFalse(by["unwritten_king"]["seen"])  # not in this run's roster, so it doesn't count
        self.assertNotIn("made_up", by)
        # giving up still records what you met
        run = self.store.start_run("u1", "b2", now=LAUNCH + 500)
        self.store.save_progress("u1", run["run_id"], {"floor": 0, "feats": {"seen": {"goblin": 1}}})
        self.store.abandon_run("u1", run["run_id"], now=LAUNCH + 600)
        self.assertEqual({e["id"]: e for e in self.store.bestiary("u1")["entries"]}["goblin"]["defeated"], 3)


def local(y, m, d, h=12):
    import time
    return int(time.mktime((y, m, d, h, 0, 0, 0, 0, -1)))


class BossTests(Base):
    """The December boss: attack windows, the shared bar, winning, and what
    happens when he escapes (scar, the Null in January, a wounded return)."""

    def setUp(self):
        super().setUp()
        self.player("u1")
        self.player("u2", cls="ranger")

    def hit(self, uid, when, damage, outcome="time"):
        a = self.store.start_boss_attack(uid, now=when)
        return self.store.finish_boss_attack(uid, a["attack_id"], {"outcome": outcome, "damage": damage}, CATALOG,
                                             now=when + 120, rng=random.Random(1))

    def boss(self, year=2026):
        with self.store._conn() as c:
            return self.store._boss_row(c, year)

    def test_calendar_windows(self):
        self.assertEqual(R.boss_calendar(local(2026, 12, 1))["slot_name"], "Week 1")
        self.assertEqual(R.boss_calendar(local(2026, 12, 25))["slot"], "2026-xmas")
        self.assertEqual(R.boss_calendar(local(2026, 12, 26))["slot"], R.boss_calendar(local(2026, 12, 21))["slot"])
        self.assertEqual(R.boss_calendar(local(2026, 12, 31))["slot_name"], "Week 5")
        self.assertEqual(R.boss_calendar(local(2027, 1, 3))["phase"], "january")
        self.assertEqual(R.boss_calendar(local(2027, 1, 3))["year"], 2026)
        self.assertEqual(R.boss_calendar(local(2026, 11, 30))["phase"], "before")

    def test_no_attacks_outside_december(self):
        with self.assertRaises(GameError):
            self.store.start_boss_attack("u1", now=local(2026, 11, 30))
        self.assertEqual(self.store.boss_state("u1", now=local(2026, 11, 30))["phase"], "before")

    def test_health_is_sized_from_the_party(self):
        st = self.store.boss_state("u1", now=local(2026, 12, 1))
        self.assertEqual(st["boss"]["hp"], st["boss"]["max_hp"])
        self.assertGreaterEqual(st["boss"]["max_hp"], R.BOSS_MIN_HP)
        self.assertTrue(st["ready"])

    def test_one_attack_per_week_and_rewards(self):
        start = self.boss() or self.store.boss_state("u1", now=local(2026, 12, 2))["boss"]
        before = self.bookmarks()
        r = self.hit("u1", local(2026, 12, 2), 300)
        self.assertEqual(r["damage"], 300)
        self.assertEqual(self.boss()["hp"], start["hp"] - 300)
        self.assertGreater(r["xp"], 0)
        self.assertEqual(self.bookmarks(), before + R.BOSS_ATTACK_BOOKMARKS + R.BADGE_BOOKMARKS)  # + Null Pointer badge
        self.assertIn("boss_hit", {a["key"] for a in self.store.achievements("u1") if a["earned_at"]})
        with self.assertRaises(GameError):
            self.store.start_boss_attack("u1", now=local(2026, 12, 6))
        st = self.store.boss_state("u1", now=local(2026, 12, 6))
        self.assertFalse(st["ready"])
        self.assertEqual(st["next_at"], local(2026, 12, 7, 0))
        self.hit("u1", local(2026, 12, 7), 100)  # week 2

    def test_christmas_never_twice_in_a_day(self):
        self.hit("u1", local(2026, 12, 21), 50)       # weekly, Monday
        self.hit("u1", local(2026, 12, 25), 50)       # Christmas bonus
        for day in (25, 26):
            with self.assertRaises(GameError):
                self.store.start_boss_attack("u1", now=local(2026, 12, day))
        self.hit("u2", local(2026, 12, 25), 50)       # didn't attack Mon-Thu: fights on the 25th...
        with self.assertRaises(GameError):
            self.store.start_boss_attack("u2", now=local(2026, 12, 25, 18))
        self.hit("u2", local(2026, 12, 26), 50)       # ...and still has the weekly attack Sat-Sun

    def test_damage_is_capped(self):
        a = self.store.start_boss_attack("u1", now=local(2026, 12, 2))
        with self.store._conn() as c:
            c.execute("UPDATE game_boss SET hp=10000000, max_hp=10000000")
        r = self.store.finish_boss_attack("u1", a["attack_id"], {"outcome": "time", "damage": 10**9}, CATALOG, now=local(2026, 12, 2) + 60)
        self.assertEqual(r["damage"], R.boss_damage_cap(a["stats"]["atk"]))
        with self.assertRaises(GameError):  # too fast
            b = self.store.start_boss_attack("u2", now=local(2026, 12, 2))
            self.store.finish_boss_attack("u2", b["attack_id"], {"outcome": "time", "damage": 5}, CATALOG, now=local(2026, 12, 2) + 2)

    def test_killing_blow_rewards_everyone_who_fought(self):
        self.hit("u2", local(2026, 12, 2), 100)
        with self.store._conn() as c:
            c.execute("UPDATE game_boss SET hp=50 WHERE year=2026")
        u2_before = self.bookmarks("u2")
        r = self.hit("u1", local(2026, 12, 3), 400, outcome="kill")
        self.assertTrue(r["killed"])
        self.assertEqual(r["damage"], 50)  # only what he had left
        self.assertEqual(len(r["loot"]), 1)
        self.assertGreaterEqual(R.RARITIES.index(r["loot"][0]["rarity"]), R.RARITIES.index(R.BOSS_WIN_RARITY))
        self.assertEqual(self.boss()["status"], "defeated")
        self.assertGreaterEqual(self.bookmarks("u2"), u2_before + R.BOSS_WIN_BOOKMARKS)
        self.assertIn("boss_won", [n["kind"] for n in self.store.take_notices("u2")])
        for uid in ("u1", "u2"):
            self.assertIn("boss_kill", {a["key"] for a in self.store.achievements(uid) if a["earned_at"]})
        with self.assertRaises(GameError):
            self.store.start_boss_attack("u2", now=local(2026, 12, 8))

    def test_top_damage_of_a_finished_week(self):
        self.hit("u1", local(2026, 12, 2), 300)
        self.hit("u2", local(2026, 12, 3), 100)
        self.store.boss_state("u1", now=local(2026, 12, 5))  # week not over yet
        self.assertNotIn("boss_top_week", {a["key"] for a in self.store.achievements("u1") if a["earned_at"]})
        self.store.boss_state("u1", now=local(2026, 12, 8))
        self.assertIn("boss_top_week", {a["key"] for a in self.store.achievements("u1") if a["earned_at"]})
        self.assertNotIn("boss_top_week", {a["key"] for a in self.store.achievements("u2") if a["earned_at"]})

    def test_momentum(self):
        base = self.store.run_config("u1")["stats"]["atk"]
        self.store.sync_dungeons("u1", [(f"b{i}", f"Book {i}", "", 5, local(2026, 11, 1)) for i in range(3)])
        with self.store._conn() as c:
            c.execute("UPDATE game_dungeons SET status='cleared', cleared_at=? WHERE user_id='u1'", (local(2026, 12, 3),))
        a = self.store.start_boss_attack("u1", now=local(2026, 12, 4))
        self.assertAlmostEqual(a["damage_mult"], 1 + 3 * R.BOSS_MOMENTUM, places=3)
        self.assertEqual(a["stats"]["atk"], round(base * a["damage_mult"]))
        self.store.finish_boss_attack("u1", a["attack_id"], {"outcome": "fell", "damage": 10}, CATALOG, now=local(2026, 12, 4) + 60)
        self.assertEqual(self.store.boss_state("u1", now=local(2026, 12, 8))["momentum"]["clears"], 0)  # used up

    def test_party_banners(self):
        base = self.store.run_config("u2")["stats"]
        with self.assertRaises(GameError):
            self.store.raise_banner("u1", "war", now=local(2026, 11, 20))  # December only
        self.store.raise_banner("u1", "war", now=local(2026, 12, 2))
        self.assertEqual(self.bookmarks(), R.WELCOME_CHEST - R.BANNERS["war"]["cost"])
        with self.assertRaises(GameError):
            self.store.raise_banner("u1", "mending", now=local(2026, 12, 2))  # one banner per player per week
        with self.assertRaises(GameError):
            self.store.raise_banner("u2", "war", now=local(2026, 12, 2))  # each banner once per week
        self.store.raise_banner("u2", "bulwark", now=local(2026, 12, 3))
        a = self.store.start_boss_attack("u2", now=local(2026, 12, 4))  # u2 benefits from u1's banner too
        self.assertEqual(sorted(a["banners"]), ["bulwark", "war"])
        self.assertEqual(a["stats"]["atk"], round(base["atk"] * 1.15))
        self.assertEqual(a["stats"]["def"], round(base["def"] * 1.25))
        st = self.store.boss_state("u1", now=local(2026, 12, 4))
        self.assertEqual({b["key"]: b["raised_by"] for b in st["banners"]}["war"], "u1")
        self.assertTrue(st["raised_one"])
        nxt = self.store.start_boss_attack("u1", now=local(2026, 12, 8))  # new week: banners are down
        self.assertEqual(nxt["banners"], [])
        with self.store._conn() as c:
            c.execute("UPDATE game_players SET bookmarks=100 WHERE user_id='u1'")
        self.store.raise_banner("u1", "resolve", now=local(2026, 12, 8))  # and can be raised again

    def test_health_counts_the_whole_party(self):
        solo = R.boss_max_hp([1000])
        self.assertEqual(solo, max(R.BOSS_MIN_HP, int(1000 * R.BOSS_MIN_PARTY * R.BOSS_SLOTS * R.BOSS_HP_SHARE)))
        self.assertEqual(R.boss_max_hp([1000, 3000], 6), int(2000 * 6 * R.BOSS_SLOTS * R.BOSS_HP_SHARE))

    def test_he_escapes_scars_the_party_and_the_null_spreads(self):
        self.hit("u1", local(2026, 12, 2), 100)
        mx = self.boss()["max_hp"]
        with self.store._conn() as c:
            c.execute("UPDATE game_boss SET hp=? WHERE year=2026", (round(mx * 0.12),))
        st = self.store.boss_state("u1", now=local(2027, 1, 2))
        self.assertEqual(self.boss()["status"], "escaped")
        scar = next(a for a in self.store.achievements("u1") if a["key"] == "boss_scar")
        self.assertTrue(scar["earned_at"])
        self.assertIn("2026 (Regent at 12%)", scar["text"])
        self.assertFalse(next(a for a in self.store.achievements("u2") if a["key"] == "boss_scar")["earned_at"])  # didn't fight
        self.assertIn("boss_escaped", [n["kind"] for n in self.store.take_notices("u1")])
        self.assertTrue(st["null"]["active"])
        self.assertEqual(st["null"]["target"], 2 * R.NULL_CLEANSE_PER_PLAYER)
        # January dungeons are harder while the Null spreads
        self.store.sync_dungeons("u1", [("jan1", "January Book", "", 5, local(2027, 1, 2))])
        normal = self.store.run_config("u1")["enemy_scale"]
        run = self.store.start_run("u1", "jan1", now=local(2027, 1, 3) - self.store.boss_offset)
        self.assertTrue(run["null"])
        self.assertAlmostEqual(run["enemy_scale"]["hp"], round(normal["hp"] * R.NULL_BUFF, 3))
        # finishing books cleanses it
        self.store.sync_dungeons("u2", [(f"j{i}", f"J{i}", "", 5, local(2027, 1, 4)) for i in range(3)])
        st = self.store.boss_state("u1", now=local(2027, 1, 5))
        self.assertFalse(st["null"]["active"])
        self.assertIsNone(self.store.boss_state("u1", now=local(2027, 2, 2))["null"])

    def test_he_comes_back_wounded_next_december(self):
        self.hit("u1", local(2026, 12, 2), 100)
        with self.store._conn() as c:
            c.execute("UPDATE game_boss SET hp=max_hp*12/100 WHERE year=2026")
        self.store.boss_state("u1", now=local(2027, 1, 2))
        st = self.store.boss_state("u1", now=local(2027, 12, 1))
        self.assertEqual(st["boss"]["returning_pct"], 12)
        self.assertAlmostEqual(st["boss"]["hp"] / st["boss"]["max_hp"], 0.12 + R.BOSS_REGEN, places=2)
        self.assertEqual(self.store.boss_state("u1", now=local(2027, 6, 1))["last"]["status"], "escaped")

    def test_simulated_attack_is_sane(self):
        for cls in R.CLASS_STATS:
            st = R.player_stats(cls, 10, [], {})
            e = R.expected_attack(st, cls, 10)
            self.assertGreater(e, st["atk"] * 4)
            self.assertLess(e, R.boss_damage_cap(st["atk"]))


class MonsterImportTests(Base):
    """Bulk monster import (docs/MONSTER_PROMPT.md) and series monsters."""

    def mon(self, name, series="Dungeon Crawler Carl #1", role="regular", **kw):
        return {"name": name, "series": series, "tier": 2, "role": role, "style": "glass",
                "moves": ["attack", "poison", "weaken", "shield"], "move_names": {"poison": "Toxic Glitter", "attack": "Slap"},
                "barks": ["Ooh, a customer!"], "appear": "It arrives.", "death": "It leaves.",
                "art": {"body": "serpent", "head": "beak", "eyes": "many", "horns": "none", "teeth": "fangs", "item": "trident",
                        "extra": "wings", "color": "#AA3366", "accent": "#223344", "size": 1.1}, **kw}

    def test_import_checks_each_monster_and_turns_them_on(self):
        res = self.store.import_monsters([self.mon("Glitter Wraith"), {"name": "Bad", "tier": 9}])
        self.assertEqual([r["ok"] for r in res], [True, False])
        m = next(m for m in self.store.custom_monsters(enabled_only=True) if m["id"] == "glitter_wraith")
        self.assertEqual(m["move_names"], {"poison": "Toxic Glitter", "attack": "Slap"})
        self.assertEqual(m["art"]["extra"], "wings")
        self.assertEqual(m["series"], "Dungeon Crawler Carl #1")

    def test_cut_off_series_names_are_completed_or_refused(self):
        self.store.library_series = ["Last Save Dave", "Ascend Online", "Ascend Online [chronological order]", "Me, My Son, & the Apocalypse",
                                     "The Legend of William Oh", "The Legend of Randidly Ghosthound"]
        res = self.store.import_monsters([self.mon("Save Point Gremlin", series="Last Save Da"), self.mon("Guild Grinder", series="Ascend Onli"),
                                          self.mon("Playground Tyrant", series="Me, My Son, and"), self.mon("Temple Brute", series="The Legend o"),
                                          self.mon("Nowhere Beast", series="Heart of Dorl")])
        self.assertEqual([r["ok"] for r in res], [True, True, True, False, False])
        self.assertEqual([r["series"] for r in res[:3]], ["Last Save Dave", "Ascend Online", "Me, My Son, & the Apocalypse"])
        self.store.library_series = []  # earlier imports with cut names can be repaired later
        self.store.import_monsters([self.mon("Old Import", series="Last Save Da")])
        self.store.library_series = ["Last Save Dave"]
        fix = self.store.repair_monster_series()
        self.assertEqual([f["to"] for f in fix["fixed"]], ["Last Save Dave"])

    def test_same_name_other_series_gets_its_own_id(self):
        self.store.import_monsters([self.mon("Shade", series="Cradle")])
        self.store.import_monsters([self.mon("Shade", series="He Who Fights with Monsters")])
        self.store.import_monsters([self.mon("Shade", series="Cradle", style="brute")])  # same series: replaces
        ids = sorted(m["id"] for m in self.store.custom_monsters())
        self.assertEqual(len(ids), 2)

    def test_series_monsters_only_in_their_series(self):
        self.store.import_monsters([self.mon("Glitter Wraith", series="Dungeon Crawler Carl"),
                                    self.mon("Carl Boss", series="Dungeon Crawler Carl", role="boss")])
        from app import game_monsters as M
        custom = self.store.custom_monsters(enabled_only=True)
        dcc = M.roster(1, custom, series="Dungeon Crawler Carl #3")
        self.assertIn("glitter_wraith", [m["id"] for m in dcc["regular"]])
        self.assertEqual(dcc["boss"]["id"], "carl_boss")
        other = M.roster(2, custom, series="Cradle #1")
        self.assertNotIn("glitter_wraith", [m["id"] for m in other["regular"]])
        self.assertNotEqual(other["boss"]["id"], "carl_boss")

    def test_player_built_monster_waits_for_approval(self):
        self.player("u1")
        self.store.library_series = ["Dungeon Crawler Carl"]
        sub = self.store.submit_monster("u1", self.mon("Glitter Golem", series="Dungeon Crawler Carl"))
        self.assertEqual(sub["status"], "new")
        self.assertEqual(self.store.custom_monsters(), [])   # nothing in the game yet
        mine = self.store.suggestions("u1")[0]
        self.assertEqual(mine["monster"]["name"], "Glitter Golem")
        with self.assertRaises(GameError):
            self.store.submit_monster("u1", self.mon("Nowhere Beast", series="Heart of Dorl"))  # not in the library
        m = self.store.approve_submission(sub["id"])
        live = self.store.custom_monsters(enabled_only=True)
        self.assertEqual([x["id"] for x in live], [m["id"]])
        self.assertEqual(self.store.suggestions("u1")[0]["status"], "live")
        self.assertIn("monster_live", [n["kind"] for n in self.store.take_notices("u1")])
        self.assertIn("monster_live", {a["key"] for a in self.store.achievements("u1") if a["earned_at"]})

    def test_suggested_monster_coming_alive_earns_a_badge(self):
        self.player("u1")
        sug = self.store.suggest_monster("u1", "Sock Goblin", "Steals one sock from every pair.", 1)
        self.store.save_custom_monster({**self.mon("Sock Goblin", series=""), "tier": 1}, suggestion_id=sug["id"])
        self.store.set_monster_enabled("sock_goblin", True)
        self.assertIn("monster_live", {a["key"] for a in self.store.achievements("u1") if a["earned_at"]})


def tier_query(**tiers):
    """A saved tier list like the Tier List page makes: base64 cover names."""
    import base64
    enc = lambda n: base64.b64encode((n.replace(" ", "_") + ".jpg").encode()).decode().rstrip("=")
    return "&".join(f"{t}={','.join(enc(n) for n in names)}" for t, names in tiers.items())


class TierRewardTests(Base):
    def setUp(self):
        super().setUp()
        self.player("u1")
        books = [("a1", "Old 1", "Old Series #1", 5, BEFORE), ("a2", "Old 2", "Old Series #2", 5, BEFORE),
                 ("b1", "New 1", "New Series #1", 5, AFTER), ("c1", "Other", "Other Saga #1", 5, BEFORE)]
        self.store.sync_dungeons("u1", books)
        self.store.take_notices("u1")

    def test_pays_fresh_and_backlog_once_and_lists_what_is_left(self):
        before = self.bookmarks()
        r = self.store.settle_tier_rewards("u1", tier_query(S=["New Series"], A=["Old Series"]), now=AFTER + 10)
        self.assertEqual(r["paid"], R.TIER_FRESH_BOOKMARKS + R.TIER_BACKLOG_BOOKMARKS)
        self.assertEqual(r["to_rank"], ["Other Saga"])
        self.assertEqual(self.bookmarks(), before + r["paid"])
        self.assertIn("tier_reward", [n["kind"] for n in self.store.take_notices("u1")])
        again = self.store.settle_tier_rewards("u1", tier_query(S=["New Series"], A=["Old Series"]), now=AFTER + 20)
        self.assertEqual(again["paid"], 0)  # each series pays once

    def test_rerank_pays_only_after_a_new_book(self):
        q = tier_query(S=["New Series"])
        self.store.settle_tier_rewards("u1", q, now=AFTER + 10)
        self.assertEqual(self.store.settle_tier_rewards("u1", tier_query(A=["New Series"]), now=AFTER + 20)["paid"], 0)
        self.store.sync_dungeons("u1", [("b2", "New 2", "New Series #2", 5, AFTER + 500)])
        r = self.store.settle_tier_rewards("u1", tier_query(A=["New Series"]), now=AFTER + 600)
        self.assertEqual(r["rerank"], [])     # keeping its rank is fine: no reminder
        self.assertEqual(sorted(r["to_rank"]), ["Old Series", "Other Saga"])
        self.assertEqual(r["paid"], 0)        # same tier: nothing
        r = self.store.settle_tier_rewards("u1", tier_query(S=["New Series"]), now=AFTER + 700)
        self.assertEqual(r["paid"], R.TIER_RERANK_BOOKMARKS)

    def test_a_book_cover_ranks_its_series(self):
        # Book 1 lacked its series in ABS, so it got its own cover and was ranked by that.
        self.store.sync_dungeons("u1", [("w2", "The City of Akul", "The Legend of William Oh #2", 12, AFTER)])
        r = self.store.settle_tier_rewards("u1", tier_query(A=["The Legend of William Oh (Unabridged)", "Old Series Year One"]), now=AFTER + 10)
        self.assertNotIn("The Legend of William Oh", r["to_rank"])
        self.assertNotIn("Old Series", r["to_rank"])

    def test_backlog_is_capped(self):
        self.store.sync_dungeons("u1", [(f"x{i}", f"X{i}", f"Saga {i} #1", 5, BEFORE) for i in range(R.TIER_BACKLOG_CAP + 20)])
        names = [f"Saga {i}" for i in range(R.TIER_BACKLOG_CAP + 20)]
        r = self.store.settle_tier_rewards("u1", tier_query(B=names), now=AFTER)
        self.assertEqual(r["paid"], R.TIER_BACKLOG_CAP)
        self.assertIn("tier_50", {a["key"] for a in self.store.achievements("u1") if a["earned_at"]})

    def test_up_to_date_badge(self):
        self.store.settle_tier_rewards("u1", tier_query(S=["New Series", "Old Series", "Other Saga"]), now=AFTER)
        self.assertIn("tier_current", {a["key"] for a in self.store.achievements("u1") if a["earned_at"]})


class RulesTests(unittest.TestCase):
    def test_bindery_is_a_long_climb(self):
        total = sum(R.bindery_cost(r, k) for k in R.BINDERY for r in range(1, R.bindery_max(k) + 1))
        self.assertEqual(total, 6 * sum(R.FORGE_RANK_PRICE * r for r in range(1, 11)) + 1650)  # 3,960 + Battle Ready

    def test_battle_ready_stops_one_short_of_a_full_bar(self):
        self.assertEqual(R.player_stats("brawler", 50, [], {})["start_energy"], 0)
        self.assertEqual(R.player_stats("brawler", 50, [], {"battle_ready": 2})["start_energy"], 2)
        self.assertEqual(R.player_stats("brawler", 50, [], {"battle_ready": 4})["start_energy"], 2)
        self.assertEqual(R.player_stats("runeblade", 50, [], {"battle_ready": 4})["start_energy"], 4)
        self.assertEqual(R.player_stats("necromancer", 50, [], {"battle_ready": 4})["start_energy"], 3)
        # ranks only work once your level unlocks them
        self.assertEqual(R.player_stats("runeblade", 1, [], {"battle_ready": 4})["start_energy"], 0)
        self.assertEqual(R.player_stats("runeblade", 16, [], {"battle_ready": 4})["start_energy"], 2)

    def test_legendary_only_as_an_epic_upgrade(self):
        for boss in (False, True):
            for h in (3, 15, 25):
                self.assertNotIn("Legendary", R.rarity_table(boss, h, 5))
        rng = random.Random(7)
        ups = [R.upgrade_rarity("Epic", rng) for _ in range(4000)]
        self.assertAlmostEqual(ups.count("Legendary") / 4000, R.LEGENDARY_CHANCE, delta=0.02)
        self.assertEqual({R.upgrade_rarity("Rare", rng) for _ in range(200)}, {"Rare"})

    def test_monsters_grow_with_gear(self):
        bare = R.player_stats("brawler", 5, [], {})
        self.assertEqual(R.power_factors("brawler", 5, bare), {"hp": 1.0, "atk": 1.0})
        geared = {**bare, "atk": bare["atk"] * 2, "hp": bare["hp"] * 1.5}
        f = R.power_factors("brawler", 5, geared)
        self.assertAlmostEqual(f["hp"], 1 + R.POWER_SCALE * 1, places=2)     # double attack -> tougher monsters
        self.assertAlmostEqual(f["atk"], 1 + R.POWER_SCALE_ATK * 1, places=2)  # and harder hits
        tank = {**bare, "hp": bare["hp"] * 3, "def": bare["def"] * 3}
        self.assertEqual(R.power_factors("brawler", 5, tank), {"hp": 1.0, "atk": 1.0})  # health and defense don't scale them
        s = R.with_power(R.enemy_scale(5), f)
        self.assertGreater(s["hp"], R.enemy_scale(5)["hp"])

    def test_stats_include_gear_and_upgrades(self):
        base = R.player_stats("brawler", 1, [], {})
        more = R.player_stats("brawler", 1, [item("Weapon")], {"thick_skin": 2, "whetstone": 3, "field_medic": 5})
        self.assertEqual(more["hp"] - base["hp"], item("Weapon")["hp"] + 10)
        self.assertEqual(more["atk"] - base["atk"], item("Weapon")["atk"] + 3)
        self.assertEqual(more["potions"], base["potions"] + 1)

    def test_long_books_improve_loot_odds(self):
        short, long_ = R.rarity_table(False, 3, 0), R.rarity_table(False, 15, 0)
        self.assertGreater(long_["Rare"], short["Rare"])
        self.assertNotIn("Common", R.rarity_table(False, 22, 0))

    def test_xp_curve(self):
        self.assertEqual([R.xp_to_next(n) for n in (1, 2, 3)], [50, 120, 210])


class MonsterTests(unittest.TestCase):
    def test_every_monster_is_valid(self):
        from app import game_monsters as M
        ids = set()
        for m in M.MONSTERS:
            self.assertNotIn(m["id"], ids); ids.add(m["id"])
            self.assertIn(m["role"], M.ROLE_BASE)
            self.assertIn(m.get("style", "balanced"), M.STYLES)
            self.assertTrue(m["moves"] and all(mv in M.MOVES for mv in m["moves"]), m["id"])
            self.assertTrue("svg" in m or "art" in m, m["id"])
            for part, value in m.get("art", {}).items():
                if part in M.PARTS:
                    self.assertIn(value, M.PARTS[part], f"{m['id']} {part}")

    def test_rosters_by_tier_with_fallback(self):
        from app import game_monsters as M
        t1, t2, t5 = M.roster(1), M.roster(2), M.roster(5)
        self.assertEqual((t1["tier"], t1["boss"]["id"]), (1, "warden"))
        self.assertEqual((t2["tier"], t2["boss"]["id"]), (2, "ossuary_king"))
        self.assertEqual((t5["tier"], t5["boss"]["id"]), (5, "unwritten_king"))
        for t in M.TIERS:
            r = M.roster(t)
            self.assertEqual(r["tier"], t)
            self.assertTrue(len(r["regular"]) >= 3 and r["elite"] and r["boss"], t)
        self.assertFalse(t1["always_modded"]); self.assertTrue(t2["always_modded"])

    def test_styles_change_stats_not_xp(self):
        from app import game_monsters as M
        brute = M.stats_for({"role": "regular", "style": "brute"})
        glass = M.stats_for({"role": "regular", "style": "glass"})
        self.assertGreater(brute["hp"], glass["hp"]); self.assertLess(brute["atk"], glass["atk"])
        self.assertEqual(brute["xp"], glass["xp"])

    def test_level_picks_tier(self):
        self.assertEqual([R.enemy_tier(lv) for lv in (1, 9, 10, 19, 20)], [1, 1, 2, 2, 3])


NEW_MONSTER = {"name": "Paper Golem", "tier": 3, "role": "elite", "style": "tank", "moves": ["attack", "heavy"],
               "art": {"body": "construct", "head": "round", "eyes": "one", "color": "#c6a06f", "accent": "#22305A", "size": 3},
               "appear": "  It rustles.  ", "death": "It tears."}


class WorkshopTests(Base):
    def test_clean_monster_validates_everything(self):
        from app import game_monsters as M
        m = M.clean_monster(NEW_MONSTER)
        self.assertEqual((m["id"], m["art"]["color"], m["art"]["size"], m["art"]["horns"], m["appear"]), ("paper_golem", "#C6A06F", 1.4, "none", "It rustles."))
        bad = [{"name": "x"}, {**NEW_MONSTER, "tier": 9}, {**NEW_MONSTER, "role": "king"}, {**NEW_MONSTER, "moves": ["attack"]},
               {**NEW_MONSTER, "moves": ["attack", "fly"]}, {**NEW_MONSTER, "art": {**NEW_MONSTER["art"], "body": "dragon"}},
               {**NEW_MONSTER, "art": {**NEW_MONSTER["art"], "color": "red"}}, {**NEW_MONSTER, "name": "Goblin"}, {**NEW_MONSTER, "name": "<b>Bad</b>"}]
        for b in bad:
            with self.assertRaises(ValueError, msg=b):
                M.clean_monster(b)

    def test_custom_monster_joins_roster_only_when_enabled(self):
        self.player()
        with self.store._conn() as c:
            c.execute("UPDATE game_players SET level=25 WHERE user_id='u1'")
        self.store.save_custom_monster(NEW_MONSTER)
        ids = lambda: [m["id"] for m in self.store.run_config("u1")["monsters"]["elite"]]
        self.assertNotIn("paper_golem", ids())
        self.store.set_monster_enabled("paper_golem", True)
        self.assertIn("paper_golem", ids())
        with self.assertRaises(GameError):  # same name again without editing
            self.store.save_custom_monster(NEW_MONSTER)
        self.store.save_custom_monster({**NEW_MONSTER, "id": "paper_golem", "name": "Paper Golem Mk II"})
        self.assertEqual(self.store.custom_monsters()[0]["name"], "Paper Golem Mk II")
        self.store.delete_custom_monster("paper_golem")
        self.assertEqual(self.store.custom_monsters(), [])

    def test_suggestion_goes_live_with_notice_and_feed(self):
        self.player()
        sug = self.store.suggest_monster("u1", "Paper Golem", "A golem made of overdue library slips.", 3)
        for n in range(2):
            self.store.suggest_monster("u1", f"Idea {n}", "Another fine idea for a monster.")
        with self.assertRaises(GameError):  # three open ideas at most
            self.store.suggest_monster("u1", "One more", "Surely one more is fine.")
        self.store.save_custom_monster(NEW_MONSTER, suggestion_id=sug["id"])
        self.assertEqual(self.store.suggestions("u1")[-1]["status"], "building")
        self.store.set_monster_enabled("paper_golem", True)
        self.store.set_monster_enabled("paper_golem", False)
        self.store.set_monster_enabled("paper_golem", True)  # announced once
        notes = [n for n in self.store.take_notices("u1") if n["kind"] == "monster_live"]
        self.assertEqual(len(notes), 1)
        self.assertEqual(sum(1 for f in self.store.list_feed() if f["kind"] == "monster"), 1)
        self.assertEqual(self.store.suggestions("u1")[-1]["status"], "live")


class CosmeticTests(Base):
    def test_buy_wear_and_show_everywhere(self):
        self.player(cls="beastmaster")
        self.store.buy_cosmetic("u1", "cape", "stars")
        self.assertEqual(self.bookmarks(), R.WELCOME_CHEST - 10)
        p = self.store.get_player("u1")
        self.assertEqual((p["worn"], p["look"]["cape"]), ({"cape": "stars"}, "stars"))
        self.assertEqual(self.store.party()[0]["look"]["cape"], "stars")
        with self.assertRaises(GameError):
            self.store.buy_cosmetic("u1", "cape", "stars")
        self.store.wear_cosmetic("u1", "cape", None)
        self.assertNotIn("cape", self.store.get_player("u1")["look"])
        with self.assertRaises(GameError):
            self.store.wear_cosmetic("u1", "title", "legend")  # not owned
        with self.assertRaises(ValueError):
            self.store.buy_cosmetic("u1", "hat", "top")
        self.store.set_look("u1", {**LOOK, "cape": "stars"})  # a dressed look saves as the same look, free
        self.assertEqual(self.bookmarks(), R.WELCOME_CHEST - 10)

    def test_pet_skin_only_for_its_class(self):
        self.player(cls="beastmaster")
        self.store.buy_cosmetic("u1", "pet", "frost")
        self.assertEqual(self.store.run_config("u1")["pet_skin"], "frost")
        with self.store._conn() as c:
            c.execute("UPDATE game_players SET cls='necromancer' WHERE user_id='u1'")
        self.assertIsNone(self.store.run_config("u1")["pet_skin"])

    def test_not_enough_bookmarks(self):
        self.player()
        with self.store._conn() as c:
            c.execute("UPDATE game_players SET bookmarks=3 WHERE user_id='u1'")
        with self.assertRaises(GameError):
            self.store.buy_cosmetic("u1", "title", "legend")
        self.assertEqual(self.store.wardrobe("u1")["worn"], {})


class GameAuthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        game_auth.init(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_token_round_trip_and_tampering(self):
        token = game_auth.make_token("abc-123")
        self.assertEqual(game_auth.user_from_token(token), "abc-123")
        user, expiry, sig = token.split(".")
        self.assertIsNone(game_auth.user_from_token(f"someone-else.{expiry}.{sig}"))
        self.assertIsNone(game_auth.user_from_token(f"{user}.{int(expiry) + 999}.{sig}"))
        self.assertIsNone(game_auth.user_from_token(token, now=int(expiry) + 1))
        self.assertIsNone(game_auth.user_from_token("garbage"))

    def test_secret_survives_restart(self):
        token = game_auth.make_token("abc-123")
        game_auth.init(self.tmp.name)
        self.assertEqual(game_auth.user_from_token(token), "abc-123")

    def test_pin_rules_and_lockout(self):
        self.assertTrue(game_auth.valid_pin("0427"))
        for bad in ("123", "12345", "12a4", "", None):
            self.assertFalse(game_auth.valid_pin(bad))
        for _ in range(4):
            game_auth.record_failure("u9")
        self.assertEqual(game_auth.lockout_remaining("u9"), 0)
        game_auth.record_failure("u9")
        self.assertGreater(game_auth.lockout_remaining("u9"), 0)
        game_auth.record_success("u9")
        self.assertEqual(game_auth.lockout_remaining("u9"), 0)


if __name__ == "__main__":
    unittest.main()
