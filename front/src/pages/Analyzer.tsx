import { useState } from 'react';

import QueryEditor from '../components/analyzer/QueryEditor';

// mockData import removed; using real API call instead
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type MockRecommendation = {
  id: string;
  rule_id: string;
  type: string;
  title: string;
  action?: {
    ddl?: string;
    rewrite_sql_hint?: string;
  };
  expected_gain?: {
    kind: string;
    value: number | null;
    source: string;
  };
  effort?: string;
  confidence?: string;
  evidence?: Array<Record<string, unknown>>;
};

type MockResponse = {
  text: string;
  risk: {
    score: number;
    severity: string;
    drivers: string[];
    confidence_factor: number;
  };
  recommendations: MockRecommendation[];
};

export default function AnalyzerPage() {
  const [query, setQuery] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<MockResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const analyzeQuery = async () => {
    const savedSettingsRaw = localStorage.getItem('dbSettings');
    if (!savedSettingsRaw) {
      setError('Сначала заполните настройки подключения в разделе Настройки.');
      return;
    }

    let dbSettings: unknown;
    try {
      dbSettings = JSON.parse(savedSettingsRaw);
      console.log(dbSettings);
    } catch {
      setError('Настройки подключения повреждены. Пересохраните их в разделе Настройки.');
      return;
    }

    if (!query.trim()) {
      setError('Введите SQL-запрос для анализа');
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      const response = await fetch(
        'http://127.0.0.1:8000/advise/sql?out_format=md&verbosity=full&include_plan=false&include_features=false',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ sql: query, analyze: false }),
        }
      );

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(errText || `HTTP ${response.status}`);
      }

      const data = (await response.json()) as MockResponse;
      setResult(data);
    } catch (err) {
      console.error('Ошибка анализа:', err);
      setError('Произошла ошибка при анализе запроса. Попробуйте еще раз.');
    } finally {
      setIsAnalyzing(false);
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
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        <div style={{ marginBottom: '32px' }}>
          <h1
            style={{
              fontSize: '28px',
              fontWeight: 'bold',
              color: '#e2e8f0',
              marginBottom: '8px',
            }}
          >
            Анализатор PostgreSQL запросов
          </h1>
          <p style={{ fontSize: '18px', color: '#94a3b8' }}>
            Анализируйте производительность и получайте рекомендации по оптимизации ваших SQL
            запросов
          </p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <QueryEditor
            query={query}
            setQuery={setQuery}
            onAnalyze={analyzeQuery}
            isAnalyzing={isAnalyzing}
          />
          {error && (
            <div
              style={{
                backgroundColor: 'rgba(245, 34, 34, 0.1)',
                border: '1px solid rgba(245, 34, 34, 0.2)',
                color: '#f87171',
                padding: '16px',
                borderRadius: '8px',
              }}
            >
              {error}
            </div>
          )}
          {result && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div className="glass-effect border border-slate-600" style={{ backgroundColor: 'rgba(30,41,59,0.5)', padding: '16px', borderRadius: 8 }}>
                <div style={{ color: '#e2e8f0' }}>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      h1: ({ node, ...props }) => (
                        <h1 style={{ fontSize: '28px', fontWeight: 800, margin: '16px 0' }} {...props} />
                      ),
                      h2: ({ node, ...props }) => (
                        <h2 style={{ fontSize: '24px', fontWeight: 700, margin: '14px 0' }} {...props} />
                      ),
                      h3: ({ node, ...props }) => (
                        <h3 style={{ fontSize: '20px', fontWeight: 700, margin: '12px 0' }} {...props} />
                      ),
                      p: ({ node, ...props }) => (
                        <p style={{ margin: '8px 0', lineHeight: 1.6 }} {...props} />
                      ),
                      ul: ({ node, ...props }) => (
                        <ul style={{ listStyleType: 'disc', paddingLeft: '20px', margin: '8px 0' }} {...props} />
                      ),
                      ol: ({ node, ...props }) => (
                        <ol style={{ listStyleType: 'decimal', paddingLeft: '20px', margin: '8px 0' }} {...props} />
                      ),
                      li: ({ node, ...props }) => (
                        <li style={{ margin: '4px 0' }} {...props} />
                      ),
                      code: ({ node, inline, className, children, ...props }: any) => (
                        inline ? (
                          <code
                            style={{
                              background: '#1e293b',
                              padding: '2px 6px',
                              borderRadius: 4,
                              border: '1px solid #334155',
                              color: '#a7f3d0',
                            }}
                            {...props}
                          >
                            {children}
                          </code>
                        ) : (
                          <code
                            style={{
                              display: 'block',
                              whiteSpace: 'pre-wrap',
                              background: '#0b1220',
                              padding: 12,
                              borderRadius: 6,
                              border: '1px solid #334155',
                              color: '#e2e8f0',
                            }}
                            {...props}
                          >
                            {children}
                          </code>
                        )
                      ),
                    }}
                  >
                    {result.text}
                  </ReactMarkdown>
                </div>
              </div>

              <div className="glass-effect border border-slate-600" style={{ backgroundColor: 'rgba(30,41,59,0.5)', padding: '16px', borderRadius: 8 }}>
                <h3 style={{ color: '#e2e8f0', marginTop: 0 }}>Риск</h3>
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', color: '#cbd5e1' }}>
                  <div>Оценка: <strong style={{ color: '#e2e8f0' }}>{result.risk.score}</strong></div>
                  <div>Уровень: <strong style={{ color: '#e2e8f0' }}>{result.risk.severity}</strong></div>
                  <div>Уверенность: <strong style={{ color: '#e2e8f0' }}>{result.risk.confidence_factor}</strong></div>
                </div>
                {result.risk.drivers?.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ color: '#94a3b8', marginBottom: 4 }}>Драйверы:</div>
                    <ul>
                      {result.risk.drivers.map(d => (
                        <li key={d} style={{ color: '#e2e8f0' }}>{d}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {result.recommendations?.length > 0 && (
                <div className="glass-effect border border-slate-600" style={{ backgroundColor: 'rgba(30,41,59,0.5)', padding: '16px', borderRadius: 8 }}>
                  <h3 style={{ color: '#e2e8f0', marginTop: 0 }}>Рекомендации ({result.recommendations.length})</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {result.recommendations.map((rec) => (
                      <div key={rec.id} style={{ border: '1px solid #334155', borderRadius: 6, padding: 12, background: 'rgba(15,23,42,0.4)' }}>
                        <div style={{ color: '#e2e8f0', fontWeight: 600 }}>{rec.title}</div>
                        <div style={{ color: '#94a3b8', fontSize: 12, marginTop: 4 }}>Тип: {rec.type} · Правило: {rec.rule_id}</div>
                        {rec.action?.rewrite_sql_hint && (
                          <div style={{ marginTop: 8 }}>
                            <div style={{ color: '#94a3b8', fontSize: 12 }}>Подсказка по переписыванию:</div>
                            <pre style={{ background: '#1e293b', color: '#e2e8f0', padding: 8, borderRadius: 4, border: '1px solid #334155', whiteSpace: 'pre-wrap' }}>{rec.action.rewrite_sql_hint}</pre>
                          </div>
                        )}
                        {rec.action?.ddl && (
                          <div style={{ marginTop: 8 }}>
                            <div style={{ color: '#94a3b8', fontSize: 12 }}>DDL:</div>
                            <pre style={{ background: '#1e293b', color: '#a7f3d0', padding: 8, borderRadius: 4, border: '1px solid #334155', whiteSpace: 'pre-wrap' }}>{rec.action.ddl}</pre>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
