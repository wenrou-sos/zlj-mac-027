import React, { useEffect, useState } from 'react'
import {
  Alert, Button, Card, DatePicker, Form, Input, InputNumber, Modal,
  Popconfirm, Segmented, Select, Space, Table, Tag, message,
} from 'antd'
import { DeleteOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api'
import { getUser, hasRole } from '../auth'
import VoidModal from '../components/VoidModal'

const MEAL_TYPES = ['早餐', '午餐', '晚餐', '加餐']

/** 剩余时间标签：绿色>2h，橙色<2h，红色已到期 */
function remainingTag(record) {
  if (record.status !== '留样中') return <Tag>{record.status}</Tag>
  const h = record.remaining_hours
  if (h < 0) return <Tag color="red">已超期 {-h} 小时，待销毁</Tag>
  if (h <= 2) return <Tag color="orange">剩余 {h} 小时</Tag>
  return <Tag color="green">剩余 {h} 小时</Tag>
}

export default function Samples() {
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({})
  const [view, setView] = useState('valid')      // valid有效 / voided已作废
  const [modalOpen, setModalOpen] = useState(false)
  const [disposeTarget, setDisposeTarget] = useState(null)
  const [voidTarget, setVoidTarget] = useState(null)
  const [form] = Form.useForm()
  const user = getUser()
  const canOperate = hasRole('admin', 'keeper')  // 留样登记/销毁权限
  const isAdmin = hasRole('admin')

  const load = async () => {
    setLoading(true)
    try {
      setList(await api.get('/samples', { params: { ...filters, view } }))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 60000) // 每分钟刷新倒计时
    return () => clearInterval(timer)
  }, [filters, view])

  const submit = async () => {
    const values = await form.validateFields()
    await api.post('/samples', {
      ...values,
      sample_time: values.sample_time.format('YYYY-MM-DDTHH:mm:ss'),
    })
    message.success('留样登记成功，保存期48小时')
    setModalOpen(false)
    load()
  }

  const confirmDispose = async () => {
    // 销毁人由后端从登录账号取
    await api.post(`/samples/${disposeTarget.id}/dispose`, {})
    message.success('销毁登记完成')
    setDisposeTarget(null)
    load()
  }

  const doVoid = async (reason) => {
    await api.post(`/samples/${voidTarget.id}/void`, { reason })
    message.success('已作废，原记录可在「已作废」视图中查看')
    setVoidTarget(null)
    load()
  }

  const doRestore = async (id) => {
    await api.post(`/samples/${id}/restore`)
    message.success('已恢复为有效记录')
    load()
  }

  const overdueCount = list.filter((s) => s.status === '留样中' && s.remaining_hours < 0).length
  const expiringCount = list.filter((s) => s.status === '留样中' && s.remaining_hours >= 0 && s.remaining_hours <= 2).length

  const baseColumns = [
    { title: '菜品名称', dataIndex: 'dish_name', width: 130, fixed: 'left' },
    { title: '餐次', dataIndex: 'meal_type', width: 70, render: (v) => <Tag color="blue">{v}</Tag> },
    { title: '留样时间', dataIndex: 'sample_time', width: 150, render: (v) => dayjs(v).format('MM-DD HH:mm') },
    { title: '到期时间(48h)', dataIndex: 'retention_deadline', width: 150, render: (v) => dayjs(v).format('MM-DD HH:mm') },
    { title: '倒计时', width: 160, render: (_, r) => remainingTag(r) },
    { title: '重量(g)', dataIndex: 'weight_grams', width: 80 },
    { title: '留样盒', dataIndex: 'container_no', width: 90, render: (v) => v || '-' },
    { title: '留样柜', dataIndex: 'fridge_no', width: 85, render: (v) => v || '-' },
    { title: '留样人', dataIndex: 'keeper', width: 90 },
    { title: '状态', dataIndex: 'status', width: 85, render: (v) => (
      <Tag color={v === '留样中' ? 'processing' : v === '已销毁' ? 'default' : 'red'}>{v}</Tag>
    ) },
    { title: '销毁信息', width: 170, render: (_, r) => (
      r.disposed_at ? `${dayjs(r.disposed_at).format('MM-DD HH:mm')} / ${r.disposed_by}` : '-'
    ) },
  ]

  const voidColumns = [
    { title: '作废时间', dataIndex: 'voided_at', width: 140, render: (v) => dayjs(v).format('MM-DD HH:mm') },
    { title: '作废原因', dataIndex: 'void_reason', width: 170, ellipsis: true },
    { title: '作废人', dataIndex: 'voided_by', width: 90 },
  ]

  const actionColumn = {
    title: '操作', width: 140, fixed: 'right',
    render: (_, r) => {
      if (view === 'voided') {
        return isAdmin ? (
          <Popconfirm title="确认恢复为有效记录？" onConfirm={() => doRestore(r.id)}>
            <a>恢复</a>
          </Popconfirm>
        ) : <span style={{ color: '#bbb' }}>只读</span>
      }
      return (
        <Space>
          {r.status === '留样中' && canOperate && (
            r.remaining_hours <= 0 ? (
              <a onClick={() => setDisposeTarget(r)}>销毁登记</a>
            ) : (
              <span style={{ color: '#bbb', cursor: 'not-allowed' }} title="留样满48小时后方可销毁">
                未到期
              </span>
            )
          )}
          {isAdmin && <a style={{ color: '#cf1322' }} onClick={() => setVoidTarget(r)}>作废</a>}
        </Space>
      )
    },
  }

  const columns = [...baseColumns, ...(view === 'voided' ? voidColumns : []), actionColumn]

  return (
    <Card
      title="食品留样记录（每品种≥125g，冷藏保存48小时）"
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          {canOperate && view === 'valid' && (
            <Button type="primary" icon={<PlusOutlined />}
              onClick={() => { form.resetFields(); form.setFieldsValue({ sample_time: dayjs(), weight_grams: 125, keeper: user?.name }); setModalOpen(true) }}>
              留样登记
            </Button>
          )}
        </Space>
      }
    >
      {(overdueCount > 0 || expiringCount > 0) && (
        <Alert
          style={{ marginBottom: 16 }}
          type={overdueCount > 0 ? 'error' : 'warning'}
          showIcon
          message={
            overdueCount > 0
              ? `有 ${overdueCount} 份留样已超期未销毁，请立即处理！`
              : `有 ${expiringCount} 份留样将在2小时内到期，请准备销毁登记`
          }
        />
      )}

      <Space wrap style={{ marginBottom: 16 }}>
        <Segmented
          options={[{ value: 'valid', label: '有效记录' }, { value: 'voided', label: '已作废' }]}
          value={view}
          onChange={setView}
        />
        <Select allowClear placeholder="餐次" style={{ width: 100 }}
          options={MEAL_TYPES.map((m) => ({ value: m, label: m }))}
          onChange={(v) => setFilters((f) => ({ ...f, meal_type: v }))} />
        <Select allowClear placeholder="状态" style={{ width: 110 }}
          options={['留样中', '已销毁', '异常'].map((s) => ({ value: s, label: s }))}
          onChange={(v) => setFilters((f) => ({ ...f, status: v }))} />
        <Input.Search allowClear placeholder="搜索菜品名称" style={{ width: 180 }}
          onSearch={(v) => setFilters((f) => ({ ...f, keyword: v || undefined }))} />
      </Space>

      <Table
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={list}
        scroll={{ x: 1300 }}
        pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 条` }}
        rowClassName={(r) => (r.status === '留样中' && r.remaining_hours < 0 ? 'row-overdue' : '')}
      />

      {/* 留样登记 */}
      <Modal
        title="留样登记"
        open={modalOpen}
        onOk={submit}
        onCancel={() => setModalOpen(false)}
        okText="登记"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item name="dish_name" label="菜品名称" rules={[{ required: true, message: '请输入菜品名称' }]}>
            <Input placeholder="如：红烧肉" />
          </Form.Item>
          <Space.Compact block>
            <Form.Item name="meal_type" label="餐次" rules={[{ required: true, message: '请选择' }]} style={{ flex: 1, marginRight: 12 }}>
              <Select options={MEAL_TYPES.map((m) => ({ value: m, label: m }))} />
            </Form.Item>
            <Form.Item name="sample_time" label="留样时间" rules={[{ required: true, message: '请选择' }]} style={{ flex: 1.4 }}>
              <DatePicker
                showTime={{ format: 'HH:mm' }}
                format="YYYY-MM-DD HH:mm"
                style={{ width: '100%' }}
                disabledDate={(d) => d && d.isAfter(dayjs(), 'day')}
              />
            </Form.Item>
          </Space.Compact>
          <Space.Compact block>
            <Form.Item name="weight_grams" label="留样重量(克，≥125)" rules={[{ required: true, message: '必填' }]} style={{ flex: 1, marginRight: 12 }}>
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="container_no" label="留样盒编号" style={{ flex: 1, marginRight: 12 }}>
              <Input placeholder="如：H-105" />
            </Form.Item>
            <Form.Item name="fridge_no" label="留样柜" style={{ flex: 1 }}>
              <Input placeholder="如：1号柜" />
            </Form.Item>
          </Space.Compact>
          <Form.Item name="keeper" label="留样人" rules={[{ required: true, message: '请填写留样人' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 销毁登记 */}
      <Modal
        title={`销毁登记：${disposeTarget?.dish_name ?? ''}`}
        open={!!disposeTarget}
        onOk={confirmDispose}
        onCancel={() => setDisposeTarget(null)}
        okText="确认销毁"
        cancelText="取消"
      >
        <p style={{ color: '#666' }}>
          该留样于 {disposeTarget && dayjs(disposeTarget.sample_time).format('MM-DD HH:mm')} 留样，
          48小时保存期已满。确认销毁后不可恢复。
        </p>
        <p>销毁人：<b>{user?.name}</b>（当前登录账号，自动记录）</p>
      </Modal>

      {/* 作废 */}
      <VoidModal
        open={!!voidTarget}
        title={`作废留样记录：${voidTarget?.dish_name ?? ''}`}
        onOk={doVoid}
        onCancel={() => setVoidTarget(null)}
      />

      <style>{`.row-overdue td { background: #fff1f0 !important; }`}</style>
    </Card>
  )
}
