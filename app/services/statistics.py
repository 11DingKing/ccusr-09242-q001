from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Tuple

from .. import models
from ..enums import ProjectStatus, ProcessingCategory


PROJECT_STATUS_FIELD_MAP = {
    ProjectStatus.ATTRACTING_INVESTMENT: "attracting_investment_count",
    ProjectStatus.NEGOTIATING: "negotiating_count",
    ProjectStatus.ESTABLISHED: "established_count",
    ProjectStatus.UNDER_CONSTRUCTION: "under_construction_count",
    ProjectStatus.COMMISSIONED: "commissioned_count",
}

PARK_STATUS_FIELD_MAP = {
    ProjectStatus.ATTRACTING_INVESTMENT: "attracting_projects",
    ProjectStatus.NEGOTIATING: "negotiating_projects",
    ProjectStatus.ESTABLISHED: "established_projects",
    ProjectStatus.UNDER_CONSTRUCTION: "under_construction_projects",
    ProjectStatus.COMMISSIONED: "commissioned_projects",
}


def _round2(value: float) -> float:
    return round(value or 0.0, 2)


def _calc_commission_rate(
    established: int,
    under_construction: int,
    commissioned: int,
) -> float:
    denominator = established + under_construction + commissioned
    if denominator <= 0:
        return 0.0
    return _round2((commissioned / denominator) * 100.0)


def _get_promised_monthly_capacity(project: models.Project) -> float:
    if project.promised_monthly_capacity_tonnes:
        return project.promised_monthly_capacity_tonnes
    if project.expected_annual_capacity_tonnes:
        return project.expected_annual_capacity_tonnes / 12.0
    return 0.0


def _get_latest_capacity_report(
    project: models.Project,
) -> Optional[models.MonthlyCapacityReport]:
    reports = project.capacity_reports or []
    if not reports:
        return None
    return max(reports, key=lambda r: (r.report_year, r.report_month))


def count_projects_by_status(projects: List[models.Project]) -> Dict[str, int]:
    counts = {field: 0 for field in PROJECT_STATUS_FIELD_MAP.values()}
    for p in projects:
        field = PROJECT_STATUS_FIELD_MAP.get(p.status)
        if field:
            counts[field] += 1
    return counts


def sum_project_financials(
    projects: List[models.Project],
) -> Dict[str, float]:
    totals = {
        "total_planned_investment_10k": 0.0,
        "total_agreed_investment_10k": 0.0,
        "total_expected_output_value_10k": 0.0,
        "total_expected_jobs": 0,
    }
    for p in projects:
        totals["total_planned_investment_10k"] += p.planned_investment_10k or 0.0
        if p.approval:
            totals["total_agreed_investment_10k"] += (
                p.approval.agreed_investment_10k or 0.0
            )
        totals["total_expected_output_value_10k"] += (
            p.expected_output_value_10k or 0.0
        )
        totals["total_expected_jobs"] += p.expected_jobs or 0
    return totals


def aggregate_park_statistics(
    parks: List[models.IndustrialPark],
    projects: List[models.Project],
) -> List[Dict[str, Any]]:
    result = []
    for park in parks:
        park_projects = [p for p in projects if p.park_id == park.id]
        status_counts = {
            PARK_STATUS_FIELD_MAP[s]: 0
            for s in PARK_STATUS_FIELD_MAP
        }
        agreed = 0.0
        planned = 0.0
        est_count = 0
        uc_count = 0
        com_count = 0

        for p in park_projects:
            park_field = PARK_STATUS_FIELD_MAP.get(p.status)
            if park_field:
                status_counts[park_field] += 1
            if p.status == ProjectStatus.ESTABLISHED:
                est_count += 1
            elif p.status == ProjectStatus.UNDER_CONSTRUCTION:
                uc_count += 1
            elif p.status == ProjectStatus.COMMISSIONED:
                com_count += 1
            if p.approval:
                agreed += p.approval.agreed_investment_10k or 0.0
            planned += p.planned_investment_10k or 0.0

        result.append(
            {
                "park_id": park.id,
                "park_name": park.name,
                "park_type": park.park_type,
                "total_projects": len(park_projects),
                **status_counts,
                "total_agreed_investment_10k": _round2(agreed),
                "total_planned_investment_10k": _round2(planned),
                "commission_rate": _calc_commission_rate(
                    est_count, uc_count, com_count
                ),
            }
        )
    return result


