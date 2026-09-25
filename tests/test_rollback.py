"""受控回退接口测试：正常回退、条件不满足、幂等重复请求、审计查询与重启持久化。

注意：导入 app 模块前把 DATABASE_URL 指向临时文件，
避免测试触发建表/迁移而改动仓库跟踪的 invest_ledger.db。
"""

import os
import tempfile
import unittest
from datetime import date

_DB_SINK = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_DB_SINK.close()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_DB_SINK.name}")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app import models
from app.enums import (
    MilestoneStatus,
    MilestoneType,
    ParkType,
    ProjectStatus,
    Region,
)

API = "/api/v1"
AUTHORIZED_OPERATOR = "招商主管"
UNAUTHORIZED_OPERATOR = "项目文员"


class ControlledRollbackTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        self.engine = create_engine(
            f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        app.dependency_overrides[get_db] = self._override_get_db
        self.client = TestClient(app)
        self._seed()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()
        os.unlink(self.db_path)

    def _override_get_db(self):
        db = self.Session()
        try:
            yield db
        finally:
            db.close()

    # ---------- 数据准备 ----------

    def _seed(self):
        db = self.Session()
        park = models.IndustrialPark(
            name="回退测试园区", park_type=ParkType.KEY_INDUSTRIAL, city="南宁"
        )
        entity = models.Entity(
            name="回退测试主体",
            region=Region.GUANGXI,
            country_or_province="广西",
            contact_person="张三",
            contact_phone="13800000000",
        )
        db.add_all([park, entity])
        db.flush()

        def new_project(name, code, status):
            p = models.Project(
                name=name,
                project_code=code,
                status=status,
                investment_direction="果汁加工",
                planned_investment_10k=1200.0,
                park_id=park.id,
                initiator_id=entity.id,
            )
            db.add(p)
            db.flush()
            return p

        def new_milestone(project_id, sequence, status, name):
            m = models.ProjectMilestone(
                project_id=project_id,
                sequence=sequence,
                milestone_type=MilestoneType.FOUNDATION,
                name=name,
                status=status,
                planned_date=date(2026, 3, 1),
            )
            db.add(m)
            return m

        # 误推进到建设中的项目：有立项依据 + 两条未完成里程碑（正常回退对象）
        p_ok = new_project("回退项目-正常", "RB-OK", ProjectStatus.UNDER_CONSTRUCTION)
        db.add(
            models.ProjectApproval(
                project_id=p_ok.id,
                approval_number="桂审字〔2026〕11号",
                approval_date=date(2026, 1, 15),
                approving_authority="自治区发展改革委",
                agreed_investment_10k=1100.0,
            )
        )
        new_milestone(p_ok.id, 1, MilestoneStatus.IN_PROGRESS, "项目奠基开工")
        new_milestone(p_ok.id, 2, MilestoneStatus.NOT_STARTED, "主体结构封顶")

        # 有已完成里程碑的项目（回退会破坏建设历史）
        p_done_ms = new_project(
            "回退项目-已完成里程碑", "RB-DONE", ProjectStatus.UNDER_CONSTRUCTION
        )
        new_milestone(p_done_ms.id, 1, MilestoneStatus.COMPLETED, "项目奠基开工")
        new_milestone(p_done_ms.id, 2, MilestoneStatus.IN_PROGRESS, "主体结构封顶")

        # 已投产且登记了产能报告的项目（回退会破坏产能兑现历史）
        p_capacity = new_project(
            "回退项目-产能报告", "RB-CAP", ProjectStatus.COMMISSIONED
        )
        db.add(
            models.MonthlyCapacityReport(
                project_id=p_capacity.id,
                report_year=2026,
                report_month=6,
                actual_output_tonnes=88.0,
            )
        )

        # 已立项项目（用于目标状态非法的用例）
        p_established = new_project(
            "回退项目-已立项", "RB-EST", ProjectStatus.ESTABLISHED
        )

        # 会话关闭后 ORM 对象会 detached，测试只保留主键
        self.p_ok_id = p_ok.id
        self.p_done_ms_id = p_done_ms.id
        self.p_capacity_id = p_capacity.id
        self.p_established_id = p_established.id

        db.commit()
        db.close()

    def _rollback_payload(self, **overrides):
        payload = {
            "to_status": ProjectStatus.NEGOTIATING.value,
            "operator": AUTHORIZED_OPERATOR,
            "reason": "项目被误推进到建设阶段，退回洽谈阶段重新确认合作条件",
            "request_id": "RB-2026-0001",
        }
        payload.update(overrides)
        return payload

    def _post_rollback(self, project_id, **overrides):
        return self.client.post(
            f"{API}/projects/{project_id}/rollback",
            json=self._rollback_payload(**overrides),
        )

    # ---------- 正常回退 ----------

    def test_rollback_success_preserves_approval_and_milestones(self):
        resp = self._post_rollback(self.p_ok_id)
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["from_status"], ProjectStatus.UNDER_CONSTRUCTION.value)
        self.assertEqual(body["to_status"], ProjectStatus.NEGOTIATING.value)
        self.assertFalse(body["idempotent_replay"])
        self.assertEqual(body["operator"], AUTHORIZED_OPERATOR)
        self.assertEqual(body["request_id"], "RB-2026-0001")

        affected = body["affected_records"]
        self.assertEqual(
            affected["preserved_approval"]["approval_number"], "桂审字〔2026〕11号"
        )
        self.assertEqual(len(affected["pending_milestones"]), 2)
        self.assertEqual(affected["capacity_report_count"], 0)

        # 项目状态已退回洽谈中
        project = self.client.get(f"{API}/projects/{self.p_ok_id}").json()
        self.assertEqual(project["status"], ProjectStatus.NEGOTIATING.value)

        # 原审批依据保留，仍可通过立项接口查询
        approval = self.client.get(
            f"{API}/workflow/projects/{self.p_ok_id}/approval"
        )
        self.assertEqual(approval.status_code, 200)
        self.assertEqual(approval.json()["approval_number"], "桂审字〔2026〕11号")

        # 未完成里程碑保持原状、仍然有效
        milestones = self.client.get(
            f"{API}/workflow/projects/{self.p_ok_id}/milestones"
        ).json()
        self.assertEqual(len(milestones), 2)
        self.assertEqual(milestones[0]["status"], MilestoneStatus.IN_PROGRESS.value)
        self.assertEqual(milestones[1]["status"], MilestoneStatus.NOT_STARTED.value)

    # ---------- 条件不满足 ----------

    def test_rollback_forbidden_for_unauthorized_operator(self):
        resp = self._post_rollback(self.p_ok_id, operator=UNAUTHORIZED_OPERATOR)
        self.assertEqual(resp.status_code, 403)
        self.assertIn("无项目回退权限", resp.json()["detail"])
        # 状态未被改动
        project = self.client.get(f"{API}/projects/{self.p_ok_id}").json()
        self.assertEqual(project["status"], ProjectStatus.UNDER_CONSTRUCTION.value)

    def test_rollback_rejected_when_milestone_completed(self):
        resp = self._post_rollback(self.p_done_ms_id)
        self.assertEqual(resp.status_code, 409)
        detail = resp.json()["detail"]
        self.assertIn("已完成里程碑", detail)
        self.assertIn("项目奠基开工", detail)

    def test_rollback_rejected_when_capacity_report_exists(self):
        resp = self._post_rollback(self.p_capacity_id)
        self.assertEqual(resp.status_code, 409)
        detail = resp.json()["detail"]
        self.assertIn("月度产能报告", detail)
        self.assertIn("1 条", detail)

    def test_rollback_rejected_for_same_or_forward_target(self):
        resp_same = self._post_rollback(
            self.p_established_id, to_status=ProjectStatus.ESTABLISHED.value
        )
        self.assertEqual(resp_same.status_code, 409)
        self.assertIn("无需回退", resp_same.json()["detail"])

        resp_forward = self._post_rollback(
            self.p_established_id, to_status=ProjectStatus.UNDER_CONSTRUCTION.value
        )
        self.assertEqual(resp_forward.status_code, 409)
        self.assertIn("只能退回到更早阶段", resp_forward.json()["detail"])

    def test_rollback_requires_reason_and_operator(self):
        payload = self._rollback_payload()
        del payload["reason"]
        resp = self.client.post(
            f"{API}/projects/{self.p_ok_id}/rollback", json=payload
        )
        self.assertEqual(resp.status_code, 422)

    def test_rollback_project_not_found(self):
        resp = self._post_rollback(99999)
        self.assertEqual(resp.status_code, 404)

    # ---------- 幂等重复请求 ----------

    def test_duplicate_request_returns_stable_result(self):
        first = self._post_rollback(self.p_ok_id)
        self.assertEqual(first.status_code, 200, first.text)

        second = self._post_rollback(self.p_ok_id)
        self.assertEqual(second.status_code, 200, second.text)

        first_body, second_body = first.json(), second.json()
        self.assertFalse(first_body["idempotent_replay"])
        self.assertTrue(second_body["idempotent_replay"])
        # 返回结果稳定：同一条日志、相同的前后状态
        self.assertEqual(first_body["log_id"], second_body["log_id"])
        self.assertEqual(first_body["from_status"], second_body["from_status"])
        self.assertEqual(first_body["to_status"], second_body["to_status"])
        self.assertEqual(first_body["logged_at"], second_body["logged_at"])

        # 只写入一条回退日志，项目状态未被二次变更
        logs = self.client.get(
            f"{API}/projects/{self.p_ok_id}/status-logs", params={"action": "rollback"}
        ).json()
        self.assertEqual(len(logs), 1)
        project = self.client.get(f"{API}/projects/{self.p_ok_id}").json()
        self.assertEqual(project["status"], ProjectStatus.NEGOTIATING.value)

        # 换一个 request_id 重复同一回退意图：按当前状态校验，拒绝且说明原因
        third = self._post_rollback(self.p_ok_id, request_id="RB-2026-0002")
        self.assertEqual(third.status_code, 409)
        self.assertIn("无需回退", third.json()["detail"])

    # ---------- 审计查询与重启持久化 ----------

    def test_audit_log_queryable_with_operator_reason_and_affected_records(self):
        self._post_rollback(self.p_ok_id)

        logs = self.client.get(f"{API}/projects/{self.p_ok_id}/status-logs").json()
        self.assertEqual(len(logs), 1)
        log = logs[0]
        self.assertEqual(log["action"], "rollback")
        self.assertEqual(log["operator"], AUTHORIZED_OPERATOR)
        self.assertEqual(log["reason"], "项目被误推进到建设阶段，退回洽谈阶段重新确认合作条件")
        self.assertEqual(log["request_id"], "RB-2026-0001")
        self.assertEqual(log["from_status"], ProjectStatus.UNDER_CONSTRUCTION.value)
        self.assertEqual(log["to_status"], ProjectStatus.NEGOTIATING.value)
        self.assertEqual(
            log["affected_records"]["preserved_approval"]["approval_number"],
            "桂审字〔2026〕11号",
        )
        self.assertEqual(len(log["affected_records"]["pending_milestones"]), 2)

        # action 过滤：rollback 可查，transition 无记录
        rollback_logs = self.client.get(
            f"{API}/projects/{self.p_ok_id}/status-logs", params={"action": "rollback"}
        ).json()
        self.assertEqual(len(rollback_logs), 1)
        transition_logs = self.client.get(
            f"{API}/projects/{self.p_ok_id}/status-logs",
            params={"action": "transition"},
        ).json()
        self.assertEqual(len(transition_logs), 0)

    def test_state_and_idempotency_survive_service_restart(self):
        first = self._post_rollback(self.p_ok_id)
        self.assertEqual(first.status_code, 200, first.text)

        # 模拟服务重启：关闭引擎，基于同一数据库文件重建会话
        self.engine.dispose()
        self.engine = create_engine(
            f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False}
        )
        self.Session = sessionmaker(bind=self.engine)

        # 重启后仍能看到完整的前后状态与审计字段
        logs = self.client.get(f"{API}/projects/{self.p_ok_id}/status-logs").json()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["from_status"], ProjectStatus.UNDER_CONSTRUCTION.value)
        self.assertEqual(logs[0]["to_status"], ProjectStatus.NEGOTIATING.value)
        self.assertEqual(logs[0]["operator"], AUTHORIZED_OPERATOR)
        project = self.client.get(f"{API}/projects/{self.p_ok_id}").json()
        self.assertEqual(project["status"], ProjectStatus.NEGOTIATING.value)

        # 重启后重复提交同一回退请求，仍返回首次的稳定结果
        replay = self._post_rollback(self.p_ok_id)
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertTrue(replay.json()["idempotent_replay"])
        self.assertEqual(replay.json()["log_id"], first.json()["log_id"])
        logs = self.client.get(f"{API}/projects/{self.p_ok_id}/status-logs").json()
        self.assertEqual(len(logs), 1)


if __name__ == "__main__":
    unittest.main()
