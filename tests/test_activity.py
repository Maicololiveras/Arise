import json
import unittest
from arise_app.activity import PublicActivity

class ActivityTests(unittest.TestCase):
    def test_projection_excludes_private_thought_prompts_arguments_results(self):
        a=PublicActivity();a.consume({'type':'run_start'})
        before=a.snapshot()
        self.assertFalse(a.consume({'type':'message_update','assistantMessageEvent':{'type':'thinking_delta','delta':'PRIVATE_SECRET'}}))
        self.assertEqual(a.snapshot(),before)
        a.consume({'type':'tool_execution_start','toolName':'bash','args':{'command':'PRIVATE_SECRET'}})
        a.consume({'type':'tool_execution_end','toolName':'bash','toolCallId':'call-1','result':{'text':'PRIVATE_SECRET'},'isError':False})
        self.assertNotIn('PRIVATE_SECRET',json.dumps(a.snapshot()))
        self.assertEqual(a.snapshot()['tools_completed'],1)
        self.assertIsNone(a.snapshot()['progress_total'])
    def test_tools_model_missing_wait_error_stop(self):
        a=PublicActivity();a.consume({'type':'run_start'})
        a.consume({'type':'message_start','message':{'role':'assistant'}})
        self.assertEqual(a.snapshot()['model'],'')
        a.consume({'type':'tool_execution_start','toolName':'read'})
        self.assertEqual(a.phase,'exploring')
        a.consume({'type':'tool_execution_start','toolName':'arise_call','args':{'name':'documents.read_docx'}})
        self.assertEqual(a.phase,'verifying')
        a.consume({'type':'waiting'});self.assertEqual(a.phase,'waiting')
        a.consume({'type':'tool_execution_end','toolName':'read','isError':True})
        self.assertEqual(a.phase,'error')
        a.consume({'type':'stop'});a.consume({'type':'finished'})
        self.assertEqual(a.phase,'stopped')
        a.consume({'type':'run_start'});a.model_state({'id':'fixture','provider':'test'})
        self.assertEqual(a.snapshot()['model'],'test/fixture')
    def test_real_subagent_status_lifecycle_and_bounded_details(self):
        a=PublicActivity();a.consume({'type':'run_start'})
        a.consume({'type':'subagent_status','task_id':'task-1','status':'running','prompt':'SECRET'})
        a.consume({'type':'finished'})
        self.assertEqual(a.phase,'executing');self.assertEqual(a.snapshot()['subagents_active'],1)
        a.consume({'type':'subagent_status','task_id':'task-1','status':'completed'})
        self.assertEqual(a.phase,'done')
        for i in range(70):a.consume({'type':'tool_execution_start','toolName':'read'})
        self.assertEqual(len(a.snapshot()['details']),30)
        self.assertNotIn('SECRET',str(a.snapshot()))
