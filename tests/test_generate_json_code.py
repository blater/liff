import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from generate_json_code import main


class GenericMultiTargetGeneratorTests(unittest.TestCase):
    def test_unrelated_json_template_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "products.json").write_text(
                json.dumps(
                    {
                        "catalog": {
                            "name": "Night market",
                            "products": [
                                {"sku": "tea", "price": 3.5, "tags": ["hot"]},
                                {"sku": "cake", "price": 4, "tags": []},
                            ],
                        }
                    }
                ),
                encoding="utf-8",
            )
            (root / "report.tmpl").write_text(
                "{{catalog.name}}\n"
                "{{#catalog.products}}"
                "{{sku}}={{price|json}} tags={{tags|json}}\n"
                "{{/catalog.products}}",
                encoding="utf-8",
            )
            config = root / "targets.json"
            config.write_text(
                json.dumps(
                    {
                        "input": "products.json",
                        "targets": {
                            "report": {
                                "template": "report.tmpl",
                                "output": "generated/report.txt",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(sys, "argv", ["generate_json_code.py", "--config", str(config)]):
                self.assertEqual(main(), 0)

            output = root / "generated" / "report.txt"
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                'Night market\ntea=3.5 tags=["hot"]\ncake=4 tags=[]\n',
            )

            with patch.object(
                sys,
                "argv",
                ["generate_json_code.py", "--config", str(config), "--check"],
            ):
                self.assertEqual(main(), 0)