def aggregate_category_statistics(
    projects: List[models.Project],
) -> List[Dict[str, Any]]:
    cat_map: Dict[ProcessingCategory, Dict[str, Any]] = {}
    for p in projects:
        for c in p.categories:
            key = c.category
            if key not in cat_map:
                cat_map[key] = {
                    "category": key,
                    "project_count": 0,
                    "total_investment_10k": 0.0,
                    "total_capacity_tonnes": 0.0,
                }
            cat_map[key]["project_count"] += 1
            cat_map[key]["total_investment_10k"] += p.planned_investment_10k or 0.0
            cat_map[key]["total_capacity_tonnes"] += (
                p.expected_annual_capacity_tonnes or 0.0
            )

    return [
        {
            "category": v["category"],
            "project_count": v["project_count"],
            "total_investment_10k": _round2(v["total_investment_10k"]),
            "total_capacity_tonnes": _round2(v["total_capacity_tonnes"]),
        }
        for v in cat_map.values()
    ]


def get_overall_statistics(db: Session) -> Dict[str, Any]:
    projects = db.query(models.Project).all()
    parks = db.query(models.IndustrialPark).all()

    status_counts = count_projects_by_status(projects)
    financials = sum_project_financials(projects)

    commission_rate = _calc_commission_rate(
        status_counts["established_count"],
        status_counts["under_construction_count"],
        status_counts["commissioned_count"],
    )

    parks_stats = aggregate_park_statistics(parks, projects)
    categories_stats = aggregate_category_statistics(projects)

    return {
        "total_projects": len(projects),
        **status_counts,
        "total_planned_investment_10k": _round2(
            financials["total_planned_investment_10k"]
        ),
        "total_agreed_investment_10k": _round2(
            financials["total_agreed_investment_10k"]
        ),
        "total_expected_output_value_10k": _round2(
            financials["total_expected_output_value_10k"]
        ),
        "total_expected_jobs": financials["total_expected_jobs"],
        "commission_rate": commission_rate,
        "parks": parks_stats,
        "categories": categories_stats,
    }


def _aggregate_park_capacity_stats(
    commissioned_projects: List[models.Project],
) -> Tuple[Dict[int, Dict[str, Any]], List[float]]:
    park_map: Dict[int, Dict[str, Any]] = {}
    overall_rates: List[float] = []

    for p in commissioned_projects:
        if not p.park:
            continue
        promised = _get_promised_monthly_capacity(p)
        latest = _get_latest_capacity_report(p)
        actual = latest.actual_output_tonnes if latest else 0.0
        procurement = latest.local_material_procurement_10k if latest else 0.0

        pid = p.park.id
        if pid not in park_map:
            park_map[pid] = {
                "park_id": pid,
                "park_name": p.park.name,
                "park_type": p.park.park_type,
                "commissioned_projects": 0,
                "reporting_projects": 0,
                "total_promised_capacity_tonnes": 0.0,
                "total_actual_output_tonnes": 0.0,
                "_utilization_rates": [],
                "total_local_procurement_10k": 0.0,
            }

        park_map[pid]["commissioned_projects"] += 1
        park_map[pid]["total_promised_capacity_tonnes"] += promised
        park_map[pid]["total_actual_output_tonnes"] += actual
        park_map[pid]["total_local_procurement_10k"] += procurement or 0.0
        if latest:
            park_map[pid]["reporting_projects"] += 1
            if promised > 0:
                rate = (actual / promised) * 100
                park_map[pid]["_utilization_rates"].append(rate)
                overall_rates.append(rate)

    return park_map, overall_rates


