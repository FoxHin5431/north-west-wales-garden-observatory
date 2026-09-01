import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublicRepositoryPrivacyTests(unittest.TestCase):
    def test_public_snapshot_has_no_forbidden_fields(self):
        payload = json.loads((ROOT / "data" / "public_snapshot.json").read_text(encoding="utf-8"))
        flattened = json.dumps(payload).lower()
        for forbidden in ("latitude", "longitude", "clip_name", "audio", "hostname", "ip_address"):
            self.assertNotIn(forbidden, flattened)

    def test_app_has_no_audio_widget(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("st.audio", source)

    def test_no_private_network_addresses_in_public_files(self):
        private_ip = re.compile(r"(?:10\.|127\.0\.0\.1|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.)")
        for relative in ("app.py", "README.md", "PRIVACY.md", "data/public_snapshot.json"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIsNone(private_ip.search(text), relative)


if __name__ == "__main__":
    unittest.main()

