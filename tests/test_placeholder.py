import unittest

from cloudshell.networking.cisco.nxos.command_templates import (  # noqa: F401
    nxos_add_remove_vlan,
)


class TestEmpty(unittest.TestCase):
    def setUp(self):
        pass

    def test_smth(self):
        self.assertTrue(True)
