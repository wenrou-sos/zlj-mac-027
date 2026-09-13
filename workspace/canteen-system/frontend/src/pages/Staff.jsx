import React, { useEffect, useState } from 'react'
import {
  Alert, Button, Card, DatePicker, Form, Input, Modal, Popconfirm,
  Select, Space, Table, Tag, message,
} from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api'

const POSITIONS = ['厨师长', '厨师', '面点师', '帮厨', '洗碗工', '采购员', '仓管员', '服务员']

function certTag(days) {
  if (days === null || days === undefined) return <Tag color="red">未登记</Tag>
  if (days < 0) return <Tag color="red">已过期{-days}天</Tag>
  if (days <= 30) return <Tag color="orange">{days}天后到期</Tag>
  return <Tag color="green">剩余{days}天</Tag>
}

export default function StaffPage() {
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({})
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      setList(await api.get('/staff', { params: filters }))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [filters])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ status: '在职', gender: '男' })
    setModalOpen(true)
  }

  const openEdit = (record) => {
    setEditing(record)
    form.setFieldsValue({
      ...record,
      hire_date: record.hire_date ? dayjs(record.hire_date) : null,
      cert_issue_date: record.cert_issue_date ? dayjs(record.cert_issue_date) : null,
      cert_expiry_date: record.cert_expiry_date ? dayjs(record.cert_expiry_date) : null,
    })
    setModalOpen(true)
  }

  const submit = async () => {
    const values = await form.validateFields()
    const payload = {
      ...values,
      hire_date: values.hire_date?.format('YYYY-MM-DD'),
      cert_issue_date: values.cert_issue_date?.format('YYYY-MM-DD'),
      cert_expiry_date: values.cert_expiry_date?.format('YYYY-MM-DD'),
    }
    if (editing) {
      await api.put(`/staff/${editing.id}`, payload)
      message.success('人员信息已更新')
    } else {
      await api.post('/staff', payload)
      message.success('人员登记成功')
    }
    setModalOpen(false)
    load()
  }

  const expired = list.filter((s) => s.status === '在职' && s.cert_days_remaining !== null && s.cert_days_remaining < 0)
  const expiring = list.filter((s) => s.status === '在职' && s.cert_days_remaining !== null && s.cert_days_remaining >= 0 && s.cert_days_remaining <= 30)

  const columns = [
    { title: '姓名', dataIndex: 'name', width: 90, fixed: 'left' },
    { title: '性别', dataIndex: 'gender', width: 60 },
    { title: '岗位', dataIndex: 'position', width: 90, render: (v) => <Tag>{v}</Tag> },
    { title: '联系电话', dataIndex: 'phone', width: 120 },
    { title: '入职日期', dataIndex: 'hire_date', width: 105 },
    { title: '健康证编号', dataIndex: 'health_cert_no', width: 130, render: (v) => v || '-' },
    { title: '发证日期', dataIndex: 'cert_issue_date', width: 105, render: (v) => v || '-' },
    { title: '有效期至', dataIndex: 'cert_expiry_date', width: 105, render: (v) => v || '-' },
    { title: '证件状态', width: 120, render: (_, r) => certTag(r.cert_days_remaining) },
    { title: '在职状态', dataIndex: 'status', width: 90, render: (v) => (
      <Tag color={v === '在职' ? 'green' : 'default'}>{v}</Tag>
    ) },
    {
      title: '操作', width: 120, fixed: 'right',
      render: (_, r) => (
        <Space>
          <a onClick={() => openEdit(r)}>编辑</a>
          <Popconfirm title="确认删除该人员？" onConfirm={async () => { await api.delete(`/staff/${r.id}`); message.success('已删除'); load() }}>
            <a style={{ color: '#cf1322' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Card
      title="从业人员健康证管理"
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>人员登记</Button>
        </Space>
      }
    >
      {(expired.length > 0 || expiring.length > 0) && (
        <Alert
          style={{ marginBottom: 16 }}
          type={expired.length > 0 ? 'error' : 'warning'}
          showIcon
          message={
            expired.length > 0
              ? `${expired.map((s) => s.name).join('、')} 的健康证已过期，须立即调离岗位！`
              : `${expiring.map((s) => s.name).join('、')} 的健康证将在30天内到期，请安排体检换证`
          }
        />
      )}

      <Space wrap style={{ marginBottom: 16 }}>
        <Select allowClear placeholder="岗位" style={{ width: 110 }}
          options={POSITIONS.map((p) => ({ value: p, label: p }))}
          onChange={(v) => setFilters((f) => ({ ...f, position: v }))} />
        <Select allowClear placeholder="在职状态" style={{ width: 110 }}
          options={['在职', '离职'].map((s) => ({ value: s, label: s }))}
          onChange={(v) => setFilters((f) => ({ ...f, status: v }))} />
        <Input.Search allowClear placeholder="搜索姓名" style={{ width: 160 }}
          onSearch={(v) => setFilters((f) => ({ ...f, keyword: v || undefined }))} />
      </Space>

      <Table
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={list}
        scroll={{ x: 1150 }}
        pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 条` }}
        rowClassName={(r) => (r.status === '在职' && r.cert_days_remaining !== null && r.cert_days_remaining < 0 ? 'row-expired' : '')}
      />

      <Modal
        title={editing ? '编辑人员信息' : '人员登记'}
        open={modalOpen}
        onOk={submit}
        onCancel={() => setModalOpen(false)}
        width={680}
        okText="保存"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          <Space.Compact block>
            <Form.Item name="name" label="姓名" rules={[{ required: true, message: '请输入姓名' }]} style={{ flex: 1, marginRight: 12 }}>
              <Input />
            </Form.Item>
            <Form.Item name="gender" label="性别" style={{ width: 90, marginRight: 12 }}>
              <Select options={['男', '女'].map((g) => ({ value: g, label: g }))} />
            </Form.Item>
            <Form.Item name="position" label="岗位" rules={[{ required: true, message: '请选择' }]} style={{ flex: 1, marginRight: 12 }}>
              <Select options={POSITIONS.map((p) => ({ value: p, label: p }))} />
            </Form.Item>
            <Form.Item name="status" label="在职状态" rules={[{ required: true }]} style={{ width: 110 }}>
              <Select options={['在职', '离职'].map((s) => ({ value: s, label: s }))} />
            </Form.Item>
          </Space.Compact>
          <Space.Compact block>
            <Form.Item name="id_card" label="身份证号" style={{ flex: 1.4, marginRight: 12 }}>
              <Input maxLength={18} />
            </Form.Item>
            <Form.Item name="phone" label="联系电话" style={{ flex: 1, marginRight: 12 }}>
              <Input />
            </Form.Item>
            <Form.Item name="hire_date" label="入职日期" style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Space.Compact>
          <Space.Compact block>
            <Form.Item name="health_cert_no" label="健康证编号" style={{ flex: 1, marginRight: 12 }}>
              <Input placeholder="如：JK2025A0001" />
            </Form.Item>
            <Form.Item name="cert_issue_date" label="发证日期" style={{ flex: 1, marginRight: 12 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="cert_expiry_date" label="有效期至（健康证有效期1年）" style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Space.Compact>
        </Form>
      </Modal>

      <style>{`.row-expired td { background: #fff1f0 !important; }`}</style>
    </Card>
  )
}
