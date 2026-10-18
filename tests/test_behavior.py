import copy
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from flow_review import review, markdown, main

class BehaviorTests(unittest.TestCase):
    def flow(self):
        return {"flowContents": {"processors": [{"identifier": "p", "schedulingPeriod": "1 sec", "properties": {"Password": "synthetic-canary"}}], "connections": [{"identifier": "q", "source": {"id": "p"}, "destination": {"id": "sink"}, "selectedRelationships": ["success"], "flowFileExpiration": "0 sec", "backPressureObjectThreshold": 10000}]}}
    def test_same_routes_expiration_change_and_no_values(self):
        before = self.flow(); after = copy.deepcopy(before)
        after["flowContents"]["connections"][0]["flowFileExpiration"] = "30 sec"
        result = review(before, after)
        self.assertEqual(result["routes_added"], []); self.assertEqual(result["routes_removed"], [])
        self.assertEqual(result["behavior_changed"], [{"kind":"connections", "component":"q", "field":"flowFileExpiration"}])
        for lang in ("fr", "en", "es"):
            rendered=markdown(result,lang)
            self.assertNotIn("synthetic-canary",rendered); self.assertNotIn("30 sec",rendered)
            self.assertIn("flowFileExpiration",rendered)
    def test_scheduling_backpressure_and_missing_vs_null(self):
        before=self.flow();after=copy.deepcopy(before)
        after["flowContents"]["processors"][0]["schedulingPeriod"]="5 sec"
        after["flowContents"]["processors"][0]["scheduledState"]=None
        after["flowContents"]["connections"][0]["backPressureObjectThreshold"]=0
        fields=[x["field"] for x in review(before,after)["behavior_changed"]]
        self.assertEqual(set(fields),{"schedulingPeriod","scheduledState","backPressureObjectThreshold"})
    def test_nested_add_remove_and_incomplete_identity(self):
        before=self.flow();after=copy.deepcopy(before)
        after["flowContents"]["processGroups"]=[{"processors":[{"identifier":"nested"}],"connections":[{"source":{"id":"a"},"destination":{"id":"b"},"selectedRelationships":[]}]}]
        result=review(before,after)
        self.assertEqual(result["behavior_components_added"],[{"kind":"processors","component":"nested"}])
        self.assertEqual(result["behavior_unchecked"],[{"side":"after","count":1}])
    def test_unchanged_copy_and_cli_gate_all_languages(self):
        with tempfile.TemporaryDirectory() as d:
            before=Path(d)/"before.json";after=Path(d)/"after.json"
            before.write_text(json.dumps(self.flow()));after.write_text(before.read_text())
            for lang in ("fr","en","es"):
                with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(main([str(before),str(after),"--lang",lang,"--fail-on-behavior-change"]),0)
            value=self.flow();value["flowContents"]["connections"][0]["flowFileExpiration"]="30 sec";after.write_text(json.dumps(value))
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(main([str(before),str(after),"--fail-on-behavior-change"]),1)
    def test_incomplete_and_added_components_fail_cli_gate(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a.json";b=Path(d)/"b.json";a.write_text(json.dumps(self.flow()));x=self.flow();del x["flowContents"]["connections"][0]["identifier"];b.write_text(json.dumps(x))
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(main([str(a),str(b),"--fail-on-behavior-change"]),1)
    def test_duplicate_queue_ids_and_bad_shapes_rejected(self):
        value=self.flow();value["flowContents"]["connections"]*=2
        with self.assertRaises(ValueError):review(self.flow(),value)
        with self.assertRaises(ValueError):review([],self.flow())
    def test_null_property_added_is_a_change(self):
        value=self.flow();value["flowContents"]["processors"][0]["properties"]["new"]=None
        self.assertEqual(review(self.flow(),value)["properties_changed"],[{"processor":"p","property":"new"}])
