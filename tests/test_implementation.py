import copy,json,unittest
from flow_review import review,markdown,main
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
class ImplementationTests(unittest.TestCase):
 def test_processor_class_and_bundle_change_without_other_diff(self):
  old={'processors':[{'id':'p','type':'OldProcessor','bundle':{'version':'1'}}]};new=copy.deepcopy(old);new['processors'][0].update(type='NewProcessor',bundle={'version':'2'})
  changes=review(old,new)['behavior_changed'];self.assertEqual({c['field']for c in changes},{'type','bundle'});self.assertNotIn('NewProcessor',json.dumps(changes))
 def test_nested_controller_property_changes_are_detected_without_values(self):
  old={'processGroups':[{'controllerServices':[{'id':'service','properties':{'Password':'SECRET_OLD'},'type':'Old'}]}]};new=copy.deepcopy(old);new['processGroups'][0]['controllerServices'][0]['properties']['Password']='SECRET_NEW'
  report=review(old,new);self.assertEqual(report['behavior_changed'],[{'kind':'controllerServices','component':'service','field':'properties'}]);self.assertNotIn('SECRET_',json.dumps(report))
  for lang in ['fr','en','es']:self.assertNotIn('SECRET_',markdown(report,lang))
 def test_added_removed_and_unidentified_services_are_accounted(self):
  r=review({'controllerServices':[{'id':'old'}]},{'controllerServices':[{'id':'new'},{}]});self.assertEqual(r['behavior_components_removed'],[{'kind':'controllerServices','component':'old'}]);self.assertEqual(r['behavior_components_added'],[{'kind':'controllerServices','component':'new'}]);self.assertEqual(r['behavior_unchecked'],[{'side':'after','count':1}])
 def test_connection_endpoint_change_with_no_relationships_is_still_visible(self):
  old={'connections':[{'id':'c','source':{'id':'a'},'destination':{'id':'b'}}]};new=copy.deepcopy(old);new['connections'][0]['destination']['id']='c';r=review(old,new);self.assertEqual(r['routes_removed'],[]);self.assertEqual(r['behavior_changed'][0]['field'],'destination')
 def test_ci_gate_fails_on_service_drift(self):
  with TemporaryDirectory()as tmp:
   old=Path(tmp)/'old.json';new=Path(tmp)/'new.json';old.write_text(json.dumps({'controllerServices':[{'id':'s','enabled':False}]}));new.write_text(json.dumps({'controllerServices':[{'id':'s','enabled':True}]}))
   with redirect_stdout(StringIO()):self.assertEqual(main([str(old),str(new),'--fail-on-behavior-change']),1)
