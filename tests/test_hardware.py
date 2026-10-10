import unittest
from unittest.mock import patch
from arise_app.hardware import local_profile,server_command

class HardwareTests(unittest.TestCase):
    def test_eight_gb_without_gpu_selects_cpu_light_profile(self):
        self.assertEqual(local_profile({},8*1024**3),'light')
        self.assertEqual(local_profile({},64*1024**3),'standard')
        self.assertEqual(local_profile({'local_profile':'light'},64*1024**3),'light')
    def test_light_profile_bounds_context_and_threads_without_rewriting_custom_servers(self):
        config={'local_profile':'light','local_server_command':['/owned/llama-server','--ctx-size','8192','--n-gpu-layers','0']}
        command=server_command(config)
        self.assertEqual(command[command.index('--ctx-size')+1],'4096')
        self.assertLessEqual(int(command[command.index('--threads')+1]),4)
        self.assertEqual(config['local_server_command'][2],'8192')
        custom={'local_profile':'light','local_server_command':['custom-server','--ctx-size','8192']}
        self.assertEqual(server_command(custom),custom['local_server_command'])
