import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
APP = ROOT / "smartdomo_benchmark" / "app"
sys.path.insert(0, str(APP))
from test_sharing import r4_run, run
import sharing


class CommunityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        root = Path(cls.temporary.name)
        cls.admin = root / "admin.key"
        cls.admin.write_text("test-administration-secret")
        os.environ["BENCHMARK_DATA"] = str(root / "data")
        os.environ["BENCHMARK_ADMIN_FILE"] = str(cls.admin)
        spec = importlib.util.spec_from_file_location("community_service_test", ROOT / "community" / "service.py")
        cls.service = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.service)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def request(self, method, path, body=None, query="", authorization=""):
        raw = b"" if body is None else json.dumps(body).encode()
        env = {
            "REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query,
            "REMOTE_ADDR": "127.0.0.1", "wsgi.input": io.BytesIO(raw),
            "CONTENT_LENGTH": str(len(raw)),
        }
        if body is not None:
            env["CONTENT_TYPE"] = "application/json"
        if authorization:
            env["HTTP_AUTHORIZATION"] = authorization
        result = {}
        def start(status, headers):
            result["status"], result["headers"] = status, headers
        payload = b"".join(self.service.application(env, start))
        result["body"] = json.loads(payload)
        return result

    def test_publish_list_moderate_and_delete(self):
        source = run(100, 1.01)
        body = sharing.make_payload([source], "Lab", "Home Assistant Green", False)
        body["consent"] = True
        published = self.request("POST", "/api/entries", body)
        self.assertTrue(published["status"].startswith("201"))
        eid = published["body"]["id"]
        token = published["body"]["delete_key"]

        listed = self.request("GET", "/api/entries", query="profile=light&device_type=green&alias=la")
        entry = next(item for item in listed["body"]["entries"] if item["id"] == eid)
        self.assertNotIn("delete_key", entry)
        self.assertEqual(entry["device_type"], "green")
        self.assertIn("quality", entry)

        filtered = self.request("GET", "/api/entries", query="profile=light&ram=4&storage_size=32")
        self.assertTrue(any(item["id"] == eid for item in filtered["body"]["entries"]))
        excluded = self.request("GET", "/api/entries", query="profile=light&ram=8&storage_size=64")
        self.assertFalse(any(item["id"] == eid for item in excluded["body"]["entries"]))

        auth = "Bearer test-administration-secret"
        hidden = self.request("POST", "/api/admin/moderate", {"id": eid, "hidden": True}, authorization=auth)
        self.assertTrue(hidden["status"].startswith("200"))
        detail = self.request("GET", "/api/entries/" + eid)
        self.assertTrue(detail["status"].startswith("404"))

        self.request("POST", "/api/admin/moderate", {"id": eid, "hidden": False}, authorization=auth)
        deleted = self.request("DELETE", "/api/entries/" + eid, {"delete_key": token})
        self.assertEqual(deleted["body"], {"deleted": True})
        self.assertIn(eid, self.service.TOMBSTONES.read_text())

    def test_duplicate_measurement_is_rejected(self):
        body = sharing.make_payload([run(200, 1.02)], "", "Green", False)
        body["consent"] = True
        first = self.request("POST", "/api/entries", body)
        second = self.request("POST", "/api/entries", body)
        self.assertTrue(first["status"].startswith("201"))
        self.assertTrue(second["status"].startswith("409"))

    def test_admin_requires_key(self):
        result = self.request("GET", "/api/admin/entries", query="profile=light")
        self.assertTrue(result["status"].startswith("403"))

    def test_startup_removes_legacy_public_entries(self):
        legacy_id = "legacy-entry"
        with self.service.db() as conn:
            conn.execute("INSERT INTO entries VALUES(?,?,?,?,?,?,0)",
                         (legacy_id, "legacy-fingerprint", 1, "unused", "{}",
                          json.dumps({"methodology_id": "legacy"})))
            conn.execute("INSERT INTO run_ids VALUES(?,?)", ("legacy-run", legacy_id))
        self.service.initialize()
        with self.service.db() as conn:
            self.assertIsNone(conn.execute("SELECT id FROM entries WHERE id=?", (legacy_id,)).fetchone())
            self.assertIsNone(conn.execute("SELECT rid FROM run_ids WHERE entry_id=?", (legacy_id,)).fetchone())

    def test_r4_is_the_only_public_methodology(self):
        body = sharing.make_payload([r4_run(300)], "R4", "Green", False)
        body["consent"] = True
        published = self.request("POST", "/api/entries", body)
        self.assertTrue(published["status"].startswith("201"))
        eid = published["body"]["id"]
        current = self.request("GET", "/api/entries", query="profile=light")
        self.assertEqual(current["body"]["methodology_id"], "CORE-2026.9.1-R4")
        self.assertTrue(any(item["id"] == eid for item in current["body"]["entries"]))
        self.assertEqual(len(current["body"]["methodologies"]), 1)


if __name__ == "__main__":
    unittest.main()
