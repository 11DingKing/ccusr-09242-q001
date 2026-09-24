"""验证招商台账服务的基础入口和关键状态枚举。"""

import unittest

from app.main import app
from app.enums import ProjectStatus


class ServiceSmokeTests(unittest.TestCase):
    def test_application_metadata_and_statuses(self):
        self.assertIn("招商台账", app.title)
        self.assertEqual(ProjectStatus.ATTRACTING_INVESTMENT.value, "招商中")
        self.assertGreaterEqual(len(app.routes), 10)


if __name__ == "__main__":
    unittest.main()
