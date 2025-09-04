import React from 'react';
import { Card, Button, message } from 'antd';
import { PlayCircleOutlined, CodeOutlined, DatabaseOutlined } from '@ant-design/icons';

interface QueryEditorProps {
  query: string;
  setQuery: (value: string) => void;
  onAnalyze: () => void;
  isAnalyzing: boolean;
}

export default function QueryEditor({ query, setQuery, onAnalyze, isAnalyzing }: QueryEditorProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.ctrlKey && e.key === 'Enter') {
      e.preventDefault();
      if (query.trim()) {
        onAnalyze();
      } else {
        message.warning('Введите SQL-запрос перед анализом.');
      }
    }
  };

  return (
    <Card
      className="glass-effect border border-slate-600 bg-slate-800/50"
      style={{ marginBottom: '24px' }}
    >
      <div style={{ padding: '24px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            marginBottom: '16px',
          }}
        >
          <div
            style={{
              width: '32px',
              height: '32px',
              backgroundColor: 'rgba(16, 185, 129, 0.2)',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <CodeOutlined style={{ color: '#10b981', fontSize: '16px' }} />
          </div>
          <div>
            <h3
              style={{
                margin: 0,
                fontSize: '16px',
                fontWeight: 500,
                color: '#fff',
              }}
            >
              SQL Запрос
            </h3>
            <p style={{ margin: 0, fontSize: '12px', color: '#94a3b8' }}>
              Вставьте ваш PostgreSQL запрос для анализа
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <textarea
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="SELECT * FROM users WHERE created_at > '2024-01-01'..."
            style={{
              minHeight: '200px',
              fontFamily: 'monospace',
              fontSize: '14px',
              padding: '16px',
              borderRadius: '8px',
              border: '1px solid #334155',
              backgroundColor: '#1e293b',
              color: '#f8fafc',
              resize: 'vertical',
              outline: query ? 'none' : undefined,
              boxShadow: query ? '0 0 0 2px rgba(16, 185, 129, 0.2)' : 'none',
            }}
          />
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '12px',
                color: '#94a3b8',
              }}
            >
              <DatabaseOutlined style={{ fontSize: '12px' }} />
              <span>Поддерживается PostgreSQL 15+</span>
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <Button
                type="default"
                size="small"
                onClick={() => setQuery('')}
                disabled={!query.trim() || isAnalyzing}
                style={{
                  borderColor: '#334155',
                  color: '#000000ff',
                }}
              >
                Очистить
              </Button>
              <Button
                type="primary"
                size="small"
                icon={<PlayCircleOutlined />}
                onClick={onAnalyze}
                disabled={!query.trim() || isAnalyzing}
                loading={isAnalyzing}
                style={{
                  backgroundColor: '#10b981',
                  borderColor: '#10b981',
                  color: '000',
                }}
              >
                {isAnalyzing ? 'Анализ...' : 'Анализировать (Ctrl+Enter)'}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
