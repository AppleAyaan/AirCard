import base64
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import aircard_backend as backend
import apply_card_skin


class CardRestoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        root_patch = patch.object(backend, "BACKUP_ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.output = redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)
        self.name = backend.ARTWORK_NAMES[0]
        self.original = b"original artwork"
        self.manifest = json.dumps({self.name: hashlib.sha1(self.original).hexdigest()}).encode()

    def backup(self):
        with patch.object(backend, "read_file", side_effect=[self.manifest, self.original]):
            backend.ensure_original_backup("device", "card")

    def test_backup_is_preserved_across_repeated_flashes(self):
        self.backup()
        before = backend.backup_path("device", "card").read_bytes()
        with patch.object(backend, "read_file") as read:
            backend.ensure_original_backup("device", "card")
        read.assert_not_called()
        self.assertEqual(before, backend.backup_path("device", "card").read_bytes())
        self.assertNotEqual(backend.backup_path("other", "card"), backend.backup_path("device", "card"))

    def test_unverified_existing_skin_is_not_saved_as_original(self):
        with patch.object(backend, "read_file", side_effect=[self.manifest, b"old skin"]):
            with self.assertRaisesRegex(ValueError, "older version"):
                backend.ensure_original_backup("device", "card")
        self.assertFalse(backend.backup_path("device", "card").exists())

    def test_missing_backup_never_touches_device(self):
        with patch.object(backend, "write_file") as write, patch.object(backend, "remove_files") as remove:
            self.assertFalse(backend.cmd_restore("device", "card"))
        write.assert_not_called()
        remove.assert_not_called()

    def test_restore_writes_original_removes_added_assets_and_caches(self):
        self.backup()
        with patch.object(backend, "write_file", return_value=True) as write, patch.object(backend, "remove_files", return_value=True) as remove:
            self.assertTrue(backend.cmd_restore("device", "card"))
        write.assert_called_once_with("device", "/var/mobile/Library/Passes/Cards/card.pkpass", self.name, self.original)
        self.assertEqual(remove.call_count, 4)
        for name in backend.ARTWORK_NAMES[1:]:
            remove.assert_any_call("device", "/var/mobile/Library/Passes/Cards/card.pkpass", [name])
        for ext in (".cache", ".pkcache"):
            remove.assert_any_call("device", f"/var/mobile/Library/Passes/Cards/card{ext}", list(backend.CACHE_FILES))
        self.assertTrue(backend.backup_path("device", "card").exists())

    def test_failed_restore_keeps_backup_for_retry(self):
        self.backup()
        with patch.object(backend, "write_file", return_value=False), patch.object(backend, "remove_files") as remove:
            self.assertFalse(backend.cmd_restore("device", "card"))
        remove.assert_not_called()
        self.assertTrue(backend.backup_path("device", "card").exists())

    def test_cache_failure_does_not_report_success(self):
        self.backup()
        with patch.object(backend, "write_file", return_value=True), patch.object(backend, "remove_files", side_effect=[True, True, False]):
            self.assertFalse(backend.cmd_restore("device", "card"))

    def test_damaged_backup_never_touches_device(self):
        self.backup()
        path = backend.backup_path("device", "card")
        record = json.loads(path.read_text())
        record["assets"][self.name]["data"] = base64.b64encode(b"damaged").decode()
        path.write_text(json.dumps(record))
        with patch.object(backend, "write_file") as write:
            self.assertFalse(backend.cmd_restore("device", "card"))
        write.assert_not_called()

    def test_failed_backup_prevents_skin_writes(self):
        image = self.root / "image.png"
        image.write_bytes(b"image")
        with patch.object(backend, "build_card_assets", return_value=[]), patch.object(backend, "ensure_original_backup", side_effect=ValueError("backup failed")), patch.object(backend, "write_files_batch") as write:
            self.assertFalse(backend.cmd_flash("device", "card", str(image)))
        write.assert_not_called()

    def test_read_does_not_delete_recovered_original_when_writeback_fails(self):
        calls = []
        def native(command, udid, *args):
            calls.append(command)
            if command == "afc-read":
                Path(args[1]).write_bytes(self.original)
            return {"exitCode": 0, "targetGatePassed": True, "operation": {"ok": True}}
        with patch.object(apply_card_skin, "native", side_effect=native), patch.object(apply_card_skin, "run_json", return_value={"exitCode": 0, "ok": True}), patch.object(apply_card_skin, "write_file", return_value=False):
            self.assertIsNone(apply_card_skin.read_file("device", "/pass", self.name))
        self.assertNotIn("finish-write", calls)


if __name__ == "__main__":
    unittest.main()
