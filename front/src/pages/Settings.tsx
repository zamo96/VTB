import { useState } from 'react';
import { Button, Card, Form, Input, InputNumber, Typography, message } from 'antd';

const { Title, Paragraph } = Typography;

type DbSettings = {
  host: string;
  port: number;
  database: string;
  user: string;
  password: string;
};

export default function SettingsPage() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form] = Form.useForm<DbSettings>();
  const [messageApi, contextHolder] = message.useMessage();

  const testConnection = async () => {
    try {
      const MESSAGE_KEY = 'db-test-connection';
      let values: DbSettings | null = null;
      try {
        values = await form.validateFields();
      } catch {
        messageApi.error({ content: 'Заполните все поля', key: 'db-test-validation' });
        return;
      }
      setIsSubmitting(true);
      messageApi.open({ type: 'loading', content: 'Проверка подключения…', key: MESSAGE_KEY, duration: 0 });
      const response = await fetch('http://127.0.0.1:8000/api/settings/db/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      if (!response.ok) {
        let errorMessage = 'Подключение не удалось';
        try {
          const contentType = response.headers.get('content-type') || '';
          if (contentType.includes('application/json')) {
            const data = await response.json();
            if (data && typeof data.detail === 'string' && data.detail.trim()) {
              errorMessage = data.detail;
            }
          } else {
            const text = await response.text();
            if (text && text.trim()) errorMessage = text;
          }
        } catch {
          // игнорируем ошибки парсинга, используем дефолтное сообщение
        }
        throw new Error(errorMessage);
      }
      localStorage.setItem('dbSettings', JSON.stringify(values));
      messageApi.success({ content: 'Подключение успешно. Настройки сохранены', key: MESSAGE_KEY });
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Неизвестная ошибка';
      messageApi.error({ content: errorMessage, key: 'db-test-connection' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        padding: '24px',
        backgroundColor: '#0f172a',
      }}
    >
      {contextHolder}
      <div style={{ maxWidth: '900px', margin: '0 auto' }}>
        <div style={{ marginBottom: '24px' }}>
          <Title level={2} style={{ color: '#e2e8f0', marginBottom: 0 }}>
            Настройки подключения к БД
          </Title>
          <Paragraph style={{ color: '#94a3b8', marginTop: 8 }}>
            Укажите параметры подключения. Бэкенд будет использовать их для соединения с целевой базой данных.
          </Paragraph>
        </div>

        <Card className="glass-effect border border-slate-600" style={{ backgroundColor: 'rgba(30, 41, 59, 0.5)' }}>
          <div style={{ padding: '16px' }}>
            <Form<DbSettings>
              form={form}
              layout="vertical"
              initialValues={{ port: 5432 }}
              requiredMark={false}
            >
              <Form.Item name="host" label={<span style={{ color: '#e2e8f0' }}>Хост</span>} rules={[{ required: true, message: 'Укажите хост' }]}>
                <Input placeholder="localhost" />
              </Form.Item>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <Form.Item name="port" label={<span style={{ color: '#e2e8f0' }}>Порт</span>} rules={[{ required: true, message: 'Укажите порт' }]}>
                  <InputNumber style={{ width: '100%' }} min={1} max={65535} placeholder="5432" />
                </Form.Item>
                <Form.Item name="database" label={<span style={{ color: '#e2e8f0' }}>База данных</span>} rules={[{ required: true, message: 'Укажите базу данных' }]}>
                  <Input placeholder="postgres" />
                </Form.Item>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <Form.Item name="user" label={<span style={{ color: '#e2e8f0' }}>Пользователь</span>} rules={[{ required: true, message: 'Укажите пользователя' }]}>
                  <Input placeholder="postgres" />
                </Form.Item>
                <Form.Item name="password" label={<span style={{ color: '#e2e8f0' }}>Пароль</span>} rules={[{ required: true, message: 'Укажите пароль' }]}>
                  <Input.Password placeholder="••••••••" />
                </Form.Item>
              </div>

              <div style={{ display: 'flex', gap: 12 }}>
                <Button type="primary" onClick={testConnection} loading={isSubmitting}>
                  Проверить подключение
                </Button>
              </div>
            </Form>
          </div>
        </Card>
      </div>
    </div>
  );
}


