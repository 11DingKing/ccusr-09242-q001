import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from app.database import Base, engine, SessionLocal
from app import models
from app.enums import (
    Region,
    ProcessingCategory,
    ProjectStatus,
    ParkType,
    IntentStatus,
    MilestoneStatus,
    MilestoneType,
)


def seed_all():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        print("🌱 开始植入示例数据 ...")

        pingxiang_border_port_park = models.IndustrialPark(
            name="广西凭祥沿边临港产业园",
            park_type=ParkType.BORDER_PORT,
            city="崇左市",
            district="凭祥市",
            total_area_km2=15.8,
            developed_area_km2=8.2,
            pillar_industries="水果加工、跨境物流、东盟特色产品加工",
            preferential_policies="享受西部大开发、自贸试验区、边合区多重叠加政策；企业所得税减按9%征收；进口设备免税",
            infrastructure="已实现七通一平；配套冷链物流园、专用码头、标准厂房12万㎡",
            contact_person="李建明",
            contact_phone="0771-8520001",
            address="广西凭祥市南山工业园",
            description="面向东盟的水果进口加工核心园区，年进口水果吞吐量200万吨",
        )
        qinfang_collab_park = models.IndustrialPark(
            name="钦防协作园（防城港片区）",
            park_type=ParkType.QINFANG_COLLABORATION,
            city="防城港市",
            district="港口区",
            total_area_km2=22.5,
            developed_area_km2=13.6,
            pillar_industries="食品深加工、冷链仓储、港口物流",
            preferential_policies="北部湾经济区优惠政策；工业用地基准价优惠30%；固投补贴最高200万元",
            infrastructure="毗邻防城港保税港；自有万吨级冷链专用泊位；标准化厂房20万㎡",
            contact_person="黄涛",
            contact_phone="0770-2880088",
            address="广西防城港市港口区企沙工业区",
            description="钦州-防城港一体化发展平台，重点布局水果精深加工及出口基地",
        )
        nanning_ftz_park = models.IndustrialPark(
            name="中国（广西）自由贸易试验区南宁片区",
            park_type=ParkType.FREE_TRADE,
            city="南宁市",
            district="良庆区",
            total_area_km2=46.8,
            developed_area_km2=28.0,
            pillar_industries="跨境电商、食品加工、数字经济、现代金融",
            preferential_policies="自贸试验区政策；跨境人民币结算便利化；高端人才个税补贴",
            infrastructure="五象新区核心区；多式联运枢纽；南宁综合保税区联动",
            contact_person="韦华",
            contact_phone="0771-4300001",
            address="广西南宁市良庆区五象大道",
            description="面向东盟的总部经济和高端加工集聚区",
        )
        dongxing_border_eco_park = models.IndustrialPark(
            name="东兴边境经济合作区",
            park_type=ParkType.BORDER_ECONOMIC_COOPERATION,
            city="防城港市",
            district="东兴市",
            total_area_km2=10.2,
            developed_area_km2=6.5,
            pillar_industries="边境贸易、水果加工、互市商品落地加工",
            preferential_policies="边合区政策；互市进口商品免征关税；加工贸易内销选择性征税",
            infrastructure="中越二桥互联互通；互市贸易区；跨境冷链查验场",
            contact_person="陈世军",
            contact_phone="0770-7680001",
            address="广西防城港市东兴市大坪路",
            description="中越边境最大的水果落地加工基地",
        )
        beihai_comprehensive_bonded_park = models.IndustrialPark(
            name="广西北海综合保税区",
            park_type=ParkType.COMPREHENSIVE_BONDED,
            city="北海市",
            district="海城区",
            total_area_km2=8.6,
            developed_area_km2=5.1,
            pillar_industries="保税加工、保税物流、跨境电商",
            preferential_policies="综保区政策；入区退税；区内交易免增值税",
            infrastructure="保税仓储30万㎡；监管货场；跨境电商分拣中心",
            contact_person="张海燕",
            contact_phone="0779-2090001",
            address="广西北海市海城区工业园区",
            description="适合果汁出口加工、保税仓分装业务",
        )
        all_parks = [
            pingxiang_border_port_park,
            qinfang_collab_park,
            nanning_ftz_park,
            dongxing_border_eco_park,
            beihai_comprehensive_bonded_park,
        ]
        db.add_all(all_parks)
        db.flush()
        print(f"  ✔ 园区 {len(all_parks)} 个")

        thai_rachada_coconut = models.Entity(
            name="泰国甲米拉差达椰子制品有限公司",
            region=Region.ASSOCIATION_SOUTH_EAST_ASIAN_NATIONS,
            country_or_province="泰国",
            city="甲米府",
            contact_person="Somchai Srivikorn",
            contact_phone="+66-86-2345678",
            contact_email="somchai@rachada-coconut.co.th",
            address="123 Moo 5, Amphur Muang, Krabi 81000",
            description="泰国南部最大的椰子初加工企业，拥有自有椰林3万亩，合作农户500余家",
            registered_capital=200000.0,
            established_year=2008,
            capabilities=[
                models.EntityCapability(
                    category=ProcessingCategory.COCONUT,
                    annual_capacity_tonnes=120000,
                    capacity_unit="吨/年",
                    production_lines=6,
                    key_products="椰青、椰肉、椰浆、椰壳炭",
                    certifications="HACCP, ISO22000, BRC, 有机认证",
                ),
            ],
        )
        thai_siam_juice = models.Entity(
            name="泰国暹罗热带果汁股份有限公司",
            region=Region.ASSOCIATION_SOUTH_EAST_ASIAN_NATIONS,
            country_or_province="泰国",
            city="曼谷",
            contact_person="Nitipong Viravan",
            contact_phone="+66-2-1234567",
            contact_email="nitipong@siamtropicaljuice.com",
            address="888 Rama IV Road, Bangkok 10110",
            description="泰国上市果汁企业，旗下12家工厂覆盖榴莲、芒果、山竹等热带水果NFC及浓缩汁",
            registered_capital=850000.0,
            established_year=1999,
            capabilities=[
                models.EntityCapability(
                    category=ProcessingCategory.FRUIT_JUICE,
                    annual_capacity_tonnes=250000,
                    capacity_unit="吨/年",
                    production_lines=18,
                    key_products="NFC果汁、浓缩果汁、果泥",
                    certifications="FDA, HACCP, ISO9001, SGF",
                ),
                models.EntityCapability(
                    category=ProcessingCategory.DURIAN,
                    annual_capacity_tonnes=35000,
                    capacity_unit="吨/年",
                    production_lines=4,
                    key_products="金枕榴莲冷冻果肉、榴莲泥、冻干榴莲",
                    certifications="中国海关准入GACC企业",
                ),
                models.EntityCapability(
                    category=ProcessingCategory.MANGO,
                    annual_capacity_tonnes=60000,
                    capacity_unit="吨/年",
                    production_lines=5,
                    key_products="芒果浓缩汁、芒果干、芒果酱",
                    certifications="BRC, Halal, Kosher",
                ),
            ],
        )
        malaysia_musang_king = models.Entity(
            name="马来西亚猫山王农业科技集团",
            region=Region.ASSOCIATION_SOUTH_EAST_ASIAN_NATIONS,
            country_or_province="马来西亚",
            city="彭亨州劳勿",
            contact_person="林敬益",
            contact_phone="+60-12-9876543",
            contact_email="lim@musangking-tech.com.my",
            address="Lot 1288, Batu 8, Jalan Tras, 27600 Raub, Pahang",
            description="拥有1500亩猫山王自有果园和液氮速冻生产线",
            registered_capital=1500000.0,
            established_year=2012,
            capabilities=[
                models.EntityCapability(
                    category=ProcessingCategory.DURIAN,
                    annual_capacity_tonnes=12000,
                    capacity_unit="吨/年",
                    production_lines=3,
                    key_products="液氮猫山王整果、冷冻榴莲果肉、榴莲浆",
                    certifications="MYGAP, Mesti, GACC准入",
                ),
                models.EntityCapability(
                    category=ProcessingCategory.FROZEN_FRUIT,
                    annual_capacity_tonnes=25000,
                    capacity_unit="吨/年",
                    production_lines=2,
                    key_products="液氮速冻热带水果",
                    certifications="HACCP",
                ),
            ],
        )
        vietnam_binhphuoc_dragon = models.Entity(
            name="越南平福火龙果联合合作社",
            region=Region.ASSOCIATION_SOUTH_EAST_ASIAN_NATIONS,
            country_or_province="越南",
            city="平福省",
            contact_person="Nguyễn Văn Hùng",
            contact_phone="+84-908-111222",
            contact_email="hung@binhphuoc-dragonfruit.vn",
            address="Tỉnh Bình Phước, Huyện Đồng Xoài",
            description="越南平福省7县联合合作社，火龙果种植面积2.8万亩",
            registered_capital=50000.0,
            established_year=2015,
            capabilities=[
                models.EntityCapability(
                    category=ProcessingCategory.DRAGON_FRUIT,
                    annual_capacity_tonnes=180000,
                    capacity_unit="吨/年",
                    production_lines=5,
                    key_products="鲜火龙果、冷冻火龙果、火龙果干、火龙果粉",
                    certifications="GLOBALGAP, VietGAP, GACC准入",
                ),
            ],
        )
        indonesia_jackfruit_food = models.Entity(
            name="印尼波罗蜜食品加工有限公司",
            region=Region.ASSOCIATION_SOUTH_EAST_ASIAN_NATIONS,
            country_or_province="印度尼西亚",
            city="中爪哇三宝垄",
            contact_person="Budi Santoso",
            contact_phone="+62-812-3334444",
            contact_email="budi@jackfruit-indo.id",
            address="Jl. Raya Semarang-Solo KM. 15, Semarang, Jawa Tengah",
            description="印尼最大的菠萝蜜加工企业，产品出口中日韩美澳",
            registered_capital=300000.0,
            established_year=2010,
            capabilities=[
                models.EntityCapability(
                    category=ProcessingCategory.JACKFRUIT,
                    annual_capacity_tonnes=45000,
                    capacity_unit="吨/年",
                    production_lines=4,
                    key_products="冷冻菠萝蜜、菠萝蜜干、菠萝蜜果脯",
                    certifications="HACCP, ISO22000, BPOM",
                ),
            ],
        )
        guangxi_nongken = models.Entity(
            name="广西农垦集团食品加工有限公司",
            region=Region.GUANGXI,
            country_or_province="广西壮族自治区",
            city="南宁市",
            contact_person="周建国",
            contact_phone="0771-2850001",
            contact_email="zhoujianguo@gxnk.com",
            address="广西南宁市民族大道32号农垦大厦",
            description="广西区直大型国有食品加工企业，布局全区水果加工、冷链、销售网络",
            registered_capital=120000.0,
            established_year=1996,
            capabilities=[
                models.EntityCapability(
                    category=ProcessingCategory.CANNED_FRUIT,
                    annual_capacity_tonnes=80000,
                    capacity_unit="吨/年",
                    production_lines=10,
                    key_products="菠萝罐头、荔枝罐头、龙眼罐头",
                    certifications="HACCP, BRC, IFS",
                ),
                models.EntityCapability(
                    category=ProcessingCategory.FRUIT_JUICE,
                    annual_capacity_tonnes=50000,
                    capacity_unit="吨/年",
                    production_lines=4,
                    key_products="荔枝汁、龙眼汁、百香果汁",
                    certifications="ISO9001, ISO22000",
                ),
                models.EntityCapability(
                    category=ProcessingCategory.DRIED_FRUIT,
                    annual_capacity_tonnes=25000,
                    capacity_unit="吨/年",
                    production_lines=6,
                    key_products="芒果干、火龙果干、桂圆肉",
                    certifications="SC认证, 绿色食品",
                ),
            ],
        )
        guangxi_huayin = models.Entity(
            name="广西华银水果深加工有限公司",
            region=Region.GUANGXI,
            country_or_province="广西壮族自治区",
            city="钦州市",
            contact_person="陈志华",
            contact_phone="0777-5880088",
            contact_email="chenzhihua@gxhuayin.com",
            address="广西钦州市钦南区皇马工业园",
            description="广西本土民营龙头，专注热带水果精深加工和冷链出口",
            registered_capital=50000.0,
            established_year=2013,
            capabilities=[
                models.EntityCapability(
                    category=ProcessingCategory.FROZEN_FRUIT,
                    annual_capacity_tonnes=60000,
                    capacity_unit="吨/年",
                    production_lines=5,
                    key_products="冷冻榴莲果肉、冷冻芒果块、冷冻火龙果丁",
                    certifications="SC, HACCP, 出口食品生产备案",
                ),
                models.EntityCapability(
                    category=ProcessingCategory.JAM,
                    annual_capacity_tonnes=15000,
                    capacity_unit="吨/年",
                    production_lines=2,
                    key_products="百香果酱、芒果酱、菠萝酱",
                    certifications="SC, 有机认证",
                ),
            ],
        )
        beibuwan_cold_chain = models.Entity(
            name="北部湾冷链食品股份有限公司",
            region=Region.GUANGXI,
            country_or_province="广西壮族自治区",
            city="防城港市",
            contact_person="林峰",
            contact_phone="0770-2800008",
            contact_email="linfeng@bbw-cold.com",
            address="广西防城港市港口区大西南临港工业园",
            description="广西最大的临港冷链仓储加工一体化企业，库容量30万吨",
            registered_capital=80000.0,
            established_year=2017,
            capabilities=[
                models.EntityCapability(
                    category=ProcessingCategory.COCONUT,
                    annual_capacity_tonnes=30000,
                    capacity_unit="吨/年",
                    production_lines=3,
                    key_products="椰浆、椰汁、椰子水",
                    certifications="SC, HACCP",
                ),
                models.EntityCapability(
                    category=ProcessingCategory.FROZEN_FRUIT,
                    annual_capacity_tonnes=120000,
                    capacity_unit="吨/年",
                    production_lines=8,
                    key_products="全品类冷冻热带水果、分切加工",
                    certifications="SC, 出口备案, ISO9001",
                ),
            ],
        )
        all_entities = [
            thai_rachada_coconut,
            thai_siam_juice,
            malaysia_musang_king,
            vietnam_binhphuoc_dragon,
            indonesia_jackfruit_food,
            guangxi_nongken,
            guangxi_huayin,
            beibuwan_cold_chain,
        ]
        db.add_all(all_entities)
        db.flush()
        print(f"  ✔ 合作主体 {len(all_entities)} 个（东盟5家，广西3家）")

        today = date.today()

        cn_th_coconut_phase1 = models.Project(
            name="中泰椰子深加工产业园（一期）",
            project_code="FGX-2025-C001",
            status=ProjectStatus.NEGOTIATING,
            investment_direction=(
                "依托凭祥沿边临港产业园的口岸优势和中泰《关于农产品贸易与加工合作备忘录》，"
                "引进泰国椰青、椰肉原料，建设年处理20万吨椰子深加工生产线，"
                "产品为椰浆、椰子水、椰奶粉、椰壳活性炭，90%返销国内并出口日韩。"
            ),
            planned_investment_10k=85000.0,
            expected_annual_capacity_tonnes=200000,
            planned_land_area_mu=320.0,
            expected_output_value_10k=168000.0,
            expected_jobs=860,
            construction_cycle_months=18,
            park_id=pingxiang_border_port_park.id,
            initiator_id=thai_rachada_coconut.id,
            background="国内椰子市场年增长率15%，原料高度依赖东南亚进口。RCEP生效后中泰水果零关税将进一步释放产能。",
            market_analysis="预计项目达产后，年均营收16.8亿元，毛利3.6亿元，投资回收期5.6年。",
            cooperation_modes="合资经营（泰方51%/中方49%），泰方供应原料+配方+品牌授权，中方负责土地、厂房、国内渠道。",
            support_requirements="申请西部大开发税收优惠、边合区固投补贴、进口原料绿色通道、跨境人民币结算。",
            responsible_department="凭祥市投资促进局",
            project_leader="李建明",
            leader_phone="0771-8520001",
            publish_date=today - timedelta(days=60),
            categories=[
                models.ProjectCategory(
                    category=ProcessingCategory.COCONUT,
                    proportion=100.0,
                    description="椰浆40%、椰子水30%、椰奶粉15%、椰壳炭15%",
                ),
            ],
        )

        asean_juice_supply_base = models.Project(
            name="东盟热带水果果汁对华供应及分装基地",
            project_code="FGX-2025-J002",
            status=ProjectStatus.NEGOTIATING,
            investment_direction=(
                "在钦防协作园建设NFC果汁分装、浓缩果汁还原及冷链出口基地，"
                "对接泰国暹罗果汁的原料供应，直供盒马、Ole'、7-11等零售渠道；"
                "同步布局榴莲、芒果、山竹冷冻果肉分装。"
            ),
            planned_investment_10k=62000.0,
            expected_annual_capacity_tonnes=180000,
            planned_land_area_mu=260.0,
            expected_output_value_10k=125000.0,
            expected_jobs=620,
            construction_cycle_months=15,
            park_id=qinfang_collab_park.id,
            initiator_id=thai_siam_juice.id,
            background="RCEP生效后，东盟果汁进入中国关税逐年递减至零。",
            market_analysis="国内NFC果汁市场CAGR 22%，东盟热带风味差异化明显。",
            cooperation_modes="合作经营 / 品牌授权；泰方提供原料+技术，中方负责分装与渠道。",
            support_requirements="申请北部湾经济区产业扶持、综保区保税加工政策。",
            responsible_department="防城港市投资促进局",
            project_leader="黄涛",
            leader_phone="0770-2880088",
            publish_date=today - timedelta(days=45),
            categories=[
                models.ProjectCategory(category=ProcessingCategory.FRUIT_JUICE, proportion=55.0),
                models.ProjectCategory(category=ProcessingCategory.DURIAN, proportion=20.0),
                models.ProjectCategory(category=ProcessingCategory.MANGO, proportion=15.0),
                models.ProjectCategory(category=ProcessingCategory.MANGOSTEEN, proportion=10.0),
            ],
        )

        cn_my_musang_king_project = models.Project(
            name="中马猫山王榴莲深加工项目",
            project_code="FGX-2025-D003",
            status=ProjectStatus.ESTABLISHED,
            investment_direction=(
                "落地南宁自贸片区，建设马来西亚猫山王液氮整果分拨中心、果肉深加工生产线、"
                "榴莲咖啡/榴莲月饼等衍生品加工车间，打造东盟榴莲中国总部基地。"
            ),
            planned_investment_10k=48000.0,
            expected_annual_capacity_tonnes=18000,
            planned_land_area_mu=180.0,
            expected_output_value_10k=96000.0,
            expected_jobs=450,
            construction_cycle_months=14,
            park_id=nanning_ftz_park.id,
            initiator_id=malaysia_musang_king.id,
            background="猫山王D197在中国高端消费市场需求爆发式增长。",
            market_analysis="达产后年营收9.6亿元，投资回收期4.8年。",
            cooperation_modes="合资经营，合资公司马方持股60%，广西合作方持股40%。",
            support_requirements="自贸区跨境电商政策、高端人才个税优惠。",
            responsible_department="南宁片区管委会",
            project_leader="韦华",
            leader_phone="0771-4300001",
            publish_date=today - timedelta(days=120),
            categories=[
                models.ProjectCategory(category=ProcessingCategory.DURIAN, proportion=80.0),
                models.ProjectCategory(category=ProcessingCategory.FROZEN_FRUIT, proportion=20.0),
            ],
        )

        vn_dragonfruit_project = models.Project(
            name="越南火龙果深加工及出口基地",
            project_code="FGX-2025-G004",
            status=ProjectStatus.UNDER_CONSTRUCTION,
            investment_direction=(
                "在东兴边合区利用互市进口落地加工政策，建设火龙果原浆、冻干、果粉生产线，"
                "对接国内茶饮（喜茶/奈雪/蜜雪冰城）和保健品行业供应。"
            ),
            planned_investment_10k=35000.0,
            expected_annual_capacity_tonnes=120000,
            planned_land_area_mu=150.0,
            expected_output_value_10k=78000.0,
            expected_jobs=380,
            construction_cycle_months=12,
            park_id=dongxing_border_eco_park.id,
            initiator_id=vietnam_binhphuoc_dragon.id,
            background="平福省火龙果年产量超80万吨，80%出口中国。",
            market_analysis="茶饮行业对火龙果原浆年需求30万吨以上。",
            cooperation_modes="中方代加工+原料采购包销；越南合作社保障供应。",
            support_requirements="边合区互市加工政策、内销选择性征税。",
            responsible_department="东兴边合区管委会",
            project_leader="陈世军",
            leader_phone="0770-7680001",
            publish_date=today - timedelta(days=180),
            categories=[
                models.ProjectCategory(category=ProcessingCategory.DRAGON_FRUIT, proportion=65.0),
                models.ProjectCategory(category=ProcessingCategory.FRUIT_JUICE, proportion=20.0),
                models.ProjectCategory(category=ProcessingCategory.DRIED_FRUIT, proportion=15.0),
            ],
        )

        id_jackfruit_project = models.Project(
            name="印尼菠萝蜜进口分装与果干加工项目",
            project_code="FGX-2025-J005",
            status=ProjectStatus.COMMISSIONED,
            investment_direction=(
                "北海综保区保税加工+出口复进口，年处理菠萝蜜5万吨，生产冷冻果块、果干、脆片。"
            ),
            planned_investment_10k=22000.0,
            expected_annual_capacity_tonnes=50000,
            planned_land_area_mu=100.0,
            expected_output_value_10k=46000.0,
            expected_jobs=260,
            construction_cycle_months=10,
            park_id=beihai_comprehensive_bonded_park.id,
            initiator_id=indonesia_jackfruit_food.id,
            background="菠萝蜜是印尼五大优势水果之一。",
            market_analysis="项目已于2025年Q1正式投产，一期月均产能4000吨。",
            cooperation_modes="保税加工+国内总代。",
            support_requirements="综保区入区退税、跨境电商B2B出口。",
            responsible_department="北海综保区管委会",
            project_leader="张海燕",
            leader_phone="0779-2090001",
            publish_date=today - timedelta(days=300),
            categories=[
                models.ProjectCategory(category=ProcessingCategory.JACKFRUIT, proportion=70.0),
                models.ProjectCategory(category=ProcessingCategory.DRIED_FRUIT, proportion=20.0),
                models.ProjectCategory(category=ProcessingCategory.FROZEN_FRUIT, proportion=10.0),
            ],
        )

        gx_nongken_upgrade_project = models.Project(
            name="广西农垦热带水果综合加工升级项目",
            project_code="FGX-2025-N006",
            status=ProjectStatus.ATTRACTING_INVESTMENT,
            investment_direction=(
                "广西农垦主导，升级南宁总部+钦州基地的水果加工产线，"
                "重点引进东盟合作方共建芒果、荔枝、百香果全产业链。"
            ),
            planned_investment_10k=56000.0,
            expected_annual_capacity_tonnes=140000,
            planned_land_area_mu=240.0,
            expected_output_value_10k=95000.0,
            expected_jobs=540,
            construction_cycle_months=20,
            park_id=nanning_ftz_park.id,
            initiator_id=guangxi_nongken.id,
            background="广西本土水果产量3000万吨+，加工率不足20%。",
            market_analysis="面向全国市场，对标三只松鼠/良品铺子代工及自有品牌。",
            cooperation_modes="寻求东盟供应商及技术合作。",
            support_requirements="自治区工业振兴专项资金。",
            responsible_department="广西农垦集团投资部",
            project_leader="周建国",
            leader_phone="0771-2850001",
            publish_date=today - timedelta(days=15),
            categories=[
                models.ProjectCategory(category=ProcessingCategory.MANGO, proportion=30.0),
                models.ProjectCategory(category=ProcessingCategory.CANNED_FRUIT, proportion=25.0),
                models.ProjectCategory(category=ProcessingCategory.FRUIT_JUICE, proportion=25.0),
                models.ProjectCategory(category=ProcessingCategory.DRIED_FRUIT, proportion=20.0),
            ],
        )

        gx_huayin_beibuwan_joint_park = models.Project(
            name="防城港华银-北部湾冷链联合加工园",
            project_code="FGX-2025-H007",
            status=ProjectStatus.ATTRACTING_INVESTMENT,
            investment_direction=(
                "广西华银+北部湾冷链合资，在钦防协作园建设东盟水果冷链+加工一体化园区，"
                "面向日韩出口速冻热带水果。"
            ),
            planned_investment_10k=72000.0,
            expected_annual_capacity_tonnes=180000,
            planned_land_area_mu=300.0,
            expected_output_value_10k=135000.0,
            expected_jobs=720,
            construction_cycle_months=18,
            park_id=qinfang_collab_park.id,
            initiator_id=guangxi_huayin.id,
            background="RCEP区域内冷链需求年增长18%。",
            market_analysis="日韩市场速冻榴莲、芒果、菠萝蜜年进口额超15亿美元。",
            cooperation_modes="合资；诚招东盟原料供应商参股。",
            support_requirements="出口退税、北部湾港口绿色通道。",
            responsible_department="钦州市发改委",
            project_leader="陈志华",
            leader_phone="0777-5880088",
            publish_date=today - timedelta(days=5),
            categories=[
                models.ProjectCategory(category=ProcessingCategory.FROZEN_FRUIT, proportion=60.0),
                models.ProjectCategory(category=ProcessingCategory.COCONUT, proportion=20.0),
                models.ProjectCategory(category=ProcessingCategory.JAM, proportion=20.0),
            ],
        )

        all_projects = [
            cn_th_coconut_phase1,
            asean_juice_supply_base,
            cn_my_musang_king_project,
            vn_dragonfruit_project,
            id_jackfruit_project,
            gx_nongken_upgrade_project,
            gx_huayin_beibuwan_joint_park,
        ]
        db.add_all(all_projects)
        db.flush()
        print(f"  ✔ 合作项目 {len(all_projects)} 个（招商中2、洽谈中2、已立项1、建设中1、已投产1）")

        intent_coconut_jv = models.CooperationIntent(
            project_id=cn_th_coconut_phase1.id,
            submitter_id=beibuwan_cold_chain.id,
            counterparty_id=thai_rachada_coconut.id,
            status=IntentStatus.IN_DISCUSSION,
            cooperation_mode="合资经营（51/49）",
            proposed_investment_10k=85000.0,
            proposed_capacity_tonnes=200000,
            cooperation_content="广西北部湾冷链提供土地、厂房、冷链仓储及国内分销网络；泰国拉差达提供原料供应、加工技术、品牌授权。双方成立合资公司，泰方占股51%，中方占股49%。",
            expected_timeline="2025Q3立项，2025Q4开工，2026Q4试生产，2027Q2正式投产。",
            requirements="需要凭祥市政府协调500亩用地指标，并给予3年税收返还。",
            submitter_comments="已实地考察泰国工厂，原料供应稳定，合作意愿强烈。",
            reviewer="李建明",
            review_comments="符合园区产业定位，建议进入深度洽谈。",
            submitted_at=datetime.utcnow() - timedelta(days=40),
            reviewed_at=datetime.utcnow() - timedelta(days=35),
        )
        intent_juice_brand_license = models.CooperationIntent(
            project_id=asean_juice_supply_base.id,
            submitter_id=guangxi_nongken.id,
            counterparty_id=thai_siam_juice.id,
            status=IntentStatus.IN_DISCUSSION,
            cooperation_mode="品牌授权+代工合作",
            proposed_investment_10k=62000.0,
            proposed_capacity_tonnes=180000,
            cooperation_content="广西农垦提供分装工厂与全国经销商渠道，暹罗果汁提供浓缩原料、NFC原液及SIAM TROPICAL品牌授权，按出厂价分成。",
            expected_timeline="2025年9月签约，12月产线试产。",
            requirements="品牌使用期5年，年保底采购额不低于2亿元。",
            submitted_at=datetime.utcnow() - timedelta(days=25),
            reviewed_at=datetime.utcnow() - timedelta(days=20),
        )
        intent_durian_tech_coop = models.CooperationIntent(
            project_id=gx_nongken_upgrade_project.id,
            submitter_id=malaysia_musang_king.id,
            status=IntentStatus.REVIEWING,
            cooperation_mode="技术合作+原料供应",
            proposed_investment_10k=15000.0,
            cooperation_content="猫山王集团向广西农垦输出榴莲深加工技术，同时作为广西农垦海外优质热带水果采购供应商。",
            expected_timeline="2025Q4签署框架协议。",
            reviewer="周建国",
            submitted_at=datetime.utcnow() - timedelta(days=8),
        )
        all_intents = [
            intent_coconut_jv,
            intent_juice_brand_license,
            intent_durian_tech_coop,
        ]
        db.add_all(all_intents)
        db.flush()
        print(f"  ✔ 合作意向 {len(all_intents)} 份（评审中1、洽谈中2）")

        all_negotiations = [
            models.NegotiationRecord(
                intent_id=intent_coconut_jv.id,
                round=1,
                title="中泰椰子项目首轮商务洽谈",
                held_at=datetime.utcnow() - timedelta(days=30),
                location="广西凭祥市人民政府会议室",
                host="凭祥市投资促进局",
                participants="泰方Somchai一行5人、中方林峰一行6人、招商局2人",
                key_topics="合资股权比例、出资方式、原料供应保障、技术人员派驻、土地选址。",
                consensus="原则上同意合资公司51/49结构；选址凭祥沿边临港产业园B区320亩。",
                disagreements="对于品牌授权费计提比例，泰方提出营收的3%，中方期望不超过1.5%。",
                next_steps="双方各自内部评估授权费率；中方出具土地测绘报告。",
                next_meeting_date=today - timedelta(days=18),
                minutes_author="黄秘书",
            ),
            models.NegotiationRecord(
                intent_id=intent_coconut_jv.id,
                round=2,
                title="中泰椰子项目第二轮洽谈（含实地考察）",
                held_at=datetime.utcnow() - timedelta(days=18),
                location="凭祥沿边临港产业园现场 + 园区接待中心",
                host="李建明（园区主任）",
                participants="泰方Somchai、工程部总监；中方林峰、周建国、园区工程部。",
                key_topics="厂房设计方案、水电配套、蒸汽供应、环保审批、品牌授权费折中。",
                consensus="品牌授权费按阶梯式：首年1.5%、次年2%、第三年起2.5%；"
                          "园区承诺6个月内完成土地平整及配套。",
                disagreements="环保验收周期，泰方希望不超过3个月，中方承诺最长4.5个月。",
                next_steps="出具合资公司框架协议初稿；开展尽职调查。",
                next_meeting_date=today - timedelta(days=5),
                minutes_author="李秘书",
            ),
            models.NegotiationRecord(
                intent_id=intent_coconut_jv.id,
                round=3,
                title="中泰椰子项目第三轮：合资协议条款确认",
                held_at=datetime.utcnow() - timedelta(days=5),
                location="南宁市沃顿国际大酒店",
                host="广西投资促进局东盟处",
                participants="双方法务、财务、税务顾问。",
                key_topics="合资公司章程、利润分配、退出机制、知识产权。",
                consensus="除利润汇出税务条款需法务再次核对，其他条款全部达成。",
                next_steps="法务修订后签框架协议，提交立项审批。",
                minutes_author="张秘书",
            ),
            models.NegotiationRecord(
                intent_id=intent_juice_brand_license.id,
                round=1,
                title="果汁对华供应合作首谈",
                held_at=datetime.utcnow() - timedelta(days=18),
                location="钦防协作园招商中心",
                host="黄涛（园区副主任）",
                participants="暹罗果汁Nitipong、广西农垦周建国、渠道部。",
                key_topics="品牌授权范围、原料价格、分装工艺质量标准、渠道独家性。",
                consensus="原则上同意华南（两广+海南）渠道非独家授权；质量采用BRC标准。",
                disagreements="保底采购额2亿/年偏高，农垦期望首年1.2亿，逐年递增。",
                next_steps="双方市场部门重新测算保底量；出具质量SOP对比表。",
                next_meeting_date=today - timedelta(days=2),
                minutes_author="王秘书",
            ),
        ]
        db.add_all(all_negotiations)
        db.flush()
        print(f"  ✔ 洽谈记录 {len(all_negotiations)} 条（椰子项目3轮、果汁项目1轮）")

        approval_musang_king = models.ProjectApproval(
            project_id=cn_my_musang_king_project.id,
            approval_number="NNZMQ-LD-2025-0037",
            approval_date=today - timedelta(days=80),
            approving_authority="中国（广西）自由贸易试验区南宁片区管理委员会",
            agreed_investment_10k=48000.0,
            agreed_capacity_tonnes=18000,
            agreed_land_area_mu=180.0,
            construction_start_deadline=today - timedelta(days=50),
            completion_deadline=today + timedelta(days=60),
            main_content="同意在南宁片区建设猫山王榴莲深加工项目，合资公司注册资本2000万美元。",
            approval_conditions="1. 2025年7月前完成项目备案与环评；2. 实际开工率不低于85%；3. 亩均税收不低于30万元/年。",
            approved_by="韦华",
        )
        approval_dragonfruit = models.ProjectApproval(
            project_id=vn_dragonfruit_project.id,
            approval_number="DXBHQ-2024-SG-0112",
            approval_date=today - timedelta(days=150),
            approving_authority="东兴边境经济合作区管委会",
            agreed_investment_10k=35000.0,
            agreed_capacity_tonnes=120000,
            agreed_land_area_mu=150.0,
            construction_start_deadline=today - timedelta(days=130),
            completion_deadline=today - timedelta(days=10),
            main_content="同意在东兴边合区互市加工片区建设火龙果深加工项目，享受边合区优惠政策。",
            approval_conditions="符合互市进口商品落地加工负面清单之外。",
            approved_by="陈世军",
        )
        approval_jackfruit = models.ProjectApproval(
            project_id=id_jackfruit_project.id,
            approval_number="BHCBZ-2024-PL-0058",
            approval_date=today - timedelta(days=260),
            approving_authority="北海综合保税区管委会",
            agreed_investment_10k=22000.0,
            agreed_capacity_tonnes=50000,
            agreed_land_area_mu=100.0,
            construction_start_deadline=today - timedelta(days=240),
            completion_deadline=today - timedelta(days=90),
            main_content="同意北海综保区保税加工项目立项。",
            approved_by="张海燕",
        )
        all_approvals = [
            approval_musang_king,
            approval_dragonfruit,
            approval_jackfruit,
        ]
        db.add_all(all_approvals)
        db.flush()
        print(f"  ✔ 立项记录 {len(all_approvals)} 份（猫山王、火龙果、菠萝蜜）")

        all_milestones = []

        base_musang_king = approval_musang_king.approval_date
        musang_king_milestone_templates = [
            (MilestoneType.FOUNDATION, "奠基开工", MilestoneStatus.COMPLETED, base_musang_king + timedelta(days=25), base_musang_king + timedelta(days=22), 1),
            (MilestoneType.MAIN_STRUCTURE, "主体结构封顶", MilestoneStatus.IN_PROGRESS, base_musang_king + timedelta(days=180), None, 2),
            (MilestoneType.EQUIPMENT_INSTALLATION, "设备安装调试", MilestoneStatus.NOT_STARTED, base_musang_king + timedelta(days=270), None, 3),
            (MilestoneType.TRIAL_PRODUCTION, "试生产", MilestoneStatus.NOT_STARTED, base_musang_king + timedelta(days=330), None, 4),
            (MilestoneType.OFFICIAL_PRODUCTION, "正式投产运营", MilestoneStatus.NOT_STARTED, base_musang_king + timedelta(days=365), None, 5),
        ]
        for mtype, mname, mstatus, planned, actual, seq in musang_king_milestone_templates:
            all_milestones.append(models.ProjectMilestone(
                project_id=cn_my_musang_king_project.id, sequence=seq, milestone_type=mtype, name=mname,
                status=mstatus, planned_date=planned, actual_date=actual,
                completion_rate=100.0 if mstatus == MilestoneStatus.COMPLETED else (40.0 if mstatus == MilestoneStatus.IN_PROGRESS else 0.0),
                responsible_person="林敬益",
            ))

        base_dragonfruit = approval_dragonfruit.approval_date
        dragonfruit_milestone_templates = [
            (MilestoneType.FOUNDATION, "奠基开工", MilestoneStatus.COMPLETED, base_dragonfruit + timedelta(days=18), base_dragonfruit + timedelta(days=15), 1),
            (MilestoneType.MAIN_STRUCTURE, "主体结构封顶", MilestoneStatus.COMPLETED, base_dragonfruit + timedelta(days=130), base_dragonfruit + timedelta(days=125), 2),
            (MilestoneType.EQUIPMENT_INSTALLATION, "设备安装调试", MilestoneStatus.COMPLETED, base_dragonfruit + timedelta(days=180), base_dragonfruit + timedelta(days=185), 3),
            (MilestoneType.TRIAL_PRODUCTION, "试生产", MilestoneStatus.IN_PROGRESS, base_dragonfruit + timedelta(days=210), base_dragonfruit + timedelta(days=215), 4),
            (MilestoneType.OFFICIAL_PRODUCTION, "正式投产运营", MilestoneStatus.NOT_STARTED, base_dragonfruit + timedelta(days=240), None, 5),
        ]
        for mtype, mname, mstatus, planned, actual, seq in dragonfruit_milestone_templates:
            all_milestones.append(models.ProjectMilestone(
                project_id=vn_dragonfruit_project.id, sequence=seq, milestone_type=mtype, name=mname,
                status=mstatus, planned_date=planned, actual_date=actual,
                completion_rate=100.0 if mstatus == MilestoneStatus.COMPLETED else (80.0 if mstatus == MilestoneStatus.IN_PROGRESS else 0.0),
                responsible_person="Nguyễn Văn Hùng",
            ))

        base_jackfruit = approval_jackfruit.approval_date
        jackfruit_milestone_templates = [
            (MilestoneType.FOUNDATION, "奠基开工", MilestoneStatus.COMPLETED, base_jackfruit + timedelta(days=15), base_jackfruit + timedelta(days=12), 1),
            (MilestoneType.MAIN_STRUCTURE, "主体结构封顶", MilestoneStatus.COMPLETED, base_jackfruit + timedelta(days=90), base_jackfruit + timedelta(days=86), 2),
            (MilestoneType.EQUIPMENT_INSTALLATION, "设备安装调试", MilestoneStatus.COMPLETED, base_jackfruit + timedelta(days=140), base_jackfruit + timedelta(days=138), 3),
            (MilestoneType.TRIAL_PRODUCTION, "试生产", MilestoneStatus.COMPLETED, base_jackfruit + timedelta(days=165), base_jackfruit + timedelta(days=168), 4),
            (MilestoneType.OFFICIAL_PRODUCTION, "正式投产运营", MilestoneStatus.COMPLETED, base_jackfruit + timedelta(days=200), base_jackfruit + timedelta(days=195), 5),
        ]
        for mtype, mname, mstatus, planned, actual, seq in jackfruit_milestone_templates:
            all_milestones.append(models.ProjectMilestone(
                project_id=id_jackfruit_project.id, sequence=seq, milestone_type=mtype, name=mname,
                status=mstatus, planned_date=planned, actual_date=actual,
                completion_rate=100.0,
                responsible_person="Budi Santoso",
            ))

        db.add_all(all_milestones)
        db.flush()
        print(f"  ✔ 里程碑 {len(all_milestones)} 个（猫山王:5 / 火龙果:5 / 菠萝蜜:5）")

        status_log_templates = [
            (cn_my_musang_king_project.id, None, ProjectStatus.ATTRACTING_INVESTMENT, "项目发布，进入招商阶段"),
            (cn_my_musang_king_project.id, ProjectStatus.ATTRACTING_INVESTMENT, ProjectStatus.NEGOTIATING, "收到合作意向"),
            (cn_my_musang_king_project.id, ProjectStatus.NEGOTIATING, ProjectStatus.ESTABLISHED, "正式立项，文号NNZMQ-LD-2025-0037"),
            (cn_my_musang_king_project.id, ProjectStatus.ESTABLISHED, ProjectStatus.UNDER_CONSTRUCTION, "奠基开工里程碑完成"),
            (vn_dragonfruit_project.id, None, ProjectStatus.ATTRACTING_INVESTMENT, "项目发布"),
            (vn_dragonfruit_project.id, ProjectStatus.ATTRACTING_INVESTMENT, ProjectStatus.NEGOTIATING, "收到越南合作方意向"),
            (vn_dragonfruit_project.id, ProjectStatus.NEGOTIATING, ProjectStatus.ESTABLISHED, "东兴边合区正式立项"),
            (vn_dragonfruit_project.id, ProjectStatus.ESTABLISHED, ProjectStatus.UNDER_CONSTRUCTION, "开工建设"),
            (id_jackfruit_project.id, None, ProjectStatus.ATTRACTING_INVESTMENT, "发布"),
            (id_jackfruit_project.id, ProjectStatus.ATTRACTING_INVESTMENT, ProjectStatus.NEGOTIATING, "洽谈"),
            (id_jackfruit_project.id, ProjectStatus.NEGOTIATING, ProjectStatus.ESTABLISHED, "立项"),
            (id_jackfruit_project.id, ProjectStatus.ESTABLISHED, ProjectStatus.UNDER_CONSTRUCTION, "开工"),
            (id_jackfruit_project.id, ProjectStatus.UNDER_CONSTRUCTION, ProjectStatus.COMMISSIONED, "正式投产运营"),
            (cn_th_coconut_phase1.id, None, ProjectStatus.ATTRACTING_INVESTMENT, "发布"),
            (cn_th_coconut_phase1.id, ProjectStatus.ATTRACTING_INVESTMENT, ProjectStatus.NEGOTIATING, "北部湾冷链提交意向"),
            (asean_juice_supply_base.id, None, ProjectStatus.ATTRACTING_INVESTMENT, "发布"),
            (asean_juice_supply_base.id, ProjectStatus.ATTRACTING_INVESTMENT, ProjectStatus.NEGOTIATING, "广西农垦提交意向"),
            (gx_nongken_upgrade_project.id, None, ProjectStatus.ATTRACTING_INVESTMENT, "发布"),
            (gx_huayin_beibuwan_joint_park.id, None, ProjectStatus.ATTRACTING_INVESTMENT, "发布"),
        ]
        all_status_logs = []
        for pid, fs, ts, reason in status_log_templates:
            all_status_logs.append(models.ProjectStatusLog(
                project_id=pid, from_status=fs, to_status=ts,
                reason=reason, operator="系统脚本",
            ))
        db.add_all(all_status_logs)
        db.commit()
        print(f"  ✔ 状态流转日志 {len(all_status_logs)} 条")
        print("\n🎉 示例数据植入完成！")
        print("   - 东盟合作主体：泰国2家、马来西亚1家、越南1家、印尼1家")
        print("   - 广西方主体：农垦、华银、北部湾冷链")
        print("   - 在谈项目（洽谈中）：中泰椰子项目、果汁对华供应项目")
        print("   - 已立项/建设中/投产：猫山王、火龙果、菠萝蜜")
        print("   - 招商中项目：农垦升级、华银联合加工园")
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
