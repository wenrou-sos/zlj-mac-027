import React, { useState } from 'react'
import { Button, Card, Form, Input, Typography, message } from 'antd'
import { LockOutlined, UserOutlined } from '@ant-design/icons'
import api from '../api'
import { setAuth } from '../auth'

const demoAccounts = [
  { u: 'admin', p: 'admin123', label: '食品安全管理员（全部权限）' },
  { u: 'keeper', p: 'keeper123', label: '留样人（留样登记/销毁）' },
  { u: 'purchaser', p: 'purchaser123', label: '采购员（采购/供应商）' },
  { u: 'viewer', p: 'viewer123', label: '检查人员（只读）' },
]

export default function Login({ onLogin }) {
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const submit = async (values) => {
    setLoading(true)
    try {
      const res = await api.post('/auth/login', values)
      setAuth(res.token, res.user)
      message.success(`欢迎，${res.user.name}（${res.user.role_name}）`)
      onLogin(res.user)
    } catch {
      /* 拦截器已提示错误 */
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg, #2f7d4f 0%, #1a4d2e 100%)',
    }}>
      <Card style={{ width: 400, boxShadow: '0 8px 24px rgba(0,0,0,0.15)' }}
        title={<div style={{ textAlign: 'center', fontSize: 18 }}>🍚 学校食堂食品安全管理系统</div>}>
        <Form form={form} onFinish={submit} size="large">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>登 录</Button>
        </Form>
        <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginTop: 16, marginBottom: 0 }}>
          演示账号（点击填充）：
          {demoAccounts.map((a) => (
            <div key={a.u} style={{ marginTop: 4 }}>
              <a onClick={() => form.setFieldsValue({ username: a.u, password: a.p })}>{a.u}</a>
              <span> — {a.label}</span>
            </div>
          ))}
        </Typography.Paragraph>
      </Card>
    </div>
  )
}
