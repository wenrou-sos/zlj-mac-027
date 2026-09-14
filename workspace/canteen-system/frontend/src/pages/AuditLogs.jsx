import React, { useEffect, useState } from 'react'
import { Button, Card, DatePicker, Input, Select, Space, Table, Tag } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api'

const ACTIONS = [
  '登录', '留样登记', '留样销毁', '删除留样',
  '采购登记', '采购修改', '采购作废', '供应商登记', '供应商删除',
  '人员登记', '人员修改', '人员删除',
  '异常上报', '下达整改', '完成整改', '验收整改', '关闭工单', '删除工单',
  '手动巡检', '修改巡检配置',
]

const actionColor = (a) => {
  if (a.includes('销毁') || a.includes('删除') || a.includes('作废')) return 'red'
  if (a.includes('验收') || a.includes('关闭')) return 'green'
  if (a.includes('巡检') || a.includes('配置')) return 'purple'
  return 'blue'
}

export default function AuditLogs() {
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({})

  const load = async () => {
    setLoading(true)
    try {
      const params = {}
      if (filters.action) params.action = filters.action
      if (filters.keyword) params.keyword = filters.keyword
      if (filters.range?.[0]) params.date_from = filters.range[0].format('YYYY-MM-DD')
      if (filters.range?.[1]) params.date_to = filters.range[1].format('YYYY-MM-DD')
      setList(await api.get('/audit-logs', { params }))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [filters])

  const columns = [
    { title: '时间', dataIndex: 'created_at', width: 165, render: (v) => dayjs(v).format('YYYY-MM-DD HH:mm:ss') },
    { title: '操作人', dataIndex: 'user_name', width: 90 },
    { title: '账号', dataIndex: 'username', width: 100 },
    { title: '岗位', dataIndex: 'role_name', width: 115, render: (v) => <Tag>{v}</Tag> },
    { title: '操作', dataIndex: 'action', width: 105, render: (v) => <Tag color={actionColor(v)}>{v}</Tag> },
    { title: '对象', width: 120, render: (_, r) => (r.target_type ? `${r.target_type}#${r.target_id ?? '-'}` : '-') },
    { title: '明细', dataIndex: 'detail', ellipsis: true },
  ]

  return (
    <Card
      title="操作日志（谁在什么时候做了什么）"
      extra={<Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>}
    >
      <Space wrap style={{ marginBottom: 16 }}>
        <Select allowClear placeholder="操作类型" style={{ width: 140 }}
          options={ACTIONS.map((a) => ({ value: a, label: a }))}
          onChange={(v) => setFilters((f) => ({ ...f, action: v }))} />
        <DatePicker.RangePicker onChange={(v) => setFilters((f) => ({ ...f, range: v }))} />
        <Input.Search allowClear placeholder="搜索操作人/明细" style={{ width: 200 }}
          onSearch={(v) => setFilters((f) => ({ ...f, keyword: v || undefined }))} />
      </Space>

      <Table
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={list}
        pagination={{ pageSize: 15, showTotal: (t) => `共 ${t} 条` }}
      />
    </Card>
  )
}
