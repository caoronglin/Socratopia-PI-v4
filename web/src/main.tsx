import React from 'react';
import ReactDOM from 'react-dom/client';
import { App, ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Workspace from './workspace';
import 'antd-mobile/es/global';
import './styles.css';

function Root() {
  const [dark, setDark] = React.useState(false);
  return (
    <ConfigProvider locale={zhCN} theme={{
      algorithm: dark ? theme.darkAlgorithm : theme.defaultAlgorithm,
      token: { colorPrimary: '#3764a8', borderRadius: 10, fontFamily: 'system-ui, sans-serif' },
    }}>
      <App>
        <Workspace dark={dark} onDarkChange={setDark} />
      </App>
    </ConfigProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><Root /></React.StrictMode>,
);
