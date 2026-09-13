import React, { useEffect, useState } from 'react'
import {
  Button, Card, DatePicker, Descriptions, Drawer, Empty, Form, Input, Modal,
  Popconfirm, Select, Space, Table, Tag, Timeline, Typography, message,
} from 'antd'
import { PlusOutlined, ReloadOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api'

const CATEGORIES = ['食材异常', '留样异常', '健康证异常', '环境卫生', '设备故障', '投诉', '其他']
const SEVERITIES = ['一般', '较重', '严重']
const sevColor = { 一般: 'blue', 较重: 'orange', 严重: 'red' }
const statusColor = { 待处理: 'red', 整改中: 'orange', 已整改: 'green', 已关闭: 'default' }
const rectColor = { 待整改: 'gold', 整改中: 'orange', 已完成: 'green', 已逾期: 'red' }

export default function Incidents() {
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({})
  const [reportOpen, setReportOpen] = useState(false)
  const [detail, setDetail] = useState(null)          // 当前查看的工单
  const [rectOpen, setRectOpen] = useState(false)     // 新建整改
  const [completeTarget, setCompleteTarget] = useState(null) // 完成整改
  const [completeResult, setCompleteResult] = useState('')
  const [form] = Form.useForm()
  const [rectForm] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      const data = await api.get('/incidents', { params: filters })
      setList(data)
      if (detail) setDetail(data.find((i) => i.id === detail.id) ?? null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [filters])

  const runInspection = async () => {
    const res = await api.post('/inspection/run')
    message.success(`巡检完成，新生成 ${res.created} 条异常工单`)
    load()
  }

  const submitReport = async () => {
    const values = await form.validateFields()
    await api.post('/incidents', values)
    message.success('异常上报成功')
    setReportOpen(false)
    load()
  }

  const submitRect = async () => {
    const values = await rectForm.validateFields()
    await api.post('/rectifications', {
      ...values,
      incident_id: detail.id,
      deadline: values.deadline.format('YYYY-MM-DD'),
    })
    message.success('整改任务已下达')
    setRectOpen(false)
    load()
  }

  const submitComplete = async () => {
    if (!completeResult.trim()) {
      message.warning('请填写整改结果')
      return
    }
    await api.post(`/rectifications/${completeTarget.id}/complete`, { result: completeResult.trim() })
    message.success('整改已完成，待验收')
    setCompleteTarget(null)
    setCompleteResult('')
    load()
  }

  const verify = async (rect) => {
    await api.post(`/rectifications/${rect.id}/verify`, { verifier: '管理员' })
    message.success('验收通过，工单已标记为已整改')
    load()
  }

  const closeIncident = async (id) => {
    await api.post(`/incidents/${id}/close`)
    message.success('工单已关闭')
    load()
  }

  const columns = [
    { title: '编号', dataIndex: 'id', width: 60, render: (v) => `#${v}` },
    { title: '标题', dataIndex: 'title', width: 220, ellipsis: true },
    { title: '分类', dataIndex: 'category', width: 100, render: (v) => <Tag>{v}</Tag> },
    { title: '严重程度', dataIndex: 'severity', width: 90, render: (v) => <Tag color={sevColor[v]}>{v}</Tag> },
    { title: '上报人', dataIndex: 'reporter', width: 90 },
    { title: '来源', dataIndex: 'source', width: 95, render: (v) => (
      <Tag color={v === '系统巡检' ? 'purple' : 'default'}>{v}</Tag>
    ) },
    { title: '上报时间', dataIndex: 'reported_at', width: 150, render: (v) => dayjs(v).format('MM-DD HH:mm') },
    { title: '状态', dataIndex: 'status', width: 90, render: (v) => <Tag color={statusColor[v]}>{v}</Tag> },
    { title: '整改', width: 80, render: (_, r) => `${r.rectifications.length} 项` },
    {
      title: '操作', width: 150, fixed: 'right',
      render: (_, r) => (
        <Space>
          <a onClick={() => setDetail(r)}>详情/整改</a>
          {(r.status === '待处理' || r.status === '已整改') && (
            <Popconfirm title="确认关闭该工单？" onConfirm={() => closeIncident(r.id)}>
              <a>关闭</a>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <Card
      title="异常上报与整改跟踪"
      extra={
        <Space>
          <Button icon={<SafetyCertificateOutlined />} onClick={runInspection}>系统巡检</Button>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />}
            onClick={() => { form.resetFields(); form.setFieldsValue({ severity: '一般' }); setReportOpen(true) }}>
            异常上报
          </Button>
        </Space>
      }
    >
      <Space wrap style={{ marginBottom: 16 }}>
        <Select allowClear placeholder="分类" style={{ width: 120 }}
          options={CATEGORIES.map((c) => ({ value: c, label: c }))}
          onChange={(v) => setFilters((f) => ({ ...f, category: v }))} />
        <Select allowClear placeholder="状态" style={{ width: 110 }}
          options={Object.keys(statusColor).map((s) => ({ value: s, label: s }))}
          onChange={(v) => setFilters((f) => ({ ...f, status: v }))} />
        <Select allowClear placeholder="严重程度" style={{ width: 110 }}
          options={SEVERITIES.map((s) => ({ value: s, label: s }))}
          onChange={(v) => setFilters((f) => ({ ...f, severity: v }))} />
        <Input.Search allowClear placeholder="搜索标题" style={{ width: 180 }}
          onSearch={(v) => setFilters((f) => ({ ...f, keyword: v || undefined }))} />
      </Space>

      <Table
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={list}
        scroll={{ x: 1100 }}
        pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 条` }}
      />

      {/* 异常上报 */}
      <Modal
        title="异常上报"
        open={reportOpen}
        onOk={submitReport}
        onCancel={() => setReportOpen(false)}
        okText="提交"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item name="title" label="标题" rules={[{ required: true, message: '请输入标题' }]}>
            <Input placeholder="简要描述异常情况" />
          </Form.Item>
          <Space.Compact block>
            <Form.Item name="category" label="分类" rules={[{ required: true, message: '请选择' }]} style={{ flex: 1, marginRight: 12 }}>
              <Select options={CATEGORIES.map((c) => ({ value: c, label: c }))} />
            </Form.Item>
            <Form.Item name="severity" label="严重程度" rules={[{ required: true }]} style={{ flex: 1, marginRight: 12 }}>
              <Select options={SEVERITIES.map((s) => ({ value: s, label: s }))} />
            </Form.Item>
            <Form.Item name="reporter" label="上报人" rules={[{ required: true, message: '请填写上报人' }]} style={{ flex: 1 }}>
              <Input />
            </Form.Item>
          </Space.Compact>
          <Form.Item name="description" label="详细描述" rules={[{ required: true, message: '请填写详细描述' }]}>
            <Input.TextArea rows={4} placeholder="时间、地点、具体情况、已采取的临时措施等" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 工单详情 + 整改跟踪 */}
      <Drawer
        title={detail ? `工单 #${detail.id}：${detail.title}` : ''}
        open={!!detail}
        onClose={() => setDetail(null)}
        width={560}
        extra={
          detail && detail.status !== '已关闭' && (
            <Button type="primary" onClick={() => { rectForm.resetFields(); setRectOpen(true) }}>
              下达整改任务
            </Button>
          )
        }
      >
        {detail && (
          <>
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="分类">{detail.category}</Descriptions.Item>
              <Descriptions.Item label="严重程度">
                <Tag color={sevColor[detail.severity]}>{detail.severity}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="上报人">{detail.reporter}</Descriptions.Item>
              <Descriptions.Item label="来源">{detail.source}</Descriptions.Item>
              <Descriptions.Item label="上报时间">{dayjs(detail.reported_at).format('YYYY-MM-DD HH:mm')}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={statusColor[detail.status]}>{detail.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="详细描述" span={2}>{detail.description}</Descriptions.Item>
            </Descriptions>

            <Typography.Title level={5} style={{ marginTop: 24 }}>整改跟踪</Typography.Title>
            {detail.rectifications.length === 0 ? (
              <Empty description="暂无整改任务" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <Timeline
                items={detail.rectifications.map((r) => ({
                  color: r.status === '已完成' ? 'green' : r.overdue ? 'red' : 'orange',
                  children: (
                    <div>
                      <Space wrap>
                        <Tag color={rectColor[r.status]}>{r.status}</Tag>
                        {r.overdue && r.status !== '已完成' && <Tag color="red">已逾期</Tag>}
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                          期限 {r.deadline} ｜ 责任人 {r.responsible}
                        </Typography.Text>
                      </Space>
                      <div style={{ margin: '6px 0' }}>{r.measures}</div>
                      {r.result && (
                        <div style={{ fontSize: 12, color: '#666' }}>
                          整改结果：{r.result}
                          {r.verifier && ` ｜ 验收人：${r.verifier}`}
                        </div>
                      )}
                      <Space style={{ marginTop: 6 }}>
                        {r.status !== '已完成' && (
                          <Button size="small" onClick={() => { setCompleteTarget(r); setCompleteResult('') }}>
                            完成整改
                          </Button>
                        )}
                        {r.status === '已完成' && !r.verifier && (
                          <Button size="small" type="primary" onClick={() => verify(r)}>
                            验收通过
                          </Button>
                        )}
                      </Space>
                    </div>
                  ),
                }))}
              />
            )}
          </>
        )}
      </Drawer>

      {/* 下达整改任务 */}
      <Modal
        title="下达整改任务"
        open={rectOpen}
        onOk={submitRect}
        onCancel={() => setRectOpen(false)}
        okText="下达"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={rectForm} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item name="measures" label="整改措施" rules={[{ required: true, message: '请填写整改措施' }]}>
            <Input.TextArea rows={3} placeholder="具体整改要求与措施" />
          </Form.Item>
          <Space.Compact block>
            <Form.Item name="responsible" label="责任人" rules={[{ required: true, message: '请填写责任人' }]} style={{ flex: 1, marginRight: 12 }}>
              <Input />
            </Form.Item>
            <Form.Item name="deadline" label="整改期限" rules={[{ required: true, message: '请选择期限' }]} style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} disabledDate={(d) => d && d < dayjs().startOf('day')} />
            </Form.Item>
          </Space.Compact>
        </Form>
      </Modal>

      {/* 完成整改 */}
      <Modal
        title="完成整改"
        open={!!completeTarget}
        onOk={submitComplete}
        onCancel={() => { setCompleteTarget(null); setCompleteResult('') }}
        okText="提交"
        cancelText="取消"
      >
        <p style={{ color: '#666' }}>整改措施：{completeTarget?.measures}</p>
        <Input.TextArea
          rows={3}
          placeholder="整改结果说明（完成情况、照片/凭证说明等）"
          value={completeResult}
          onChange={(e) => setCompleteResult(e.target.value)}
        />
      </Modal>
    </Card>
  )
}
