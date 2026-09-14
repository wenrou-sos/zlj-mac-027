import React, { useEffect, useState } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { Badge, Button, Layout, List, Menu, Popconfirm, Popover, Space, Tag, Typography } from 'antd'
import {
  BellOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  IdcardOutlined,
  LogoutOutlined,
  ShoppingOutlined,
  UserOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import api from './api'
import { clearAuth, getToken, getUser } from './auth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Purchases from './pages/Purchases'
import Samples from './pages/Samples'
import StaffPage from './pages/Staff'
import Incidents from './pages/Incidents'
import AuditLogs from './pages/AuditLogs'

const { Header, Sider, Content } = Layout

const levelColor = { danger: 'red', warning: 'orange', info: 'blue' }
const levelText = { danger: '紧急', warning: '提醒', info: '提示' }
const pageTitles = {
  '/': '安全总览',
  '/purchases': '食材采购管理',
  '/samples': '食品留样记录',
  '/staff': '从业人员健康证',
  '/incidents': '异常上报与整改跟踪',
  '/audit': '操作日志',
}

function AlertBell() {
  const [alerts, setAlerts] = useState([])

  const load = () => api.get('/alerts').then(setAlerts).catch(() => {})
  useEffect(() => {
    load()
    const timer = setInterval(load, 60000) // 每分钟刷新预警
    return () => clearInterval(timer)
  }, [])

  const content = (
    <div style={{ width: 380, maxHeight: 420, overflow: 'auto' }}>
      <List
        size="small"
        dataSource={alerts}
        locale={{ emptyText: '暂无预警，一切正常 ✅' }}
        renderItem={(a) => (
          <List.Item>
            <div>
              <Tag color={levelColor[a.level]}>{levelText[a.level]}</Tag>
              <Typography.Text strong>{a.title}</Typography.Text>
              <div style={{ color: '#888', fontSize: 12, marginTop: 4 }}>{a.description}</div>
            </div>
          </List.Item>
        )}
      />
    </div>
  )

  return (
    <Popover content={content} title={`实时预警（${alerts.length}）`} trigger="click" placement="bottomRight">
      <Badge count={alerts.filter((a) => a.level === 'danger').length} size="small" offset={[-2, 4]}>
        <Button type="text" icon={<BellOutlined style={{ fontSize: 18, color: '#fff' }} />} />
      </Badge>
    </Popover>
  )
}

function Shell({ user, onLogout }) {
  const location = useLocation()
  const menuItems = [
    { key: '/', icon: <DashboardOutlined />, label: <Link to="/">仪表盘</Link> },
    { key: '/purchases', icon: <ShoppingOutlined />, label: <Link to="/purchases">食材采购</Link> },
    { key: '/samples', icon: <ExperimentOutlined />, label: <Link to="/samples">留样记录</Link> },
    { key: '/staff', icon: <IdcardOutlined />, label: <Link to="/staff">健康证管理</Link> },
    { key: '/incidents', icon: <WarningOutlined />, label: <Link to="/incidents">异常与整改</Link> },
    ...(user.role === 'admin'
      ? [{ key: '/audit', icon: <FileTextOutlined />, label: <Link to="/audit">操作日志</Link> }]
      : []),
  ]
  const selected = menuItems.find((m) => m.key === location.pathname)?.key ?? '/'

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark" width={210}>
        <div style={{ color: '#fff', fontSize: 16, fontWeight: 600, padding: '18px 16px', lineHeight: 1.4 }}>
          🍚 学校食堂
          <br />
          食品安全管理系统
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={[selected]} items={menuItems} />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#2f7d4f',
            padding: '0 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Typography.Text style={{ color: '#fff', fontSize: 15 }}>
            {pageTitles[selected] ?? ''}
          </Typography.Text>
          <Space size="middle">
            <AlertBell />
            <Space size={4}>
              <UserOutlined style={{ color: '#fff' }} />
              <Typography.Text style={{ color: '#fff' }}>{user.name}</Typography.Text>
              <Tag color="gold" style={{ marginLeft: 2 }}>{user.role_name}</Tag>
            </Space>
            <Popconfirm title="确认退出登录？" onConfirm={onLogout} okText="退出" cancelText="取消">
              <Button type="text" icon={<LogoutOutlined style={{ color: '#fff' }} />} />
            </Popconfirm>
          </Space>
        </Header>
        <Content style={{ padding: 20, background: '#f0f2f5' }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/purchases" element={<Purchases />} />
            <Route path="/samples" element={<Samples />} />
            <Route path="/staff" element={<StaffPage />} />
            <Route path="/incidents" element={<Incidents />} />
            {user.role === 'admin' && <Route path="/audit" element={<AuditLogs />} />}
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  )
}

export default function App() {
  const [user, setUser] = useState(getUser())

  if (!user || !getToken()) {
    return <Login onLogin={setUser} />
  }

  const logout = () => {
    clearAuth()
    setUser(null)
  }

  return (
    <BrowserRouter>
      <Shell user={user} onLogout={logout} />
    </BrowserRouter>
  )
}
