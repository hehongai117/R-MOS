import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'

import App from './App'
import { darkTheme } from './styles/theme'
import './styles/index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN} theme={darkTheme}>
      <App />
    </ConfigProvider>
  </React.StrictMode>,
)
