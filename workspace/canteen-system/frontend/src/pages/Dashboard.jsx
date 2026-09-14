import React, { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, List, Row, Statistic, Tag, Typography, message } from 'antd'
import {
  AlertOutlined,
  ClockCircleOutlined,
  ExperimentOutlined,
  IdcardOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  ShoppingCartOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import api from '../api'
import { hasRole } from '../auth'
import Chart from '../components/Chart'

const levelColor = { danger: 'red', warning: 'orange', info: 'blue' }
const levelText = { danger: '紧急', warning: '提醒', info: '提示' }

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [inspecting, setInspecting] = useState(false)

  const load = () => api.get('/dashboard').then(setData).catch(() => {})
  useEffect(() => {
    load()
  }, [])

  const runInspection = async () => {
    setInspecting(true)
    try {
      const res = await api.post('/inspection/run')
      message.success(`巡检完成：新开 ${res.created} 单，自动关闭 ${res.closed} 单`)
      load()
    } finally {
      setInspecting(false)
    }
  }

  if (!data) return <Card loading style={{ minHeight: 400 }} />
  const { stats } = data

  const cards = [
    { title: '今日留样', value: stats.today_samples, suffix: `留样中 ${stats.active_samples}`, icon: <ExperimentOutlined />, color: '#2f7d4f' },
    { title: '留样即将到期', value: stats.expiring_samples, suffix: `待销毁 ${stats.pending_dispose}`, icon: <ClockCircleOutlined />, color: stats.pending_dispose > 0 ? '#cf1322' : '#fa8c16' },
    { title: '健康证临期/过期', value: stats.cert_expiring, suffix: `已过期 ${stats.cert_expired}`, icon: <IdcardOutlined />, color: stats.cert_expired > 0 ? '#cf1322' : '#fa8c16' },
    { title: '待处理异常', value: stats.open_incidents, suffix: '工单', icon: <AlertOutlined />, color: stats.open_incidents > 0 ? '#cf1322' : '#2f7d4f' },
    { title: '整改逾期', value: stats.overdue_rectifications, suffix: '项', icon: <ToolOutlined />, color: stats.overdue_rectifications > 0 ? '#cf1322' : '#2f7d4f' },
    { title: '本月采购金额', value: stats.month_purchase_amount, prefix: '¥', icon: <ShoppingCartOutlined />, color: '#1677ff' },
  ]

  return (
    <div>
      {data.alerts.some((a) => a.level === 'danger') && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message={`当前有 ${data.alerts.filter((a) => a.level === 'danger').length} 条紧急预警，请立即处理！`}
          action={
            hasRole('admin') && (
              <Button size="small" danger icon={<SafetyCertificateOutlined />} loading={inspecting} onClick={runInspection}>
                系统巡检
              </Button>
            )
          }
        />
      )}

      <Row gutter={[16, 16]}>
        {cards.map((c) => (
          <Col xs={12} sm={8} lg={4} key={c.title}>
            <Card size="small">
              <Statistic
                title={
                  <span>
                    {c.icon} {c.title}
                  </span>
                }
                value={c.value}
                prefix={c.prefix}
                suffix={c.suffix && <span style={{ fontSize: 12, color: '#999' }}>{c.suffix}</span>}
                valueStyle={{ color: c.color, fontSize: 26 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={10}>
          <Card title="近30天采购分类占比" size="small">
            <Chart
              option={{
                tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
                legend: { bottom: 0 },
                series: [{
                  type: 'pie',
                  radius: ['40%', '65%'],
                  center: ['50%', '45%'],
                  label: { formatter: '{b}' },
                  data: data.purchase_by_category.map((d) => ({ name: d.category, value: d.amount })),
                }],
              }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={7}>
          <Card title="近7天采购金额" size="small">
            <Chart
              option={{
                tooltip: { trigger: 'axis' },
                grid: { left: 50, right: 20, top: 30, bottom: 30 },
                xAxis: { type: 'category', data: data.purchase_last_7_days.map((d) => d.date) },
                yAxis: { type: 'value' },
                series: [{
                  type: 'bar',
                  barWidth: 18,
                  itemStyle: { color: '#2f7d4f', borderRadius: [4, 4, 0, 0] },
                  data: data.purchase_last_7_days.map((d) => d.amount),
                }],
              }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={7}>
          <Card title="异常工单分类" size="small">
            <Chart
              option={{
                tooltip: {},
                grid: { left: 70, right: 20, top: 20, bottom: 30 },
                xAxis: { type: 'value' },
                yAxis: { type: 'category', data: data.incident_by_category.map((d) => d.category) },
                series: [{
                  type: 'bar',
                  barWidth: 14,
                  itemStyle: { color: '#fa8c16', borderRadius: [0, 4, 4, 0] },
                  data: data.incident_by_category.map((d) => d.count),
                }],
              }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="实时预警"
        size="small"
        style={{ marginTop: 16 }}
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={load}>
            刷新
          </Button>
        }
      >
        <List
          size="small"
          dataSource={data.alerts}
          locale={{ emptyText: '暂无预警，一切正常 ✅' }}
          renderItem={(a) => (
            <List.Item>
              <Tag color={levelColor[a.level]}>{levelText[a.level]}</Tag>
              <Typography.Text strong style={{ marginRight: 12 }}>{a.title}</Typography.Text>
              <Typography.Text type="secondary">{a.description}</Typography.Text>
            </List.Item>
          )}
        />
      </Card>
    </div>
  )
}
