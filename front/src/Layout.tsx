import { Link, Outlet, useLocation } from 'react-router-dom';
import { DatabaseOutlined, HistoryOutlined } from '@ant-design/icons';
import { Layout, Menu } from 'antd';
import Title from 'antd/es/typography/Title';

const { Sider, Content } = Layout;

const navigationItems = [
  {
    title: 'Анализатор',
    url: '/analyzer',
    icon: <DatabaseOutlined />,
  },
  {
    title: 'История',
    url: '/history',
    icon: <HistoryOutlined />,
  },
];

export default function AppLayout() {
  const location = useLocation();

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider breakpoint="lg" collapsedWidth="0" theme="dark" style={{ background: '#1e293b' }}>
        <Title level={3} style={{ padding: '10px 0 0 30px', color: '#e2e8f0' }}>
          PgAnalyzer
        </Title>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={navigationItems.map(item => ({
            key: item.url,
            icon: item.icon,
            label: <Link to={item.url}>{item.title}</Link>,
          }))}
          style={{ background: '#1e293b', borderRight: 'none' }}
        />
      </Sider>
      <Layout>
        <Content style={{ background: '#0f172a' }}>
          <div className="p-6 min-h-screen" style={{ color: '#e2e8f0' }}>
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}
