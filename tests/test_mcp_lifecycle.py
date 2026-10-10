import tempfile
import unittest
from unittest.mock import Mock, patch
from arise_app.assistant import Assistant

class McpLifecycleTests(unittest.TestCase):
    def test_saving_same_configuration_keeps_verified_clients(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Assistant(tmp)
            client=Mock();client.tools=[{'name':'observe','inputSchema':{}}]
            r.mcp['screenview']=client
            try:
                r.settings({'thinking':'low'})
                client.close.assert_not_called()
                self.assertIn('screenview.observe',[t['name'] for t in r.tool_catalog()['tools']])
                r.settings({'mcp':{}})
                client.close.assert_called_once()
                self.assertNotIn('screenview',r.mcp)
            finally:r.close();r.storage.db.close()

    def test_desktop_permission_connects_enabled_desktop_services(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Assistant(tmp)
            try:
                with patch('arise_app.assistant.os.name','nt'), patch.object(r,'connect_mcp') as connect, patch.object(r,'status',return_value={}):
                    r.set_desktop(True)
                self.assertEqual([c.args[0] for c in connect.call_args_list],['screenview','inputcontrol'])
                self.assertTrue(r.desktop)
            finally:r.close();r.storage.db.close()

    def test_failed_connection_is_reported_and_disabled_service_not_started(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Assistant(tmp);r.storage.config['mcp']['inputcontrol']['enabled']=False
            try:
                with patch('arise_app.assistant.os.name','nt'),patch.object(r,'connect_mcp',side_effect=RuntimeError('fixture unavailable')) as connect,patch.object(r,'status',return_value={}),patch.object(r,'emit') as emit:
                    r.set_desktop(True)
                connect.assert_called_once_with('screenview')
                self.assertTrue(any('fixture unavailable' in str(c) for c in emit.call_args_list))
                self.assertFalse(r.tool_catalog()['mcp_connections']['screenview']['connected'])
            finally:r.close();r.storage.db.close()
