import urllib.request
import json

BASE = "http://127.0.0.1:8000"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return json.loads(r.read().decode())


def section(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


section("1. 健康检查")
r = get("/")
print(json.dumps(r, ensure_ascii=False, indent=2))

section("2. 合作项目（7个）")
r = get("/api/v1/projects")
print(f"共 {len(r)} 个项目：")
for p in r:
    print(f"  ✦ [{p['status']:>6}] {p['name']}")
    print(f"       投资: {p['planned_investment_10k']:>10.0f} 万元 | 园区: {p['park_name']}")

section("3. 合作主体（东盟5 + 广西3）")
r = get("/api/v1/entities")
print(f"共 {len(r)} 个主体：")
for e in r:
    print(f"  ✦ [{e['region']}] {e['name']}")
    print(f"       {e['country_or_province']} | 联系人: {e['contact_person']}")

section("4. 产业园区（5个）")
r = get("/api/v1/parks")
print(f"共 {len(r)} 个园区：")
for p in r:
    print(f"  ✦ [{p['park_type']}] {p['name']}")
    print(f"       {p['city']} | 面积: {p['total_area_km2']} km²")

section("5. 在谈合作意向（含多轮洽谈）")
r = get("/api/v1/workflow/intents?status=%E6%B4%BD%E8%B0%88%E4%B8%AD")
print(f"共 {len(r)} 份在谈意向：")
for it in r:
    print(f"  ✦ 项目: {it['project_name']}")
    print(f"       {it['submitter_name']} → {it['counterparty_name'] or '(待定)'}")
    print(f"       拟投资: {it['proposed_investment_10k']}万元 | 状态: {it['status']}")
    detail = get(f"/api/v1/workflow/intents/{it['id']}")
    print(f"       洽谈记录: 共 {len(detail['negotiations'])} 轮")
    for n in detail['negotiations']:
        held = n['held_at'][:10]
        cons = (n['consensus'] or '（空）').replace('\n', ' ')[:50]
        print(f"         · 第{n['round']}轮 [{held}] {n['title']}")
        print(f"           共识摘要: {cons}...")

section("6. 立项项目里程碑（猫山王 / 火龙果 / 菠萝蜜）")
for pid in [3, 4, 5]:
    proj = get(f"/api/v1/projects/{pid}")
    ms = get(f"/api/v1/workflow/projects/{pid}/milestones")
    print(f"  ✦ {proj['name']}  [{proj['status']}]")
    for m in ms:
        actual = m['actual_date'] or '--'
        print(f"     · [Step{m['sequence']}] {m['name']:>12} | 计划:{m['planned_date']} | 实际:{actual} | [{m['status']}] 进度{m['completion_rate']}%")

section("7. 统计总览")
r = get("/api/v1/statistics/overview")
print(f"项目总数: {r['total_projects']}")
print(f"状态分布: 招商中 {r['attracting_investment_count']} | 洽谈中 {r['negotiating_count']} | 已立项 {r['established_count']} | 建设中 {r['under_construction_count']} | 已投产 {r['commissioned_count']}")
print(f"规划投资总额: {r['total_planned_investment_10k']:,.0f} 万元")
print(f"协议投资总额: {r['total_agreed_investment_10k']:,.0f} 万元")
print(f"预期年产值:   {r['total_expected_output_value_10k']:,.0f} 万元")
print(f"预期就业岗位: {r['total_expected_jobs']} 人")
print(f"整体投产率:   {r['commission_rate']}%")

print()
print("-- 各园区落地统计 --")
for s in r['parks']:
    print(f"  ✦ {s['park_name']} [{s['park_type']}]")
    print(f"      总项目{s['total_projects']:>2} (招商{s['attracting_projects']}洽谈{s['negotiating_projects']}立项{s['established_projects']}建设{s['under_construction_projects']}投产{s['commissioned_projects']})")
    print(f"      协议投资 {s['total_agreed_investment_10k']:>10,.0f} 万 | 投产率 {s['commission_rate']}%")

print()
print("-- 各加工品类项目分布 --")
for c in r['categories']:
    print(f"  ✦ {c['category']:<12} | {c['project_count']:>2}个项目 | 投资 {c['total_investment_10k']:>10,.0f}万 | 年产能 {c['total_capacity_tonnes']:>10,.0f} 吨")

section("8. 项目状态流转日志（椰子项目示例）")
logs = get("/api/v1/projects/1/status-logs")
for lg in logs:
    fs = lg['from_status'] or '(始)'
    print(f"  [{lg['changed_at'][:16]}] {fs:>6} → {lg['to_status']:<6} | {lg['reason']}")

print()
print("=" * 60)
print("  ✅ 所有接口验证通过！服务运行正常。")
print("=" * 60)
