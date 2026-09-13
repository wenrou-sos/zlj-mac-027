"""本地模拟数据：日期均相对当前时间生成，保证演示时预警/到期场景始终可见。"""
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .models import Incident, Purchase, Rectification, Sample, Staff, Supplier


def seed(db: Session) -> None:
    if db.query(Supplier).count() > 0:
        return  # 已有数据则跳过

    today = date.today()
    now = datetime.now().replace(minute=0, second=0, microsecond=0)

    # ---------- 供应商 ----------
    suppliers = [
        Supplier(name="绿源农产品配送有限公司", contact="王建国", phone="13801112233",
                 license_no="JY11101050012345", address="市农产品批发市场A区12号"),
        Supplier(name="鲜肉联食品厂", contact="李红梅", phone="13902223344",
                 license_no="JY11101050023456", address="市经济开发区食品工业园3号"),
        Supplier(name="金龙粮油批发部", contact="张伟", phone="13703334455",
                 license_no="JY11101050034567", address="市粮油批发市场B区8号"),
        Supplier(name="每日鲜蛋奶配送中心", contact="陈晓燕", phone="13604445566",
                 license_no="JY11101050045678", address="市高新区物流园C5库"),
    ]
    db.add_all(suppliers)
    db.flush()

    # ---------- 食材采购 ----------
    def p(name, cat, sid, qty, unit, price, days_ago, shelf_days, batch, cert, purchaser, inspector, loc, status="合格"):
        pd = today - timedelta(days=days_ago)
        return Purchase(
            ingredient_name=name, category=cat, supplier_id=sid, quantity=qty, unit=unit,
            unit_price=price, total_price=round(qty * price, 2), purchase_date=pd,
            production_date=pd - timedelta(days=1), expiry_date=pd + timedelta(days=shelf_days),
            batch_no=batch, certificate_no=cert, purchaser=purchaser, inspector=inspector,
            status=status, storage_location=loc,
        )

    purchases = [
        p("大白菜", "蔬菜", 1, 80, "kg", 2.4, 1, 5, "PC20260912001", "JZ20260912001", "刘强", "赵敏", "常温库"),
        p("土豆", "蔬菜", 1, 100, "kg", 3.0, 2, 15, "PC20260911002", "JZ20260911002", "刘强", "赵敏", "常温库"),
        p("西红柿", "蔬菜", 1, 60, "kg", 5.6, 1, 4, "PC20260912003", "JZ20260912003", "刘强", "赵敏", "冷藏柜1"),
        p("黄瓜", "蔬菜", 1, 50, "kg", 4.8, 0, 4, "PC20260913001", "JZ20260913001", "刘强", "赵敏", "冷藏柜1"),
        p("猪后腿肉", "肉类", 2, 45, "kg", 28.0, 0, 3, "PC20260913002", "JY20260913011", "刘强", "赵敏", "冷库"),
        p("鸡胸肉", "肉类", 2, 30, "kg", 18.0, 1, 5, "PC20260912004", "JY20260912008", "刘强", "赵敏", "冷库"),
        p("猪五花肉", "肉类", 2, 25, "kg", 30.0, 6, 7, "PC20260907001", "JY20260907005", "刘强", "赵敏", "冷库"),   # 明天到期->临期
        p("带鱼", "水产", 2, 20, "kg", 22.0, 3, 30, "PC20260910001", "JY20260910003", "刘强", "赵敏", "冷库"),
        p("鸡蛋", "蛋奶", 4, 40, "kg", 9.6, 2, 20, "PC20260911001", "JD20260911001", "刘强", "赵敏", "常温库"),
        p("纯牛奶", "蛋奶", 4, 200, "盒", 2.5, 4, 12, "PC20260909001", "JD20260909002", "刘强", "赵敏", "冷藏柜2"),
        p("酸奶", "蛋奶", 4, 150, "杯", 3.2, 9, 21, "PC20260904001", "JD20260904001", "刘强", "赵敏", "冷藏柜2"),  # 临期
        p("大米", "粮油", 3, 500, "kg", 5.2, 10, 180, "PC20260903001", "LY20260903001", "刘强", "赵敏", "粮油库"),
        p("面粉", "粮油", 3, 200, "kg", 4.4, 12, 120, "PC20260901001", "LY20260901001", "刘强", "赵敏", "粮油库"),
        p("食用油", "粮油", 3, 100, "桶", 68.0, 15, 365, "PC20260829001", "LY20260829001", "刘强", "赵敏", "粮油库"),
        p("生抽酱油", "调味品", 3, 40, "瓶", 8.5, 20, 540, "PC20260824001", "LY20260824002", "刘强", "赵敏", "调味品库"),
        p("食用盐", "调味品", 3, 50, "袋", 2.0, 20, 1095, "PC20260824002", "LY20260824003", "刘强", "赵敏", "调味品库"),
        p("豆腐", "其他", 1, 35, "kg", 4.0, 8, 7, "PC20260905001", "JZ20260905001", "刘强", "赵敏", "冷藏柜1"),    # 已过期
        p("苹果", "水果", 1, 60, "kg", 7.0, 2, 10, "PC20260911003", "JZ20260911004", "刘强", "赵敏", "常温库"),
        p("冷冻虾仁", "水产", 2, 15, "kg", 45.0, 5, 90, "PC20260908001", "JY20260908002", "刘强", "赵敏", "冷库"),
        p("午餐肉罐头", "其他", 3, 24, "罐", 12.0, 30, 720, "PC20260814001", "LY20260814001", "刘强", "赵敏", "常温库", status="待检"),
    ]
    db.add_all(purchases)

    # ---------- 留样记录（相对当前时间，覆盖各种到期状态） ----------
    def s(dish, meal, hours_ago, weight, box, fridge, keeper, status="留样中", disposed=False):
        st = now - timedelta(hours=hours_ago)
        sample = Sample(
            dish_name=dish, meal_type=meal, sample_time=st,
            retention_deadline=st + timedelta(hours=48),
            weight_grams=weight, container_no=box, fridge_no=fridge, keeper=keeper,
            status=status,
        )
        if disposed:
            sample.disposed_at = sample.retention_deadline + timedelta(hours=1)
            sample.disposed_by = keeper
        return sample

    samples = [
        # 今日留样（留样中，时间充裕）
        s("红烧肉", "午餐", 3, 150, "H-101", "1号柜", "周师傅"),
        s("清炒大白菜", "午餐", 3, 130, "H-102", "1号柜", "周师傅"),
        s("西红柿鸡蛋汤", "午餐", 3, 125, "H-103", "1号柜", "周师傅"),
        s("米饭", "午餐", 3, 125, "H-104", "1号柜", "周师傅"),
        s("小米粥", "早餐", 8, 125, "Z-201", "1号柜", "吴阿姨"),
        s("煮鸡蛋", "早餐", 8, 130, "Z-202", "1号柜", "吴阿姨"),
        s("花卷", "早餐", 8, 125, "Z-203", "1号柜", "吴阿姨"),
        # 即将到期（剩余<2小时）
        s("土豆炖牛腩", "晚餐", 47, 150, "W-301", "2号柜", "周师傅"),
        s("蒜蓉黄瓜", "晚餐", 47, 125, "W-302", "2号柜", "周师傅"),
        # 已到期未销毁（触发超期提醒/巡检工单）
        s("宫保鸡丁", "午餐", 51, 145, "H-098", "2号柜", "周师傅"),
        s("醋溜土豆丝", "午餐", 51, 130, "H-099", "2号柜", "周师傅"),
        # 历史已销毁
        s("红烧带鱼", "晚餐", 72, 150, "W-288", "2号柜", "周师傅", status="已销毁", disposed=True),
        s("清炒时蔬", "晚餐", 72, 125, "W-289", "2号柜", "周师傅", status="已销毁", disposed=True),
        s("冬瓜排骨汤", "午餐", 96, 140, "H-080", "1号柜", "吴阿姨", status="已销毁", disposed=True),
        s("蛋炒饭", "早餐", 100, 125, "Z-180", "1号柜", "吴阿姨", status="已销毁", disposed=True),
    ]
    db.add_all(samples)

    # ---------- 从业人员健康证 ----------
    def st(name, gender, pos, phone, hire_days_ago, cert_no, expiry_in_days, status="在职"):
        return Staff(
            name=name, gender=gender, position=pos, phone=phone,
            id_card=f"11010119{80 + hire_days_ago % 20}0{(hire_days_ago % 9) + 1}1{hire_days_ago % 28 + 1:02d}{1000 + hire_days_ago % 9000}",
            hire_date=today - timedelta(days=hire_days_ago),
            health_cert_no=cert_no,
            cert_issue_date=today + timedelta(days=expiry_in_days) - timedelta(days=365),
            cert_expiry_date=today + timedelta(days=expiry_in_days),
            status=status,
        )

    staff = [
        st("周建国", "男", "厨师长", "13811110001", 1500, "JK2025A0001", 200),
        st("吴桂芳", "女", "面点师", "13811110002", 1200, "JK2025A0002", 160),
        st("郑海涛", "男", "厨师", "13811110003", 900, "JK2025A0003", 120),
        st("王丽萍", "女", "厨师", "13811110004", 800, "JK2025A0004", 95),
        st("刘志明", "男", "帮厨", "13811110005", 600, "JK2025A0005", 60),
        st("张秀兰", "女", "帮厨", "13811110006", 500, "JK2025A0006", 25),   # 临期
        st("赵国庆", "男", "洗碗工", "13811110007", 400, "JK2025A0007", 12),   # 临期
        st("孙丽华", "女", "服务员", "13811110008", 350, "JK2025A0008", 8),    # 临期
        st("马建军", "男", "采购员", "13811110009", 1000, "JK2025A0009", -5),  # 已过期
        st("胡小燕", "女", "仓管员", "13811110010", 300, "JK2025A0010", 45),
        st("高志强", "男", "厨师", "13811110011", 200, "JK2025A0011", 300),
        st("林美玲", "女", "服务员", "13811110012", 180, "JK2024A0012", -20, status="离职"),
    ]
    db.add_all(staff)
    db.flush()

    # ---------- 异常上报 + 整改 ----------
    inc1 = Incident(
        title="猪五花肉色泽异常", category="食材异常", severity="较重",
        description="今日验收时发现一批猪五花肉表面发黏、色泽偏暗，有轻微异味，已当场拒收并要求供应商换货。",
        reporter="赵敏", source="人工上报", status="整改中",
        reported_at=now - timedelta(days=2, hours=5),
    )
    inc2 = Incident(
        title="2号留样柜温度偏高", category="设备故障", severity="严重",
        description="晨检发现2号留样柜温度显示8℃，高于留样冷藏标准(0-4℃)，柜内留样已转移至1号柜。",
        reporter="周建国", source="人工上报", status="整改中",
        reported_at=now - timedelta(days=4, hours=2),
    )
    inc3 = Incident(
        title="学生反映午餐菜品偏咸", category="投诉", severity="一般",
        description="多名学生反映昨日午餐红烧肉偏咸，已提醒厨师长控制用盐量。",
        reporter="值班老师", source="人工上报", status="已整改",
        reported_at=now - timedelta(days=6),
    )
    inc4 = Incident(
        title="仓库防鼠设施破损", category="环境卫生", severity="较重",
        description="粮油库门口挡鼠板变形无法闭合，存在鼠害隐患。",
        reporter="胡小燕", source="人工上报", status="待处理",
        reported_at=now - timedelta(days=1, hours=3),
    )
    inc5 = Incident(
        title="留样盒数量不足", category="留样异常", severity="一般",
        description="午高峰留样盒不够用，临时使用未消毒备用盒，存在交叉污染风险。",
        reporter="吴桂芳", source="人工上报", status="已关闭",
        reported_at=now - timedelta(days=10), closed_at=now - timedelta(days=8),
    )
    db.add_all([inc1, inc2, inc3, inc4, inc5])
    db.flush()

    rects = [
        Rectification(
            incident_id=inc1.id, measures="联系鲜肉联食品厂更换同批次猪肉，并索取新的动物检疫合格证明；加强验收环节感官检查",
            responsible="刘强", deadline=today + timedelta(days=2), status="整改中",
            started_at=now - timedelta(days=2),
        ),
        Rectification(
            incident_id=inc2.id, measures="联系厂家维修2号留样柜压缩机，维修期间留样统一存放1号柜；每日三次记录柜温",
            responsible="周建国", deadline=today - timedelta(days=1), status="已逾期",   # 逾期未整改
            started_at=now - timedelta(days=4),
        ),
        Rectification(
            incident_id=inc3.id, measures="调整菜品盐量标准，厨师长每餐试味；建立学生口味反馈周汇总",
            responsible="周建国", deadline=today - timedelta(days=3), status="已完成",
            started_at=now - timedelta(days=6), completed_at=now - timedelta(days=4),
            result="已修订用盐标准并培训到岗，近三日无类似投诉", verifier="赵敏",
            verified_at=now - timedelta(days=3),
        ),
    ]
    db.add_all(rects)

    db.commit()
    print("✅ 模拟数据初始化完成：供应商4家、采购20条、留样15条、从业人员12名、异常5条、整改3条")
