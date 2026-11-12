import unittest,json,tempfile
from pathlib import Path
from flow_review import routing_obligations
class Obligations(unittest.TestCase):
 def test_missing_required_route(self):
  x=routing_obligations({'processors':[{'identifier':'p'}]},{'p':['success']});self.assertEqual(x['findings'][0]['code'],'unrouted_required_relationship')
 def test_explicit_auto_termination_satisfies_obligation(self):
  x=routing_obligations({'processors':[{'identifier':'p','autoTerminatedRelationships':['success']}]},{'p':['success']});self.assertEqual(x['findings'],[])
 def test_routed_and_terminated_is_conflict(self):
  doc={'processors':[{'identifier':'p','autoTerminatedRelationships':['success']},{'identifier':'q'}],'connections':[{'source':{'id':'p'},'destination':{'id':'q'},'selectedRelationships':['success']}]};self.assertEqual(routing_obligations(doc,{'p':['success']})['findings'][0]['code'],'routed_and_auto_terminated')
