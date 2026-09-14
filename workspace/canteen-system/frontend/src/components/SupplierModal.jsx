import React, { useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Popconfirm, Space, Table, Tag, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api'
import { hasRole } from '../auth'
import VoidModal from './VoidModal'

/** 供应商管理弹窗：登记新供应商、停用/恢复（含全部历史记录） */
export default function SupplierModal({ open, onClose, onChanged }) {
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(false)
  const [voidTarget, setVoidTarget] = useState(null)
  const [form] = Form.useForm()
  const canEdit = hasRole('admin', 'purchaser')
  const isAdmin = hasRole('admin')

  const load = async () => {
    setLoading(true)
    try {
      setList(await api.get('/suppliers', { params: { view: 'all' } }))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open) load()
  }, [open])

  const add = async () => {
    const values = await form.validateFields()
    await api.post('/suppliers', values)
    message.success('供应商已登记')
    form.resetFields()
    load()
    onChanged?.()
  }

  const doVoid = async (reason) => {
    await api.post(`/suppliers/${voidTarget.id}/void`, { reason })
    message.success('已停用，历史采购记录保留可查')
    setVoidTarget(null)
    load()
    onChanged?.()
  }

  const doRestore = async (id) => {
    await api.post(`/suppliers/${id}/restore`)
    message.success('已恢复')
    load()
    onChanged?.()
  }

  const columns = [
    { title: '名称', dataIndex: 'name', width: 180, ellipsis: true },
    { title: '联系人', dataIndex: 'contact', width: 80 },
    { title: '电话', dataIndex: 'phone', width: 115 },
    { title: '许可证号', dataIndex: 'license_no', width: 150, render: (v) => v || '-' },
    {
      title: '状态', width: 150,
      render: (_, r) => r.voided_at
        ? <Tag color="red">已停用 {dayjs(r.voided_at).format('MM-DD')}</Tag>
        : <Tag color="green">有效</Tag>,
    },
    { title: '停用原因', dataIndex: 'void_reason', width: 140, ellipsis: true, render: (v) => v || '-' },
    {
      title: '操作', width: 80,
      render: (_, r) => {
        if (r.voided_at) {
          return isAdmin ? (
            <Popconfirm title="确认恢复该供应商？" onConfirm={() => doRestore(r.id)}>
              <a>恢复</a>
            </Popconfirm>
          ) : '-'
        }
        return canEdit ? <a style={{ color: '#cf1322' }} onClick={() => setVoidTarget(r)}>停用</a> : '-'
      },
    },
  ]

  return (
    <Modal title="供应商管理" open={open} onCancel={onClose} footer={null} width={900}>
      {canEdit && (
        <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
          <Form.Item name="name" rules={[{ required: true, message: '必填' }]}>
            <Input placeholder="供应商名称*" style={{ width: 180 }} />
          </Form.Item>
          <Form.Item name="contact">
            <Input placeholder="联系人" style={{ width: 100 }} />
          </Form.Item>
          <Form.Item name="phone">
            <Input placeholder="电话" style={{ width: 130 }} />
          </Form.Item>
          <Form.Item name="license_no">
            <Input placeholder="许可证号" style={{ width: 160 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" icon={<PlusOutlined />} onClick={add}>登记</Button>
          </Form.Item>
        </Form>
      )}
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={list}
        pagination={{ pageSize: 8 }}
        scroll={{ x: 900 }}
      />
      <VoidModal
        open={!!voidTarget}
        title={`停用供应商：${voidTarget?.name ?? ''}`}
        label="停用原因"
        onOk={doVoid}
        onCancel={() => setVoidTarget(null)}
      />
    </Modal>
  )
}