def _aggregate_category_capacity_stats(
    commissioned_projects: List[models.Project],
) -> Dict[ProcessingCategory, Dict[str, Any]]:
    category_map: Dict[ProcessingCategory, Dict[str, Any]] = {}

    for p in commissioned_projects:
        promised = _get_promised_monthly_capacity(p)
        latest = _get_latest_capacity_report(p)
        actual = latest.actual_output_tonnes if latest else 0.0
        procurement = latest.local_material_procurement_10k if latest else 0.0

        for c in p.categories:
            cat = c.category
            if cat not in category_map:
                category_map[cat] = {
                    "category": cat,
                    "project_count": 0,
                    "total_promised_capacity_tonnes": 0.0,
                    "total_actual_output_tonnes": 0.0,
                    "_utilization_rates": [],
                    "total_local_procurement_10k": 0.0,
                }
            category_map[cat]["project_count"] += 1
            category_map[cat]["total_promised_capacity_tonnes"] += promised
            category_map[cat]["total_actual_output_tonnes"] += actual
            category_map[cat]["total_local_procurement_10k"] += procurement or 0.0
            if latest and promised > 0:
                category_map[cat]["_utilization_rates"].append(
                    (actual / promised) * 100
                )

    return category_map


def _finalize_capacity_group_stats(
    raw_map: Dict[Any, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    result = []
    for v in raw_map.values():
        rates = v.pop("_utilization_rates")
        avg_rate = _round2(sum(rates) / len(rates)) if rates else 0.0
        result.append(
            {
                **v,
                "average_utilization_rate": avg_rate,
                "total_promised_capacity_tonnes": _round2(
                    v["total_promised_capacity_tonnes"]
                ),
                "total_actual_output_tonnes": _round2(
                    v["total_actual_output_tonnes"]
                ),
                "total_local_procurement_10k": _round2(
                    v["total_local_procurement_10k"]
                ),
            }
        )
    return result


def get_capacity_overview_statistics(db: Session) -> Dict[str, Any]:
    from sqlalchemy.orm import joinedload

    commissioned_projects = (
        db.query(models.Project)
        .options(
            joinedload(models.Project.park),
            joinedload(models.Project.categories),
            joinedload(models.Project.capacity_reports),
        )
        .filter(models.Project.status == ProjectStatus.COMMISSIONED)
        .all()
    )

    total_promised = 0.0
    total_actual = 0.0
    total_procurement = 0.0
    reporting_count = 0

    for p in commissioned_projects:
        promised = _get_promised_monthly_capacity(p)
        latest = _get_latest_capacity_report(p)
        actual = latest.actual_output_tonnes if latest else 0.0
        procurement = latest.local_material_procurement_10k if latest else 0.0

        total_promised += promised
        total_actual += actual
        total_procurement += procurement or 0.0
        if latest:
            reporting_count += 1

    park_map, _ = _aggregate_park_capacity_stats(commissioned_projects)
    category_map = _aggregate_category_capacity_stats(commissioned_projects)

    parks_stats = _finalize_capacity_group_stats(park_map)
    categories_stats = _finalize_capacity_group_stats(category_map)

    overall_rate = (
        _round2((total_actual / total_promised) * 100) if total_promised > 0 else 0.0
    )

    return {
        "total_commissioned_projects": len(commissioned_projects),
        "total_reporting_projects": reporting_count,
        "total_promised_capacity_tonnes": _round2(total_promised),
        "total_actual_output_tonnes": _round2(total_actual),
        "overall_utilization_rate": overall_rate,
        "total_local_procurement_10k": _round2(total_procurement),
        "parks": parks_stats,
        "categories": categories_stats,
    }


def get_project_capacity_curve_data(
    project: models.Project,
) -> Dict[str, Any]:
    promised = _get_promised_monthly_capacity(project)
    reports = project.capacity_reports or []

    curve = []
    for r in reports:
        utilization = r.capacity_utilization_rate
        if utilization is None and promised > 0:
            utilization = _round2((r.actual_output_tonnes / promised) * 100)
        curve.append(
            {
                "period": f"{r.report_year}-{r.report_month:02d}",
                "year": r.report_year,
                "month": r.report_month,
                "promised_capacity_tonnes": _round2(promised),
                "actual_output_tonnes": _round2(r.actual_output_tonnes),
                "utilization_rate": _round2(utilization or 0.0),
            }
        )

    curve.sort(key=lambda x: (x["year"], x["month"]))

    return {
        "project_id": project.id,
        "project_name": project.name,
        "promised_monthly_capacity_tonnes": (
            _round2(promised) if promised > 0 else None
        ),
        "curve": curve,
    }
