import { useState, useEffect } from 'react';
import { Card, Typography, Badge, Button, message } from 'antd';
import { CodeOutlined, ClockCircleOutlined, RiseOutlined, EyeOutlined } from '@ant-design/icons';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

import mockAnalyses from '../mock/mockAnalyses.json';
import type { Analysis } from '../components/analyzer/types';

const { Title } = Typography;

export default function HistoryPage() {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [selectedAnalysis, setSelectedAnalysis] = useState<Analysis | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    loadAnalyses();
  }, []);

  const loadAnalyses = async () => {
    try {
      await new Promise(resolve => setTimeout(resolve, 800));
      setAnalyses(mockAnalyses as Analysis[]);
    } catch (error) {
      console.error('Ошибка загрузки истории:', error);
      message.error('Не удалось загрузить историю анализов');
    } finally {
      setIsLoading(false);
    }
  };

  const getScoreColor = (score: number): 'green' | 'orange' | 'red' => {
    if (score <= 3) return 'green';
    if (score <= 6) return 'orange';
    return 'red';
  };

  const truncateQuery = (query: string, maxLength = 80): string => {
    return query.length > maxLength ? `${query.substring(0, maxLength)}...` : query;
  };

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          padding: '24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#0f172a',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            color: '#94a3b8',
          }}
        >
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-emerald-500" />
          <span style={{ color: '#e2e8f0' }}>Загрузка истории...</span>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        padding: '24px',
        backgroundColor: '#0f172a',
        color: '#e2e8f0',
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
            История анализов
          </h1>
          <p style={{ fontSize: '18px', color: '#94a3b8' }}>
            Просматривайте результаты предыдущих анализов запросов
          </p>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '24px',
          }}
        >
          <div className="space-y-4">
            <h2
              style={{
                fontSize: '18px',
                fontWeight: '600',
                color: '#e2e8f0',
                marginBottom: '16px',
              }}
            >
              Последние анализы ({analyses.length})
            </h2>

            {analyses.length > 0 ? (
              analyses.map(analysis => (
                <Card
                  key={analysis.id}
                  className={`glass-effect border border-slate-600 cursor-pointer transition-all duration-200 hover:border-emerald-500/50 ${
                    selectedAnalysis?.id === analysis.id
                      ? 'border-emerald-500 bg-emerald-500/5'
                      : ''
                  }`}
                  style={{
                    borderRadius: '8px',
                    backgroundColor: 'rgba(30, 41, 59, 0.5)',
                    marginBottom: '15px',
                    cursor: 'pointer',
                  }}
                  onClick={() => setSelectedAnalysis(analysis)}
                >
                  <div style={{ padding: '16px' }}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                        marginBottom: '12px',
                      }}
                    >
                      <div style={{ flex: 1 }}>
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            marginBottom: '8px',
                          }}
                        >
                          <CodeOutlined style={{ color: '#94a3b8', fontSize: '14px' }} />
                          <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                            {format(new Date(analysis.created_date), 'dd MMMM yyyy, HH:mm', {
                              locale: ru,
                            })}
                          </span>
                        </div>
                        <p
                          style={{
                            fontFamily: 'monospace',
                            fontSize: '13px',
                            backgroundColor: 'rgba(30, 41, 59, 0.5)',
                            padding: '8px',
                            borderRadius: '6px',
                            color: '#cbd5e1',
                            margin: 0,
                          }}
                        >
                          {truncateQuery(analysis.query)}
                        </p>
                      </div>
                      <Badge
                        color={getScoreColor(analysis.complexity_score)}
                        text={`${analysis.complexity_score}/10`}
                        style={{
                          backgroundColor: 'transparent',
                          border: '1px solid',
                          borderColor:
                            getScoreColor(analysis.complexity_score) === 'green'
                              ? '#52c41a'
                              : getScoreColor(analysis.complexity_score) === 'orange'
                                ? '#faad14'
                                : '#f5222d',
                          fontSize: '11px',
                          padding: '0 6px',
                          color: '#e2e8f0',
                        }}
                      />
                    </div>

                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: '13px',
                        color: '#94a3b8',
                      }}
                    >
                      <div style={{ display: 'flex', gap: '12px' }}>
                        <span
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <ClockCircleOutlined style={{ fontSize: '12px', color: '#94a3b8' }} />
                          {analysis.execution_time}мс
                        </span>
                        <span
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <RiseOutlined style={{ fontSize: '12px', color: '#94a3b8' }} />$
                          {analysis.estimated_cost?.toFixed(2)}
                        </span>
                      </div>
                      <Button
                        type="text"
                        icon={<EyeOutlined style={{ color: '#52c41a' }} />}
                        size="small"
                      />
                    </div>
                  </div>
                </Card>
              ))
            ) : (
              <Card
                className="glass-effect border border-slate-600"
                style={{ textAlign: 'center', padding: '32px' }}
              >
                <div
                  style={{
                    width: '64px',
                    height: '64px',
                    margin: '0 auto 16px',
                    backgroundColor: '#334155',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <CodeOutlined style={{ fontSize: '32px', color: '#94a3b8' }} />
                </div>
                <h3
                  style={{
                    fontSize: '18px',
                    fontWeight: '500',
                    color: '#e2e8f0',
                    marginBottom: '8px',
                  }}
                >
                  История пуста
                </h3>
                <p style={{ color: '#94a3b8', fontSize: '14px' }}>
                  Проанализируйте ваш первый запрос, чтобы увидеть историю здесь
                </p>
              </Card>
            )}
          </div>
          <div style={{ position: 'sticky', top: 24 }}>
            {selectedAnalysis ? (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '16px',
                }}
              >
                <h2
                  style={{
                    fontSize: '18px',
                    fontWeight: '600',
                    color: '#e2e8f0',
                  }}
                >
                  Детали анализа
                </h2>
                <Card className="glass-effect border border-slate-600">
                  <div style={{ padding: '16px' }}>
                    <Title level={5} style={{ color: '#e2e8f0', margin: 0 }}>
                      Запрос
                    </Title>
                    <pre
                      style={{
                        backgroundColor: '#1e293b',
                        padding: '16px',
                        borderRadius: '6px',
                        border: '1px solid #334155',
                        color: '#f8fafc',
                        fontSize: '13px',
                        marginTop: '8px',
                        overflowX: 'auto',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-all',
                        margin: 0,
                      }}
                    >
                      {selectedAnalysis.query}
                    </pre>
                  </div>
                </Card>
                <Card className="glass-effect border border-slate-600">
                  <div style={{ padding: '16px' }}>
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr 1fr',
                        gap: '16px',
                        textAlign: 'center',
                      }}
                    >
                      <div>
                        <p style={{ color: '#94a3b8', fontSize: '12px' }}>Стоимость</p>
                        <p
                          style={{
                            fontSize: '20px',
                            fontWeight: 'bold',
                            color: '#e2e8f0',
                            margin: '4px 0',
                          }}
                        >
                          ${selectedAnalysis.estimated_cost.toFixed(2)}
                        </p>
                      </div>
                      <div>
                        <p style={{ color: '#94a3b8', fontSize: '12px' }}>Время</p>
                        <p
                          style={{
                            fontSize: '20px',
                            fontWeight: 'bold',
                            color: '#e2e8f0',
                            margin: '4px 0',
                          }}
                        >
                          {selectedAnalysis.execution_time}мс
                        </p>
                      </div>
                      <div>
                        <p style={{ color: '#94a3b8', fontSize: '12px' }}>Сложность</p>
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '6px',
                            marginTop: '4px',
                          }}
                        >
                          <p
                            style={{
                              fontSize: '20px',
                              fontWeight: 'bold',
                              color:
                                getScoreColor(selectedAnalysis.complexity_score) === 'green'
                                  ? '#52c41a'
                                  : getScoreColor(selectedAnalysis.complexity_score) === 'orange'
                                    ? '#faad14'
                                    : '#f5222d',
                            }}
                          >
                            {selectedAnalysis.complexity_score} / 10
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>
                {selectedAnalysis.recommendations &&
                  selectedAnalysis.recommendations.length > 0 && (
                    <Card className="glass-effect border border-slate-600">
                      <div style={{ padding: '16px' }}>
                        <Title
                          level={5}
                          style={{
                            color: '#e2e8f0',
                            margin: 0,
                            fontSize: '14px',
                          }}
                        >
                          Рекомендации ({selectedAnalysis.recommendations.length})
                        </Title>
                        <div
                          style={{
                            marginTop: '12px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '8px',
                          }}
                        >
                          {selectedAnalysis.recommendations.slice(0, 3).map((rec, idx) => (
                            <div
                              key={idx}
                              style={{
                                padding: '12px',
                                backgroundColor: 'rgba(30, 41, 59, 0.3)',
                                borderRadius: '6px',
                                border: '1px solid rgba(71, 85, 105, 0.5)',
                              }}
                            >
                              <h4
                                style={{
                                  margin: 0,
                                  fontSize: '14px',
                                  fontWeight: '500',
                                  color: '#e2e8f0',
                                }}
                              >
                                {rec.title}
                              </h4>
                              <p
                                style={{
                                  margin: '4px 0 0',
                                  fontSize: '12px',
                                  color: '#94a3b8',
                                }}
                              >
                                {rec.description}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </Card>
                  )}
                {selectedAnalysis.optimization_suggestions &&
                  selectedAnalysis.optimization_suggestions.length > 0 && (
                    <Card className="glass-effect border border-slate-600">
                      <div style={{ padding: '16px' }}>
                        <Title
                          level={5}
                          style={{
                            color: '#e2e8f0',
                            margin: 0,
                            fontSize: '14px',
                          }}
                        >
                          Предложения по оптимизации (
                          {selectedAnalysis.optimization_suggestions.length})
                        </Title>
                        <div
                          style={{
                            marginTop: '12px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '8px',
                          }}
                        >
                          {selectedAnalysis.optimization_suggestions
                            .slice(0, 2)
                            .map((sugg, idx) => (
                              <div
                                key={idx}
                                style={{
                                  padding: '12px',
                                  backgroundColor: 'rgba(16, 185, 129, 0.1)',
                                  borderRadius: '6px',
                                  border: '1px solid rgba(16, 185, 129, 0.2)',
                                }}
                              >
                                <div
                                  style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    marginBottom: '6px',
                                  }}
                                >
                                  <strong
                                    style={{
                                      color: '#e2e8f0',
                                      fontSize: '14px',
                                    }}
                                  >
                                    {sugg.suggestion}
                                  </strong>
                                  {sugg.expected_improvement && (
                                    <Badge
                                      color="#52c41a"
                                      text={sugg.expected_improvement}
                                      style={{
                                        fontSize: '11px',
                                        padding: '0 6px',
                                        border: '1px solid rgba(82, 196, 26, 0.3)',
                                        color: '#e2e8f0',
                                      }}
                                    />
                                  )}
                                </div>
                                <pre
                                  style={{
                                    backgroundColor: '#1e293b',
                                    padding: '8px',
                                    borderRadius: '4px',
                                    border: '1px solid #334155',
                                    color: '#a7f3d0',
                                    fontSize: '12px',
                                    margin: 0,
                                    overflowX: 'auto',
                                  }}
                                >
                                  {sugg.optimized_query}
                                </pre>
                              </div>
                            ))}
                        </div>
                      </div>
                    </Card>
                  )}
              </div>
            ) : (
              <>
                <h2
                  style={{
                    fontSize: '18px',
                    fontWeight: '600',
                    color: '#e2e8f0',
                    marginBottom: '16px',
                  }}
                >
                  Детали анализа
                </h2>
                <Card
                  className="glass-effect border border-slate-600"
                  style={{ textAlign: 'center', padding: '32px' }}
                >
                  <div
                    style={{
                      width: '64px',
                      height: '64px',
                      margin: '0 auto 16px',
                      backgroundColor: '#334155',
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <EyeOutlined style={{ fontSize: '32px', color: '#94a3b8' }} />
                  </div>
                  <h3
                    style={{
                      fontSize: '18px',
                      fontWeight: '500',
                      color: '#e2e8f0',
                      marginBottom: '8px',
                    }}
                  >
                    Выберите анализ
                  </h3>
                  <p style={{ color: '#94a3b8', fontSize: '14px' }}>
                    Кликните на любой анализ слева, чтобы посмотреть детали
                  </p>
                </Card>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
