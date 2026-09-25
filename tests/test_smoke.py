"""验证招商台账服务的基础入口和关键状态枚举。"""

import os
import tempfile
import unittest

# 导入 app 前把数据库指向临时文件，避免测试改动仓库跟踪的 invest_ledger.db
_DB_SINK = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_DB_SINK.close()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_DB_SINK.name}")

from app.main import app
from app.enums import ProjectStatus


class ServiceSmokeTests(unittest.TestCase):
    def test_application_metadata_and_statuses(self):
        self.assertIn("招商台账", app.title)
        self.assertEqual(ProjectStatus.ATTRACTING_INVESTMENT.value, "招商中")
        self.assertGreaterEqual(len(app.routes), 10)


if __name__ == "__main__":
    unittest.main()
