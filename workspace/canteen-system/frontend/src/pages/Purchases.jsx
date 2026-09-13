import React, { useEffect, useState } from 'react'
import {
  Button, Card, DatePicker, Form, Input, InputNumber, Modal, Popconfirm,
  Select, Space, Table, Tag, message,
} from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api'

const CATEGORIES = ['蔬菜', '肉类', '水产', '蛋奶', '粮油', '调味品', '水果', '其他']
const UNITS = ['kg', 'g', 'L', '瓶', '桶', '袋', '盒', '杯', '罐', '个']
const STATUS = ['合格', '待检', '不合格']

function expiryTag(days) {
  if (days === null || days === undefined) return '-'
  if (days < 0) return <Tag color="red">已过期{-days}天</Tag>
  if (days <= 3) return <Tag color="orange">{days}天后到期</Tag>
  return <Tag color="green">剩余{days}天</Tag>
}

export default function Purchases() {
  const [list, setList] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({})
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      const params = {}
      if (filters.category) params.category = filters.category
      if (filters.status) params.status = filters.status
      if (filters.keyword) params.keyword = filters.keyword
      if (filters.range?.[0]) params.date_from = filters.range[0].format('YYYY-MM-DD')
      if (filters.range?.[1]) params.date_to = filters.range[1].format('YYYY-MM-DD')
      setList(await api.get('/purchases', { params }))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    api.get('/suppliers').then(setSuppliers).catch(() => {})
  }, [filters])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ purchase_date: dayjs(), unit: 'kg', status: '合格' })
    setModalOpen(true)
  }

  const openEdit = (record) => {
    setEditing(record)
    form.setFieldsValue({
      ...record,
      purchase_date: record.purchase_date ? dayjs(record.purchase_date) : null,
      production_date: record.production_date ? dayjs(record.production_date) : null,
      expiry_date: record.expiry_date ? dayjs(record.expiry_date) : null,
    })
    setModalOpen(true)
  }

  const submit = async () => {
    const values = await form.validateFields()
    const raw = {
      ...values,
      purchase_date: values.purchase_date?.format('YYYY-MM-DD'),
      production_date: values.production_date?.format('YYYY-MM-DD'),
      expiry_date: values.expiry_date?.format('YYYY-MM-DD'),
    }
    // 清空的下拉/日期值为 undefined，JSON 序列化会丢弃导致后端不更新；
    // 显式转为 null，后端收到后写入 NULL 清空原值
    const payload = Object.fromEntries(Object.entries(raw).map(([k, v]) => [k, v ?? null]))
    if (editing) {
      await api.put(`/purchases/${editing.id}`, payload)
      message.success('采购记录已更新')
    } else {
      await api.post('/purchases', payload)
      message.success('采购登记成功')
    }
    setModalOpen(false)
    load()
  }

  const remove = async (id) => {
    await api.delete(`/purchases/${id}`)
    message.success('已删除')
    load()
  }

  const columns = [
    { title: '食材名称', dataIndex: 'ingredient_name', width: 110, fixed: 'left' },
    { title: '分类', dataIndex: 'category', width: 80, render: (v) => <Tag>{v}</Tag> },
    { title: '供应商', dataIndex: 'supplier_name', width: 170, ellipsis: true },
    { title: '数量', width: 90, render: (_, r) => `${r.quantity}${r.unit}` },
    { title: '单价(元)', dataIndex: 'unit_price', width: 90 },
    { title: '总价(元)', dataIndex: 'total_price', width: 100, render: (v) => <b>{v}</b> },
    { title: '采购日期', dataIndex: 'purchase_date', width: 105 },
    { title: '保质期至', dataIndex: 'expiry_date', width: 105, render: (v) => v || '-' },
    { title: '保质状态', width: 110, render: (_, r) => expiryTag(r.days_to_expiry) },
    { title: '批次号', dataIndex: 'batch_no', width: 140 },
    { title: '合格证号', dataIndex: 'certificate_no', width: 130, render: (v) => v || '-' },
    { title: '验收', dataIndex: 'status', width: 80, render: (v) => (
      <Tag color={v === '合格' ? 'green' : v === '待检' ? 'gold' : 'red'}>{v}</Tag>
    ) },
    { title: '存放位置', dataIndex: 'storage_location', width: 95 },
    {
      title: '操作', width: 120, fixed: 'right',
      render: (_, r) => (
        <Space>
          <a onClick={() => openEdit(r)}>编辑</a>
          <Popconfirm title="确认删除该采购记录？" onConfirm={() => remove(r.id)}>
            <a style={{ color: '#cf1322' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Card
      title="食材采购管理"
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>采购登记</Button>
        </Space>
      }
    >
      <Space wrap style={{ marginBottom: 16 }}>
        <Select allowClear placeholder="分类" style={{ width: 110 }}
          options={CATEGORIES.map((c) => ({ value: c, label: c }))}
          onChange={(v) => setFilters((f) => ({ ...f, category: v }))} />
        <Select allowClear placeholder="验收状态" style={{ width: 110 }}
          options={STATUS.map((s) => ({ value: s, label: s }))}
          onChange={(v) => setFilters((f) => ({ ...f, status: v }))} />
        <DatePicker.RangePicker onChange={(v) => setFilters((f) => ({ ...f, range: v }))} />
        <Input.Search allowClear placeholder="搜索食材名称" style={{ width: 180 }}
          onSearch={(v) => setFilters((f) => ({ ...f, keyword: v || undefined }))} />
      </Space>

      <Table
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={list}
        scroll={{ x: 1400 }}
        pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 条` }}
        rowClassName={(r) => (r.days_to_expiry !== null && r.days_to_expiry < 0 ? 'row-expired' : '')}
      />

      <Modal
        title={editing ? '编辑采购记录' : '采购登记'}
        open={modalOpen}
        onOk={submit}
        onCancel={() => setModalOpen(false)}
        width={720}
        okText="保存"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          <Space.Compact block>
            <Form.Item name="ingredient_name" label="食材名称" rules={[{ required: true, message: '请输入名称' }]} style={{ flex: 1, marginRight: 12 }}>
              <Input placeholder="如：大白菜" />
            </Form.Item>
            <Form.Item name="category" label="分类" rules={[{ required: true, message: '请选择' }]} style={{ width: 130, marginRight: 12 }}>
              <Select options={CATEGORIES.map((c) => ({ value: c, label: c }))} />
            </Form.Item>
            <Form.Item name="supplier_id" label="供应商" style={{ flex: 1.4 }}>
              <Select allowClear showSearch optionFilterProp="label"
                options={suppliers.map((s) => ({ value: s.id, label: s.name }))} />
            </Form.Item>
          </Space.Compact>
          <Space.Compact block>
            <Form.Item name="quantity" label="数量" rules={[{ required: true, message: '必填' }]} style={{ width: 120, marginRight: 12 }}>
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="unit" label="单位" rules={[{ required: true }]} style={{ width: 100, marginRight: 12 }}>
              <Select options={UNITS.map((u) => ({ value: u, label: u }))} />
            </Form.Item>
            <Form.Item name="unit_price" label="单价(元)" rules={[{ required: true, message: '必填' }]} style={{ width: 120, marginRight: 12 }}>
              <InputNumber min={0} step={0.1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="purchase_date" label="采购日期" rules={[{ required: true, message: '必填' }]} style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Space.Compact>
          <Space.Compact block>
            <Form.Item name="production_date" label="生产日期" style={{ flex: 1, marginRight: 12 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="expiry_date" label="保质期至" style={{ flex: 1, marginRight: 12 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="batch_no" label="批次号" style={{ flex: 1, marginRight: 12 }}>
              <Input />
            </Form.Item>
            <Form.Item name="certificate_no" label="检疫/合格证号" style={{ flex: 1 }}>
              <Input />
            </Form.Item>
          </Space.Compact>
          <Space.Compact block>
            <Form.Item name="purchaser" label="采购员" style={{ flex: 1, marginRight: 12 }}>
              <Input />
            </Form.Item>
            <Form.Item name="inspector" label="验收员" style={{ flex: 1, marginRight: 12 }}>
              <Input />
            </Form.Item>
            <Form.Item name="status" label="验收状态" rules={[{ required: true }]} style={{ flex: 1, marginRight: 12 }}>
              <Select options={STATUS.map((s) => ({ value: s, label: s }))} />
            </Form.Item>
            <Form.Item name="storage_location" label="存放位置" style={{ flex: 1 }}>
              <Input placeholder="如：冷库/常温库" />
            </Form.Item>
          </Space.Compact>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      <style>{`.row-expired td { background: #fff1f0 !important; }`}</style>
    </Card>
  )
}
