import unittest

from flow_review import review, markdown, check_contract


class FlowReviewTests(unittest.TestCase):
    def test_nested_route_and_secret_redaction(self):
        old = {"flowContents": {"processGroups": [{"processors": [{"identifier": "p", "properties": {"Password": "secret-old"}}], "connections": [{"source": {"id": "p"}, "destination": {"id": "dead"}, "selectedRelationships": ["failure"]}]}]}}
        new = {"flowContents": {"processGroups": [{"processors": [{"identifier": "p", "properties": {"Password": "secret-new"}}], "connections": [{"source": {"id": "p"}, "destination": {"id": "ok"}, "selectedRelationships": ["failure"]}]}]}}
        result = review(old, new)
        self.assertEqual(result["routes_removed"][0]["relationship"], "failure")
        self.assertEqual(result["properties_changed"], [{"processor": "p", "property": "Password"}])
        self.assertNotIn("secret-old", markdown(result))
        self.assertNotIn("secret-new", str(result))

    def test_termination_change(self):
        old = {"processors": [{"id": "p", "autoTerminatedRelationships": []}]}
        new = {"processors": [{"id": "p", "autoTerminatedRelationships": ["failure"]}]}
        self.assertEqual(review(old, new)["auto_terminated_added"], [{"processor": "p", "relationship": "failure"}])

    def test_required_route_contract(self):
        flow = {"connections": [{"source": {"id": "a"}, "destination": {"id": "b"}, "selectedRelationships": ["success"]}]}
        contract = {"required_routes": [{"source": "a", "relationship": "failure", "destination": "b"}]}
        self.assertEqual(check_contract(flow, contract), contract["required_routes"])


if __name__ == "__main__":
    unittest.main()
