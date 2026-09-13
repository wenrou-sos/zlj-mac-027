import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import App from './App'

dayjs.locale('zh-cn')

ReactDOM.createRoot(document.getElementById('root')).render(
  <ConfigProvider
    locale={zhCN}
    theme={{
      token: { colorPrimary: '#2f7d4f', borderRadius: 6 },
    }}
  >
    <App />
  </ConfigProvider>,
)
