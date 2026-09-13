"""数据模型：供应商、食材采购、留样记录、从业人员健康证、异常上报、整改跟踪。"""
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Supplier(Base):
    """供应商"""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)      # 供应商名称
    contact = Column(String(50))                                  # 联系人
    phone = Column(String(20))                                    # 联系电话
    license_no = Column(String(50))                               # 食品经营许可证号
    address = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)

    purchases = relationship("Purchase", back_populates="supplier")


class Purchase(Base):
    """食材采购记录"""
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_name = Column(String(100), nullable=False)         # 食材名称
    category = Column(String(20), nullable=False, index=True)     # 蔬菜/肉类/水产/蛋奶/粮油/调味品/水果/其他
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    quantity = Column(Float, nullable=False)                      # 数量
    unit = Column(String(10), nullable=False, default="kg")       # 单位
    unit_price = Column(Float, nullable=False)                    # 单价(元)
    total_price = Column(Float, nullable=False)                   # 总价(元)
    purchase_date = Column(Date, nullable=False, index=True)      # 采购日期
    production_date = Column(Date)                                # 生产日期
    expiry_date = Column(Date, index=True)                        # 保质期至
    batch_no = Column(String(50))                                 # 批次号
    certificate_no = Column(String(50))                           # 检疫/合格证号(索证索票)
    purchaser = Column(String(50))                                # 采购员
    inspector = Column(String(50))                                # 验收员
    status = Column(String(10), default="合格")                   # 待检/合格/不合格
    storage_location = Column(String(50))                         # 存放位置(冷库/常温库/冷藏柜...)
    remark = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)

    supplier = relationship("Supplier", back_populates="purchases")


class Sample(Base):
    """食品留样记录：每餐每品种留样≥125g，专柜冷藏保存48小时"""
    __tablename__ = "samples"

    id = Column(Integer, primary_key=True, index=True)
    dish_name = Column(String(100), nullable=False)               # 菜品名称
    meal_type = Column(String(10), nullable=False, index=True)    # 早餐/午餐/晚餐/加餐
    sample_time = Column(DateTime, nullable=False, index=True)    # 留样时间
    retention_deadline = Column(DateTime, nullable=False)         # 留样截止(留样时间+48h)
    weight_grams = Column(Float, nullable=False, default=125)     # 留样重量(克)
    container_no = Column(String(20))                             # 留样盒编号
    fridge_no = Column(String(20))                                # 留样柜编号
    keeper = Column(String(50))                                   # 留样人
    status = Column(String(10), default="留样中", index=True)     # 留样中/已销毁/异常
    disposed_at = Column(DateTime)                                # 销毁时间
    disposed_by = Column(String(50))                              # 销毁人
    remark = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)


class Staff(Base):
    """从业人员及健康证"""
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)                     # 姓名
    gender = Column(String(4))                                    # 男/女
    position = Column(String(20), nullable=False)                 # 岗位:厨师/面点师/帮厨/洗碗工/采购员/仓管员/服务员
    id_card = Column(String(18))                                  # 身份证号
    phone = Column(String(20))
    hire_date = Column(Date)                                      # 入职日期
    health_cert_no = Column(String(50))                           # 健康证编号
    cert_issue_date = Column(Date)                                # 发证日期
    cert_expiry_date = Column(Date, index=True)                   # 有效期至(健康证有效期1年)
    status = Column(String(10), default="在职")                   # 在职/离职
    created_at = Column(DateTime, default=datetime.now)


class Incident(Base):
    """异常上报"""
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)                   # 标题
    category = Column(String(20), nullable=False, index=True)     # 食材异常/留样异常/健康证异常/环境卫生/设备故障/投诉/其他
    description = Column(Text)                                    # 详细描述
    severity = Column(String(10), default="一般")                 # 一般/较重/严重
    reporter = Column(String(50))                                 # 上报人
    source = Column(String(10), default="人工上报")               # 人工上报/系统巡检
    related_type = Column(String(20))                             # 关联对象类型: purchase/sample/staff/rectification
    related_id = Column(Integer)                                  # 关联对象ID
    status = Column(String(10), default="待处理", index=True)     # 待处理/整改中/已整改/已关闭
    reported_at = Column(DateTime, default=datetime.now)
    closed_at = Column(DateTime)

    rectifications = relationship("Rectification", back_populates="incident",
                                  cascade="all, delete-orphan",
                                  order_by="Rectification.id")


class Rectification(Base):
    """整改跟踪"""
    __tablename__ = "rectifications"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False, index=True)
    measures = Column(Text, nullable=False)                       # 整改措施
    responsible = Column(String(50), nullable=False)              # 责任人
    deadline = Column(Date, nullable=False)                       # 整改期限
    status = Column(String(10), default="待整改", index=True)     # 待整改/整改中/已完成/已逾期
    started_at = Column(DateTime)                                 # 开始整改时间
    completed_at = Column(DateTime)                               # 完成时间
    result = Column(Text)                                         # 整改结果说明
    verifier = Column(String(50))                                 # 验收人
    verified_at = Column(DateTime)                                # 验收时间
    created_at = Column(DateTime, default=datetime.now)

    incident = relationship("Incident", back_populates="rectifications")


class InspectionRun(Base):
    """巡检运行记录（自动/手动）"""
    __tablename__ = "inspection_runs"

    id = Column(Integer, primary_key=True, index=True)
    trigger = Column(String(10), nullable=False)                  # 自动/手动
    started_at = Column(DateTime, nullable=False, index=True)
    finished_at = Column(DateTime)
    status = Column(String(10), default="失败")                   # 成功/失败
    created_count = Column(Integer, default=0)                    # 本次新开工单数
    error = Column(String(500))                                   # 失败原因


class Setting(Base):
    """系统配置（键值对），如自动巡检开关与运行时刻"""
    __tablename__ = "settings"

    key = Column(String(50), primary_key=True)
    value = Column(String(500))
