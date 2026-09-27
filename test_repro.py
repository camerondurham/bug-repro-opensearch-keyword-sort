"""Offline checks for result validity and exact-owned cleanup; never run Docker."""
import argparse
import copy
import json
import unittest
from unittest.mock import patch

import repro


class ContractTests(unittest.TestCase):
    def response(self):
        return {"timed_out": False,
                "_shards": {"total": 18, "successful": 18, "failed": 0, "skipped": 0},
                "hits": {"hits": [{"_id": f"item-{rank:09d}",
                                   "sort": [f"item-{rank:09d}", rank % 16],
                                   "_version": 1, "_source": repro.document(rank)}
                                  for rank in range(250)]}}

    def test_oracle_accepts_exact_results_rejects_wrong_payload(self):
        response = self.response()
        self.assertEqual(len(repro.validate(response, 18)), 64)
        for field, value in (("_version", 2), ("sort", ["wrong", 0]),
                             ("_source", {}), ("_id", "wrong")):
            bad = copy.deepcopy(response)
            bad["hits"]["hits"][0][field] = value
            with self.assertRaises(RuntimeError):
                repro.validate(bad, 18)

    def test_incomplete_shards_fail(self):
        response = self.response()
        response["_shards"]["successful"] = 17
        with self.assertRaises(RuntimeError):
            repro.validate(response, 18)

    def test_rebuilt_segment_shapes_ignore_names_not_document_counts(self):
        a = {"segments": {"0": {"_0": {"num_docs": 100, "deleted_docs": 0}}}}
        b = {"segments": {"0": {"_1": {"num_docs": 100, "deleted_docs": 0}}}}
        self.assertEqual(repro.segment_shape(a), repro.segment_shape(b))
        b["segments"]["0"]["_1"]["num_docs"] = 99
        self.assertNotEqual(repro.segment_shape(a), repro.segment_shape(b))

    def test_settings_readback_required(self):
        with patch.object(repro, "http", return_value={"nodes": {"node": {"settings": {}}}}):
            with self.assertRaises(RuntimeError):
                repro.settings(9200, 128)

    def test_failed_startup_cleans_only_exact_owned_id(self):
        cid, calls = "a" * 64, []
        owner = "b" * 32
        inspection = {"Id": cid, "Image": "sha256:image",
                      "Config": {"Labels": {"repro.owner": owner}}}
        def docker(*args, **kwargs):
            calls.append(args)
            if args[0] == "create":
                return cid
            if args[0] == "inspect":
                return json.dumps([inspection])
            if args[0] == "start":
                raise RuntimeError("fake startup failure")
            return ""
        args = argparse.Namespace(version="2.19.0", heap="2g")
        result = {"cells": []}
        with patch.object(repro, "docker", side_effect=docker), \
                patch.object(repro.uuid, "uuid4") as nonce:
            nonce.return_value.hex = owner
            with self.assertRaisesRegex(RuntimeError, "startup failure"):
                repro.cell(args, {"Id": "sha256:image"}, 1024, 1, result)
        self.assertIn(("rm", "-f", "-v", cid), calls)
        self.assertEqual(result["cells"][0]["cleanup"], "clean")

    def test_unknown_create_output_never_removed_by_name(self):
        calls = []
        def docker(*args, **kwargs):
            calls.append(args)
            return "malformed-id"
        result = {"cells": []}
        with patch.object(repro, "docker", side_effect=docker):
            with self.assertRaisesRegex(RuntimeError, "ambiguous ownership"):
                repro.cell(argparse.Namespace(version="2.19.0", heap="2g"),
                           {"Id": "sha256:image"}, 128, 1, result)
        self.assertEqual([call[0] for call in calls], ["create"])
        self.assertEqual(result["cells"][0]["cleanup"], "unknown")


if __name__ == "__main__":
    unittest.main()
