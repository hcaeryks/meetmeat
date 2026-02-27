from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from app import db
from app.main import app


class ApiReliabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        db.DATABASE_PATH = os.path.join(self._tmp.name, "test.db")
        db.init_db()
        self._client_ctx = TestClient(app)
        self.client = self._client_ctx.__enter__()

    def tearDown(self) -> None:
        self._client_ctx.__exit__(None, None, None)
        self._tmp.cleanup()

    def _create_plan(self, mode: str, config: dict, slot_minutes: int = 15) -> str:
        res = self.client.post(
            "/api/plans",
            json={
                "title": f"{mode} plan",
                "mode": mode,
                "anchor_timezone": "America/New_York",
                "slot_minutes": slot_minutes,
                "require_password": False,
                "config": config,
            },
        )
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()["plan_id"]

    def _join(self, plan_id: str, name: str) -> str:
        res = self.client.post(
            f"/api/plans/{plan_id}/participants",
            json={"display_name": name, "timezone": "America/New_York"},
        )
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()["participant_id"]

    def _save(self, plan_id: str, participant_id: str, availability: dict) -> dict:
        res = self.client.put(
            f"/api/plans/{plan_id}/submissions/{participant_id}",
            json={"availability": availability},
        )
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()

    def _get_submission(self, plan_id: str, participant_id: str) -> dict:
        res = self.client.get(f"/api/plans/{plan_id}/submissions/{participant_id}")
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()

    def test_submission_roundtrip_all_modes(self) -> None:
        cases = [
            (
                "WEEKLY_GRID",
                {"scope": "ANY_WEEK", "slot_minutes": 15},
                {
                    "type": "WEEKLY_GRID",
                    "scope": "ANY_WEEK",
                    "anchor_timezone": "America/New_York",
                    "weekly": [{"dow": 1, "start": "09:00", "end": "10:00", "value": "IDEAL"}],
                },
            ),
            (
                "WEEKLY_GRID",
                {"scope": "SPECIFIC_WEEK", "week_start_local_date": "2026-03-01", "slot_minutes": 15},
                {
                    "type": "WEEKLY_GRID",
                    "scope": "SPECIFIC_WEEK",
                    "intervals_utc": [["2026-03-02T14:00:00.000Z", "2026-03-02T15:00:00.000Z", "OK"]],
                },
            ),
            (
                "DATES_ONLY",
                {"date_start_local": "2026-03-01", "date_end_local": "2026-03-31"},
                {
                    "type": "DATES_ONLY",
                    "anchor_timezone": "America/New_York",
                    "dates": [{"date": "2026-03-02", "value": "IDEAL"}],
                },
            ),
            (
                "DATE_TIME_WINDOWS",
                {"date_start_local": "2026-03-01", "date_end_local": "2026-03-03", "slot_minutes": 15},
                {
                    "type": "DATE_TIME_WINDOWS",
                    "intervals_utc": [["2026-03-02T14:00:00.000Z", "2026-03-02T15:00:00.000Z", "IDEAL"]],
                },
            ),
            (
                "OPTIONS_POLL",
                {
                    "options": [
                        {
                            "option_id": "o1",
                            "start_utc": "2026-03-02T14:00:00.000Z",
                            "duration_minutes": 60,
                        }
                    ]
                },
                {"type": "OPTIONS_POLL", "votes": [{"option_id": "o1", "value": "OK"}]},
            ),
            (
                "DURATION_FINDER",
                {
                    "date_start_local": "2026-03-01",
                    "date_end_local": "2026-03-03",
                    "slot_minutes": 15,
                    "duration_minutes": 60,
                    "min_attendees": 1,
                },
                {
                    "type": "DATE_TIME_WINDOWS",
                    "intervals_utc": [["2026-03-02T14:00:00.000Z", "2026-03-02T15:00:00.000Z", "IDEAL"]],
                },
            ),
        ]

        for mode, config, availability in cases:
            with self.subTest(mode=mode, config=config):
                plan_id = self._create_plan(mode, config)
                participant_id = self._join(plan_id, "alice")
                saved = self._save(plan_id, participant_id, availability)
                self.assertIn("updated_at_utc", saved)
                fetched = self._get_submission(plan_id, participant_id)
                self.assertEqual(fetched["participant_id"], participant_id)
                self.assertTrue(fetched["updated_at_utc"])
                self.assertEqual(fetched["availability"]["type"], availability["type"])

    def test_invalid_payload_422_and_no_mutation(self) -> None:
        plan_id = self._create_plan("WEEKLY_GRID", {"scope": "ANY_WEEK", "slot_minutes": 15})
        participant_id = self._join(plan_id, "alice")

        invalid = {
            "type": "WEEKLY_GRID",
            "scope": "ANY_WEEK",
            "anchor_timezone": "America/New_York",
            "weekly": [{"dow": 9, "start": "09:00", "end": "10:00", "value": "IDEAL"}],
        }
        res = self.client.put(
            f"/api/plans/{plan_id}/submissions/{participant_id}",
            json={"availability": invalid},
        )
        self.assertEqual(res.status_code, 422, res.text)

        fetched = self._get_submission(plan_id, participant_id)
        self.assertEqual(fetched["availability"], {})
        self.assertIsNone(fetched["updated_at_utc"])

    def test_participant_plan_mismatch_returns_404(self) -> None:
        plan_a = self._create_plan("DATES_ONLY", {"date_start_local": "2026-03-01", "date_end_local": "2026-03-03"})
        plan_b = self._create_plan("DATES_ONLY", {"date_start_local": "2026-03-01", "date_end_local": "2026-03-03"})
        participant_id = self._join(plan_a, "alice")

        res = self.client.put(
            f"/api/plans/{plan_b}/submissions/{participant_id}",
            json={"availability": {"type": "DATES_ONLY", "anchor_timezone": "America/New_York", "dates": []}},
        )
        self.assertEqual(res.status_code, 404, res.text)

    def test_aggregate_participant_maps_present(self) -> None:
        weekly_plan = self._create_plan("WEEKLY_GRID", {"scope": "ANY_WEEK", "slot_minutes": 15})
        alice = self._join(weekly_plan, "alice")
        bob = self._join(weekly_plan, "bob")
        self._save(
            weekly_plan,
            alice,
            {
                "type": "WEEKLY_GRID",
                "scope": "ANY_WEEK",
                "anchor_timezone": "America/New_York",
                "weekly": [{"dow": 1, "start": "09:00", "end": "10:00", "value": "IDEAL"}],
            },
        )
        self._save(
            weekly_plan,
            bob,
            {
                "type": "WEEKLY_GRID",
                "scope": "ANY_WEEK",
                "anchor_timezone": "America/New_York",
                "weekly": [{"dow": 1, "start": "09:00", "end": "10:00", "value": "OK"}],
            },
        )
        agg = self.client.get(f"/api/plans/{weekly_plan}/aggregate").json()["data"]
        self.assertIn("slot_participants", agg)
        self.assertTrue(any("alice" in v["IDEAL"] or "alice" in v["OK"] for v in agg["slot_participants"].values()))

        dates_plan = self._create_plan("DATES_ONLY", {"date_start_local": "2026-03-01", "date_end_local": "2026-03-03"})
        d_alice = self._join(dates_plan, "alice")
        self._save(
            dates_plan,
            d_alice,
            {"type": "DATES_ONLY", "anchor_timezone": "America/New_York", "dates": [{"date": "2026-03-02", "value": "IDEAL"}]},
        )
        dates_agg = self.client.get(f"/api/plans/{dates_plan}/aggregate").json()["data"]
        self.assertIn("date_participants", dates_agg)
        self.assertIn("2026-03-02", dates_agg["date_participants"])

        options_plan = self._create_plan(
            "OPTIONS_POLL",
            {"options": [{"option_id": "o1", "start_utc": "2026-03-02T14:00:00.000Z", "duration_minutes": 60}]},
        )
        o_alice = self._join(options_plan, "alice")
        self._save(options_plan, o_alice, {"type": "OPTIONS_POLL", "votes": [{"option_id": "o1", "value": "IDEAL"}]})
        options_agg = self.client.get(f"/api/plans/{options_plan}/aggregate").json()["data"]
        self.assertIn("option_participants", options_agg)
        self.assertIn("o1", options_agg["option_participants"])

    def test_aggregate_expands_brushed_ranges_into_slots(self) -> None:
        weekly_plan = self._create_plan("WEEKLY_GRID", {"scope": "ANY_WEEK", "slot_minutes": 15})
        weekly_pid = self._join(weekly_plan, "alice")
        self._save(
            weekly_plan,
            weekly_pid,
            {
                "type": "WEEKLY_GRID",
                "scope": "ANY_WEEK",
                "anchor_timezone": "America/New_York",
                "weekly": [{"dow": 1, "start": "09:00", "end": "10:00", "value": "IDEAL"}],
            },
        )
        weekly_agg = self.client.get(f"/api/plans/{weekly_plan}/aggregate").json()["data"]
        self.assertIn("1|09:00|09:15", weekly_agg["slot_counts"])
        self.assertIn("1|09:15|09:30", weekly_agg["slot_counts"])
        self.assertIn("alice", weekly_agg["slot_participants"]["1|09:00|09:15"]["IDEAL"])

        dt_plan = self._create_plan(
            "DATE_TIME_WINDOWS",
            {"date_start_local": "2026-03-01", "date_end_local": "2026-03-03", "slot_minutes": 15},
        )
        dt_pid = self._join(dt_plan, "alice")
        self._save(
            dt_plan,
            dt_pid,
            {
                "type": "DATE_TIME_WINDOWS",
                "intervals_utc": [["2026-03-02T14:00:00.000Z", "2026-03-02T15:00:00.000Z", "IDEAL"]],
            },
        )
        dt_agg = self.client.get(f"/api/plans/{dt_plan}/aggregate").json()["data"]
        self.assertIn(
            "2026-03-02T14:00:00.000Z|2026-03-02T14:15:00.000Z",
            dt_agg["slot_counts"],
        )
        self.assertIn(
            "alice",
            dt_agg["slot_participants"]["2026-03-02T14:00:00.000Z|2026-03-02T14:15:00.000Z"]["IDEAL"],
        )

    def test_ai_export_is_human_readable_per_participant(self) -> None:
        plan_id = self._create_plan("WEEKLY_GRID", {"scope": "ANY_WEEK", "slot_minutes": 15})
        participant_id = self._join(plan_id, "Skyreach")
        self._save(
            plan_id,
            participant_id,
            {
                "type": "WEEKLY_GRID",
                "scope": "ANY_WEEK",
                "anchor_timezone": "America/New_York",
                "weekly": [
                    {"dow": 1, "start": "13:00", "end": "14:00", "value": "IDEAL"},
                    {"dow": 1, "start": "15:00", "end": "16:00", "value": "OK"},
                ],
            },
        )

        res = self.client.get(f"/api/plans/{plan_id}/export?format=ai")
        self.assertEqual(res.status_code, 200, res.text)
        text = res.json()["text"]
        self.assertIn("Participant availability:", text)
        self.assertIn("Skyreach is ideally available for", text)
        self.assertIn("Skyreach could be available for", text)
        self.assertIn("Skyreach is not available for any other time.", text)


if __name__ == "__main__":
    unittest.main()
