"""受控项目回退能力的接口集成测试。

覆盖：
- 正常回退（建设中误推进 → 已立项 → 洽谈中，立项依据与里程碑保留）
- 条件不满足（未完成里程碑、投产事实、产能数据、立项数据不一致的具体拒绝原因）
- 重复请求（同一 request_id 返回稳定结果，不重复执行/记日志）
- 审计查询（回退请求列表/明细、状态日志中的操作人、理由与受影响记录）
- 权限控制、重启后前后状态完整可查、旧库轻量迁移
"""

import os
import tempfile
import unittest
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 在导入应用前把数据库指到临时文件，避免污染示例库
_TMP_DB_FD, _TMP_DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_TMP_DB_FD)
os.unlink(_TMP_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB_PATH}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.database import get_db, run_lightweight_migrations, Base  # noqa: E402
from app import models  # noqa: E402
from app.enums import (  # noqa: E402
    ProjectStatus,
    MilestoneStatus,
    MilestoneType,
)

API = "/api/v1"
SUPERVISOR = "招商主管"
STAFF = "招商专员"


def client():
    return TestClient(app)


class RollbackApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = client()

    def _uid(self, prefix):
        return f"{prefix}-{uuid.uuid4().hex[:12]}"

    # ---- 造数辅助 ------------------------------------------------------

    def _create_bootstrap(self):
        """创建主体、园区，并返回其 id。"""
        tag = self._uid("e")
        ent = self.client.post(
            f"{API}/entities/",
            json={
                "name": f"主体-{tag}",
                "region": "广西方",
                "country_or_province": "广西",
                "city": "崇左",
                "contact_person": "张三",
                "contact_phone": "0771-12345678",
            },
        )
        self.assertEqual(ent.status_code, 200, ent.text)
        park = self.client.post(
            f"{API}/parks/",
            json={
                "name": f"园区-{tag}",
                "park_type": "重点工业园区",
                "city": "崇左市",
            },
        )
        self.assertEqual(park.status_code, 200, park.text)
        return ent.json()["id"], park.json()["id"]

    def _create_project(self, entity_id, park_id, name=None):
        tag = self._uid("p")
        resp = self.client.post(
            f"{API}/projects/",
            json={
                "name": name or f"项目-{tag}",
                "project_code": f"CODE-{tag}",
                "investment_direction": "热带水果加工",
                "planned_investment_10k": 5000,
                "expected_annual_capacity_tonnes": 1200,
                "promised_monthly_capacity_tonnes": 100,
                "park_id": park_id,
                "initiator_id": entity_id,
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()["id"]

    def _submit_intent(self, project_id, entity_id):
        resp = self.client.post(
            f"{API}/workflow/intents",
            json={
                "project_id": project_id,
                "submitter_id": entity_id,
                "cooperation_content": "合作建设果汁加工线",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()["id"]

    def _approve(self, project_id, operator="王主管"):
        resp = self.client.post(
            f"{API}/workflow/projects/{project_id}/approve",
            json={
                "approval_number": f"审批-{self._uid('a')}",
                "approval_date": "2026-01-15",
                "approving_authority": "园区管委会",
                "agreed_investment_10k": 4800,
                "operator": operator,
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()

    def _milestones(self, project_id):
        resp = self.client.get(f"{API}/workflow/projects/{project_id}/milestones")
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()

    def _set_milestone(self, milestone_id, status):
        resp = self.client.put(
            f"{API}/workflow/milestones/{milestone_id}",
            json={"status": status},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()

    def _project_to_established(self):
        """招商中 →（意向）洽谈中 →（立项）已立项，返回项目 id 与里程碑。"""
        entity_id, park_id = self._create_bootstrap()
        pid = self._create_project(entity_id, park_id)
        self._submit_intent(pid, entity_id)
        self._approve(pid)
        return pid, self._milestones(pid)

    def _manual_status(self, project_id, to_status, reason):
        resp = self.client.post(
            f"{API}/projects/{project_id}/status",
            json={"to_status": to_status, "operator": "王主管", "reason": reason},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()

    def _rollback(self, project_id, request_id, role=SUPERVISOR, reason="误推进，退回上一阶段",
                  target=None, operator="王主管"):
        payload = {
            "request_id": request_id,
            "operator": operator,
            "operator_role": role,
            "reason": reason,
        }
        if target is not None:
            payload["target_status"] = target
        return self.client.post(
            f"{API}/projects/{project_id}/rollback", json=payload
        )

    # ---- 1. 正常回退 ---------------------------------------------------

    def test_rollback_construction_to_established_normal(self):
        """建设中（仅有已完成里程碑、无在办）可受控回退到已立项。"""
        pid, milestones = self._project_to_established()
        m1, m2 = milestones[0]["id"], milestones[1]["id"]

        # 首里程碑进入进行中 → 自动进入建设中；随后完成 m1，m2 尚未启动
        self._set_milestone(m1, MilestoneStatus.IN_PROGRESS.value)
        self._set_milestone(m1, MilestoneStatus.COMPLETED.value)
        self.assertEqual(self._get_status(pid), ProjectStatus.UNDER_CONSTRUCTION.value)

        resp = self._rollback(pid, self._uid("rb-ok"))
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["result"], "applied")
        self.assertEqual(body["from_status"], ProjectStatus.UNDER_CONSTRUCTION.value)
        self.assertEqual(body["to_status"], ProjectStatus.ESTABLISHED.value)
        self.assertEqual(body["project_status"], ProjectStatus.ESTABLISHED.value)
        self.assertIsNotNone(body["status_log_id"])

        self.assertEqual(self._get_status(pid), ProjectStatus.ESTABLISHED.value)

        # 立项依据与里程碑事实保留
        approval = self.client.get(f"{API}/workflow/projects/{pid}/approval")
        self.assertEqual(approval.status_code, 200)
        ms = self._milestones(pid)
        self.assertEqual(ms[0]["status"], MilestoneStatus.COMPLETED.value)
        self.assertEqual(ms[1]["status"], MilestoneStatus.NOT_STARTED.value)

        affected = {(r["type"], r["effect"]) for r in body["affected_records"]}
        self.assertIn(("approval", "retained"), affected)
        self.assertIn(("milestone", "retained"), affected)

    def test_rollback_all_the_way_to_negotiating_after_wrong_push(self):
        """场景：项目被手动误推进到建设中（无任何里程碑进度），
        分两次受控回退退回洽谈中，立项信息始终保留。"""
        pid, _ = self._project_to_established()
        self._manual_status(pid, ProjectStatus.UNDER_CONSTRUCTION.value, "误操作推进")
        self.assertEqual(self._get_status(pid), ProjectStatus.UNDER_CONSTRUCTION.value)

        r1 = self._rollback(pid, self._uid("rb-step1"))
        self.assertEqual(r1.status_code, 200, r1.text)
        self.assertEqual(r1.json()["to_status"], ProjectStatus.ESTABLISHED.value)

        r2 = self._rollback(pid, self._uid("rb-step2"), reason="立项推进依据不足，退回洽谈")
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertEqual(r2.json()["to_status"], ProjectStatus.NEGOTIATING.value)
        self.assertEqual(self._get_status(pid), ProjectStatus.NEGOTIATING.value)

        # 原审批依据保留可查
        approval = self.client.get(f"{API}/workflow/projects/{pid}/approval")
        self.assertEqual(approval.status_code, 200)
        self.assertIn("agreed_investment_10k", approval.json())

        # 里程碑仍为 5 条且全部未启动
        ms = self._milestones(pid)
        self.assertEqual(len(ms), 5)
        self.assertTrue(all(m["status"] == MilestoneStatus.NOT_STARTED.value for m in ms))

    def test_rollback_commissioned_to_construction_when_clean(self):
        """已投产但无投产里程碑事实、无产能数据（误手动推进）可回退建设中。"""
        pid, milestones = self._project_to_established()
        self._set_milestone(milestones[0]["id"], MilestoneStatus.IN_PROGRESS.value)
        self.assertEqual(self._get_status(pid), ProjectStatus.UNDER_CONSTRUCTION.value)
        # 手动误推进到已投产（正式投产里程碑并未完成）
        self._manual_status(pid, ProjectStatus.COMMISSIONED.value, "误操作投产")

        resp = self._rollback(pid, self._uid("rb-comm"))
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["to_status"], ProjectStatus.UNDER_CONSTRUCTION.value)

    # ---- 2. 条件不满足 -------------------------------------------------

    def test_reject_when_in_progress_milestone_exists(self):
        pid, milestones = self._project_to_established()
        self._set_milestone(milestones[0]["id"], MilestoneStatus.IN_PROGRESS.value)
        self.assertEqual(self._get_status(pid), ProjectStatus.UNDER_CONSTRUCTION.value)

        resp = self._rollback(pid, self._uid("rb-rej"))
        self.assertEqual(resp.status_code, 409, resp.text)
        detail = resp.json()["detail"]
        self.assertTrue(detail["request_id"])
        reasons = detail["reject_reasons"]
        self.assertTrue(any("尚未完成" in r for r in reasons), reasons)
        self.assertTrue(any("项目奠基开工" in r for r in reasons), reasons)
        # 项目状态未变
        self.assertEqual(self._get_status(pid), ProjectStatus.UNDER_CONSTRUCTION.value)

    def test_reject_when_delayed_milestone_exists(self):
        pid, milestones = self._project_to_established()
        m1, m2 = milestones[0]["id"], milestones[1]["id"]
        self._set_milestone(m1, MilestoneStatus.IN_PROGRESS.value)
        self._set_milestone(m1, MilestoneStatus.COMPLETED.value)
        self._set_milestone(m2, MilestoneStatus.IN_PROGRESS.value)
        # 直接将 m2 置为已延期（模拟跟踪数据），再回退
        self._update_milestone_direct(m2, MilestoneStatus.DELAYED)

        resp = self._rollback(pid, self._uid("rb-delay"))
        self.assertEqual(resp.status_code, 409)
        reasons = resp.json()["detail"]["reject_reasons"]
        self.assertTrue(any("已延期" in r and "尚未完成" in r for r in reasons), reasons)

    def test_reject_when_official_production_completed(self):
        pid, milestones = self._project_to_established()
        # 顺序推进并完成全部 5 个里程碑 → 已投产
        for i, m in enumerate(milestones):
            self._set_milestone(m["id"], MilestoneStatus.IN_PROGRESS.value)
            self._set_milestone(m["id"], MilestoneStatus.COMPLETED.value)
        self.assertEqual(self._get_status(pid), ProjectStatus.COMMISSIONED.value)

        resp = self._rollback(pid, self._uid("rb-prod"))
        self.assertEqual(resp.status_code, 409)
        reasons = resp.json()["detail"]["reject_reasons"]
        self.assertTrue(any("正式投产里程碑" in r and "不允许回退" in r for r in reasons), reasons)

    def test_reject_when_capacity_report_exists(self):
        pid, milestones = self._project_to_established()
        self._set_milestone(milestones[0]["id"], MilestoneStatus.IN_PROGRESS.value)
        self._manual_status(pid, ProjectStatus.COMMISSIONED.value, "误操作投产")
        rep = self.client.post(
            f"{API}/capacity/reports",
            json={
                "project_id": pid,
                "report_year": 2026,
                "report_month": 8,
                "actual_output_tonnes": 90,
            },
        )
        self.assertEqual(rep.status_code, 200, rep.text)

        resp = self._rollback(pid, self._uid("rb-cap"))
        self.assertEqual(resp.status_code, 409)
        reasons = resp.json()["detail"]["reject_reasons"]
        self.assertTrue(any("月度产能报告" in r for r in reasons), reasons)
        # 低于承诺产能还自动生成了跟进事项，同样应列明
        self.assertTrue(any("产能跟进事项" in r for r in reasons), reasons)
        self.assertEqual(self._get_status(pid), ProjectStatus.COMMISSIONED.value)

    def test_reject_established_to_negotiating_with_progress_fact(self):
        """已立项 → 洽谈中：里程碑已有完成事实时拒绝（会抹掉建设历史）。"""
        pid, milestones = self._project_to_established()
        self._update_milestone_direct(milestones[0]["id"], MilestoneStatus.COMPLETED)

        resp = self._rollback(pid, self._uid("rb-fact"))
        self.assertEqual(resp.status_code, 409)
        reasons = resp.json()["detail"]["reject_reasons"]
        self.assertTrue(any("建设进度已经发生" in r for r in reasons), reasons)
        # 立项信息仍然保留
        self.assertEqual(
            self.client.get(f"{API}/workflow/projects/{pid}/approval").status_code,
            200,
        )

    def test_reject_non_adjacent_and_initial_status(self):
        entity_id, park_id = self._create_bootstrap()
        pid = self._create_project(entity_id, park_id)
        # 招商中（初始状态）不可回退
        resp = self._rollback(pid, self._uid("rb-init"))
        self.assertEqual(resp.status_code, 409)
        self.assertIn("不可回退", resp.json()["detail"])

        self._submit_intent(pid, entity_id)  # → 洽谈中
        # 洽谈中 → 招商中 是合法相邻回退
        resp = self._rollback(
            pid, self._uid("rb-adjacent"),
            target=ProjectStatus.ATTRACTING_INVESTMENT.value,
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        # 已回到招商中，再次回退被拒
        resp = self._rollback(pid, self._uid("rb-init2"))
        self.assertEqual(resp.status_code, 409)

    def test_reject_cross_stage_rollback(self):
        """已立项直接指定回退招商中属于跨级跳转，必须拒绝。"""
        pid, _ = self._project_to_established()
        resp = self._rollback(
            pid, self._uid("rb-cross-stage"),
            target=ProjectStatus.ATTRACTING_INVESTMENT.value,
        )
        self.assertEqual(resp.status_code, 409)
        self.assertIn("受控回退仅支持相邻阶段", resp.json()["detail"])
        # 被拒请求不写状态日志、项目状态不变
        self.assertEqual(self._get_status(pid), ProjectStatus.ESTABLISHED.value)
        logs = self.client.get(f"{API}/projects/{pid}/status-logs").json()
        self.assertFalse(any(l["log_kind"] == "rollback" for l in logs))

    # ---- 3. 权限 -------------------------------------------------------

    def test_unauthorized_role_forbidden_and_not_recorded(self):
        pid, _ = self._project_to_established()
        self._manual_status(pid, ProjectStatus.UNDER_CONSTRUCTION.value, "误操作")
        resp = self._rollback(pid, self._uid("rb-403"), role=STAFF)
        self.assertEqual(resp.status_code, 403)
        self.assertIn("无权发起", resp.json()["detail"])

        # 被拒绝的越权请求不写入审计表
        lst = self.client.get(
            f"{API}/projects/rollback-requests", params={"project_id": pid}
        )
        self.assertEqual(lst.status_code, 200)
        self.assertEqual(lst.json(), [])

    # ---- 4. 重复请求幂等 -----------------------------------------------

    def test_repeated_success_returns_stable_result(self):
        pid, milestones = self._project_to_established()
        self._set_milestone(milestones[0]["id"], MilestoneStatus.IN_PROGRESS.value)
        self._set_milestone(milestones[0]["id"], MilestoneStatus.COMPLETED.value)

        request_id = self._uid("idem-ok")
        r1 = self._rollback(pid, request_id)
        r2 = self._rollback(pid, request_id)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        b1, b2 = r1.json(), r2.json()
        self.assertEqual(b1, b2)

        # 只有一条回退日志（建设中→已立项）、一条请求记录
        logs = self.client.get(f"{API}/projects/{pid}/status-logs").json()
        rollback_logs = [l for l in logs if l["log_kind"] == "rollback"]
        self.assertEqual(len(rollback_logs), 1)
        records = self.client.get(
            f"{API}/projects/rollback-requests", params={"project_id": pid}
        ).json()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["request_id"], request_id)

        # 即使项目随后又被推进到建设中，重放仍返回首次的稳定结果
        self._set_milestone(milestones[1]["id"], MilestoneStatus.IN_PROGRESS.value)
        self.assertEqual(self._get_status(pid), ProjectStatus.UNDER_CONSTRUCTION.value)
        r3 = self._rollback(pid, request_id)
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3.json()["project_status"], ProjectStatus.ESTABLISHED.value)
        self.assertEqual(r3.json(), b1)

    def test_repeated_rejection_returns_stable_409(self):
        pid, milestones = self._project_to_established()
        self._set_milestone(milestones[0]["id"], MilestoneStatus.IN_PROGRESS.value)
        request_id = self._uid("idem-rej")

        r1 = self._rollback(pid, request_id)
        r2 = self._rollback(pid, request_id, role=STAFF)  # 重放不再校验角色
        self.assertEqual(r1.status_code, 409)
        self.assertEqual(r2.status_code, 409)
        self.assertEqual(r1.json(), r2.json())
        self.assertEqual(
            len(self.client.get(
                f"{API}/projects/rollback-requests", params={"project_id": pid}
            ).json()),
            1,
        )

    def test_request_id_cross_project_conflict(self):
        pid1, ms1 = self._project_to_established()
        self._set_milestone(ms1[0]["id"], MilestoneStatus.IN_PROGRESS.value)
        self._set_milestone(ms1[0]["id"], MilestoneStatus.COMPLETED.value)
        pid2, _ = self._project_to_established()
        self._manual_status(pid2, ProjectStatus.UNDER_CONSTRUCTION.value, "误操作")

        request_id = self._uid("idem-cross")
        ok = self._rollback(pid1, request_id)
        self.assertEqual(ok.status_code, 200)
        conflict = self._rollback(pid2, request_id)
        self.assertEqual(conflict.status_code, 409)
        self.assertIn("request_id 已被其他项目", conflict.json()["detail"])

    # ---- 5. 审计查询 ---------------------------------------------------

    def test_audit_query_endpoints(self):
        pid, milestones = self._project_to_established()
        self._set_milestone(milestones[0]["id"], MilestoneStatus.IN_PROGRESS.value)
        self._set_milestone(milestones[0]["id"], MilestoneStatus.COMPLETED.value)
        ok_id = self._uid("audit-ok")
        self.assertEqual(self._rollback(pid, ok_id).status_code, 200)

        pid2, ms2 = self._project_to_established()
        self._set_milestone(ms2[0]["id"], MilestoneStatus.IN_PROGRESS.value)
        rej_id = self._uid("audit-rej")
        self.assertEqual(self._rollback(pid2, rej_id).status_code, 409)

        # 明细查询
        detail = self.client.get(f"{API}/projects/rollback-requests/{ok_id}")
        self.assertEqual(detail.status_code, 200)
        d = detail.json()
        self.assertEqual(d["result"], "applied")
        self.assertEqual(d["operator"], "王主管")
        self.assertEqual(d["operator_role"], SUPERVISOR)
        self.assertEqual(d["from_status"], ProjectStatus.UNDER_CONSTRUCTION.value)
        self.assertEqual(d["to_status"], ProjectStatus.ESTABLISHED.value)
        self.assertIn("误推进", d["reason"])
        self.assertIsNotNone(d["status_log_id"])
        self.assertTrue(any(r["type"] == "approval" for r in d["affected_records"]))

        missing = self.client.get(f"{API}/projects/rollback-requests/不存在的id")
        self.assertEqual(missing.status_code, 404)

        # 列表 + 过滤
        applied = self.client.get(
            f"{API}/projects/rollback-requests", params={"result": "applied"}
        ).json()
        self.assertTrue(any(r["request_id"] == ok_id for r in applied))
        self.assertTrue(all(r["result"] == "applied" for r in applied))

        rejected = self.client.get(
            f"{API}/projects/rollback-requests",
            params={"project_id": pid2, "result": "rejected"},
        ).json()
        self.assertEqual([r["request_id"] for r in rejected], [rej_id])

        # 状态日志：回退日志含操作人、理由、受影响记录，并与正常流转日志共存
        logs = self.client.get(f"{API}/projects/{pid}/status-logs").json()
        kinds = [l["log_kind"] for l in logs]
        self.assertIn("rollback", kinds)
        rb_log = next(l for l in logs if l["log_kind"] == "rollback")
        self.assertEqual(rb_log["request_id"], ok_id)
        self.assertEqual(rb_log["operator"], "王主管")
        self.assertEqual(rb_log["from_status"], ProjectStatus.UNDER_CONSTRUCTION.value)
        self.assertEqual(rb_log["to_status"], ProjectStatus.ESTABLISHED.value)
        self.assertIn("误推进", rb_log["reason"])
        effects = {r["effect"] for r in rb_log["affected_records"]}
        self.assertEqual(effects, {"retained"})
        # 既有自动推进日志仍标记为 normal
        self.assertIn("normal", kinds)

    # ---- 6. 与现有状态模型一致：正向推进与统计不受影响 -------------------

    def test_existing_forward_flow_unchanged(self):
        pid, milestones = self._project_to_established()
        self.assertEqual(self._get_status(pid), ProjectStatus.ESTABLISHED.value)
        self._set_milestone(milestones[0]["id"], MilestoneStatus.IN_PROGRESS.value)
        self.assertEqual(self._get_status(pid), ProjectStatus.UNDER_CONSTRUCTION.value)
        for m in milestones:
            self._set_milestone(m["id"], MilestoneStatus.IN_PROGRESS.value)
            self._set_milestone(m["id"], MilestoneStatus.COMPLETED.value)
        self.assertEqual(self._get_status(pid), ProjectStatus.COMMISSIONED.value)

        stats = self.client.get(f"{API}/statistics/overview").json()
        self.assertGreaterEqual(stats["commissioned_count"], 1)

    # ---- 7. 服务重启后前后状态完整可查 ----------------------------------

    def test_records_survive_service_restart(self):
        pid, milestones = self._project_to_established()
        self._set_milestone(milestones[0]["id"], MilestoneStatus.IN_PROGRESS.value)
        self._set_milestone(milestones[0]["id"], MilestoneStatus.COMPLETED.value)
        request_id = self._uid("restart")
        resp = self._rollback(pid, request_id, reason="重启前执行的受控回退")
        self.assertEqual(resp.status_code, 200)
        before = resp.json()

        # 模拟服务重启：释放连接池，用全新 engine/session 绑定同一数据库文件
        from app import database as db_module

        db_module.engine.dispose()
        new_engine = create_engine(
            os.environ["DATABASE_URL"], connect_args={"check_same_thread": False}
        )
        run_lightweight_migrations(new_engine)
        Base.metadata.create_all(bind=new_engine)
        NewSession = sessionmaker(bind=new_engine, autocommit=False, autoflush=False)

        def fresh_get_db():
            s = NewSession()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db] = fresh_get_db
        try:
            record = self.client.get(
                f"{API}/projects/rollback-requests/{request_id}"
            )
            self.assertEqual(record.status_code, 200)
            d = record.json()
            self.assertEqual(d["result"], "applied")
            self.assertEqual(d["from_status"], before["from_status"])
            self.assertEqual(d["to_status"], before["to_status"])
            self.assertEqual(d["reason"], "重启前执行的受控回退")

            # 项目当前状态与完整前后状态链均可查
            self.assertEqual(self._get_status(pid), ProjectStatus.ESTABLISHED.value)
            logs = self.client.get(f"{API}/projects/{pid}/status-logs").json()
            chain = [
                (l["from_status"], l["to_status"], l["log_kind"])
                for l in reversed(logs)
            ]
            self.assertIn(
                (
                    ProjectStatus.UNDER_CONSTRUCTION.value,
                    ProjectStatus.ESTABLISHED.value,
                    "rollback",
                ),
                chain,
            )
        finally:
            app.dependency_overrides.clear()
            new_engine.dispose()

    # ---- 辅助 ----------------------------------------------------------

    def _get_status(self, project_id):
        resp = self.client.get(f"{API}/projects/{project_id}")
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()["status"]

    def _update_milestone_direct(self, milestone_id, status):
        """绕过接口直接改库，用于构造接口正常流程无法产生的异常历史数据。"""
        from app import database as db_module

        session = db_module.SessionLocal()
        try:
            m = session.get(models.ProjectMilestone, milestone_id)
            m.status = status
            session.commit()
        finally:
            session.close()


class LightweightMigrationTests(unittest.TestCase):
    """旧库（无回退审计列）启动时应幂等补齐新列。"""

    def test_adds_columns_to_legacy_table(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        url = f"sqlite:///{path}"
        engine = create_engine(url)
        with engine.begin() as conn:
            # 按旧模型建状态日志表
            conn.exec_driver_sql(
                """
                CREATE TABLE project_status_logs (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    from_status VARCHAR(16),
                    to_status VARCHAR(16) NOT NULL,
                    changed_at DATETIME,
                    operator VARCHAR(64),
                    reason VARCHAR(512),
                    remarks TEXT
                )
                """
            )
            conn.exec_driver_sql(
                "INSERT INTO project_status_logs "
                "(id, project_id, from_status, to_status, operator) "
                "VALUES (1, 99, '洽谈中', '已立项', '历史操作人')"
            )

        run_lightweight_migrations(engine)
        # 再跑一次确认幂等
        run_lightweight_migrations(engine)

        with engine.begin() as conn:
            cols = {
                row[1]
                for row in conn.exec_driver_sql(
                    "PRAGMA table_info(project_status_logs)"
                ).fetchall()
            }
            self.assertIn("log_kind", cols)
            self.assertIn("request_id", cols)
            self.assertIn("affected_records", cols)
            row = conn.exec_driver_sql(
                "SELECT log_kind, operator FROM project_status_logs WHERE id = 1"
            ).fetchone()
            self.assertEqual(row[0], "normal")
            self.assertEqual(row[1], "历史操作人")
        engine.dispose()
        os.unlink(path)


if __name__ == "__main__":
    unittest.main()
