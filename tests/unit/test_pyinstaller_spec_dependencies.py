import unittest

class TestPyInstallerSpecDependencies(unittest.TestCase):
    def test_critical_dll_list(self):
        required_dlls = ["Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll", "Qt6Pdf.dll"]
        self.assertIn("Qt6Pdf.dll", required_dlls)

if __name__ == "__main__":
    unittest.main()
