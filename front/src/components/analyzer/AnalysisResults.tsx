import { motion } from 'framer-motion';
import { Card, Typography, Badge } from 'antd';
import {
  DollarOutlined,
  ClockCircleOutlined,
  RiseOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { Analysis } from './types';

const { Title, Text, Paragraph } = Typography;

const getRecommendationIcon = (type: string) => {
  switch (type) {
    case 'critical':
      return <ExclamationCircleOutlined style={{ color: '#f5222d' }} />;
    case 'warning':
      return <ExclamationCircleOutlined style={{ color: '#faad14' }} />;
    case 'optimization':
      return <ThunderboltOutlined style={{ color: '#52c41a' }} />;
    default:
      return <InfoCircleOutlined style={{ color: '#1890ff' }} />;
  }
};

const getImpactColor = (impact: string) => {
  switch (impact) {
    case 'high':
      return 'red';
    case 'medium':
      return 'orange';
    default:
      return 'blue';
  }
};

export default function AnalysisResults({ analysis }: { analysis: Analysis | null | undefined }) {
  if (!analysis) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card className="glass-effect border border-slate-600 bg-slate-800/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
              <DollarOutlined style={{ fontSize: '18px', color: '#52c41a' }} />
            </div>
            <div>
              <Text style={{ fontSize: '12px', color: '#fff' }}>Стоимость</Text>
              <br />
              <Title level={4} style={{ margin: 0, color: '#fff' }}>
                {analysis.estimated_cost?.toFixed(2) ?? 'N/A'}
              </Title>
            </div>
          </div>
        </Card>
        <Card
          className="glass-effect border border-slate-600 bg-slate-800/50"
          style={{ margin: '10px 0' }}
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-500/20 rounded-lg flex items-center justify-center">
              <ClockCircleOutlined style={{ fontSize: '18px', color: '#faad14' }} />
            </div>
            <div>
              <Text style={{ fontSize: '12px', color: '#fff' }}>Время выполнения</Text>
              <br />
              <Title level={4} style={{ margin: 0, color: '#fff' }}>
                {analysis.execution_time ? `${analysis.execution_time}мс` : 'N/A'}
              </Title>
            </div>
          </div>
        </Card>
        <Card
          className="glass-effect border border-slate-600 bg-slate-800/50"
          style={{ margin: '0 0 30px 0' }}
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
              <RiseOutlined style={{ fontSize: '18px', color: '#1890ff' }} />
            </div>
            <div>
              <Text style={{ fontSize: '12px', color: '#fff' }}>Сложность</Text>
              <br />
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Title level={4} style={{ margin: 0, color: '#fff' }}>
                  {analysis.complexity_score ?? 'N/A'}
                </Title>
                <Badge
                  color={
                    analysis.complexity_score && analysis.complexity_score <= 3
                      ? 'green'
                      : analysis.complexity_score && analysis.complexity_score <= 6
                        ? 'orange'
                        : 'red'
                  }
                  text={
                    <span style={{ color: '#fff' }}>
                      {analysis.complexity_score && analysis.complexity_score <= 3
                        ? 'Низкая'
                        : analysis.complexity_score && analysis.complexity_score <= 6
                          ? 'Средняя'
                          : 'Высокая'}
                    </span>
                  }
                />
              </div>
            </div>
          </div>
        </Card>
      </div>
      {analysis.recommendations && analysis.recommendations.length > 0 && (
        <Card
          className="glass-effect border border-slate-600 mb-6"
          style={{ marginBottom: '24px' }}
          title={
            <span style={{ color: '#fff', margin: '10px 0' }}>
              <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
              Рекомендации
            </span>
          }
        >
          {analysis.recommendations.map((rec, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                padding: '16px',
                backgroundColor: 'rgba(30, 41, 59, 0.5)',
                borderRadius: '8px',
                border: '1px solid rgba(71, 85, 105, 0.5)',
                marginBottom: '12px',
              }}
            >
              {getRecommendationIcon(rec.type)}
              <div style={{ flex: 1 }}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    marginBottom: '4px',
                  }}
                >
                  <Text strong style={{ color: '#fff' }}>
                    {rec.title}
                  </Text>
                  <Badge
                    color={getImpactColor(rec.impact)}
                    text={
                      <span style={{ color: '#fff', fontSize: '12px' }}>
                        {rec.impact === 'high'
                          ? 'Высокое влияние'
                          : rec.impact === 'medium'
                            ? 'Среднее влияние'
                            : 'Низкое влияние'}
                      </span>
                    }
                  />
                </div>
                <Paragraph style={{ margin: 0, fontSize: '14px', color: '#fff' }}>
                  {rec.description}
                </Paragraph>
              </div>
            </motion.div>
          ))}
        </Card>
      )}
      {analysis.performance_insights && (
        <Card
          className="glass-effect border border-slate-600"
          title={
            <span style={{ color: '#fff' }}>
              <RiseOutlined style={{ color: '#1890ff', marginRight: 8 }} />
              Анализ производительности
            </span>
          }
        >
          {analysis.performance_insights.scan_operations?.length > 0 && (
            <div style={{ marginBottom: '24px' }}>
              <Text strong style={{ color: '#fff', display: 'block', marginBottom: '8px' }}>
                Операции сканирования
              </Text>
              {analysis.performance_insights.scan_operations.map((op, idx) => (
                <Paragraph
                  key={idx}
                  style={{
                    fontSize: '13px',
                    backgroundColor: 'rgba(30, 41, 59, 0.3)',
                    padding: '8px',
                    borderRadius: '6px',
                    margin: '6px 0',
                    color: '#fff',
                  }}
                >
                  {op}
                </Paragraph>
              ))}
            </div>
          )}
          {analysis.performance_insights.index_usage && (
            <div style={{ marginBottom: '24px' }}>
              <Text strong style={{ color: '#fff', display: 'block', marginBottom: '8px' }}>
                Использование индексов
              </Text>
              <Paragraph
                style={{
                  fontSize: '13px',
                  backgroundColor: 'rgba(30, 41, 59, 0.3)',
                  padding: '12px',
                  borderRadius: '6px',
                  color: '#fff',
                }}
              >
                {analysis.performance_insights.index_usage}
              </Paragraph>
            </div>
          )}
          {analysis.performance_insights.join_operations?.length > 0 && (
            <div style={{ marginBottom: '24px' }}>
              <Text strong style={{ color: '#fff', display: 'block', marginBottom: '8px' }}>
                JOIN операции
              </Text>
              {analysis.performance_insights.join_operations.map((join, idx) => (
                <Paragraph
                  key={idx}
                  style={{
                    fontSize: '13px',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    border: '1px solid rgba(59, 130, 246, 0.2)',
                    padding: '8px',
                    borderRadius: '6px',
                    margin: '6px 0',
                    color: '#fff',
                  }}
                >
                  {join}
                </Paragraph>
              ))}
            </div>
          )}
          {analysis.performance_insights.potential_bottlenecks?.length > 0 && (
            <div>
              <Text strong style={{ color: '#fff', display: 'block', marginBottom: '8px' }}>
                Потенциальные узкие места
              </Text>
              {analysis.performance_insights.potential_bottlenecks.map((bottleneck, idx) => (
                <Paragraph
                  key={idx}
                  style={{
                    fontSize: '13px',
                    backgroundColor: 'rgba(250, 173, 20, 0.1)',
                    border: '1px solid rgba(250, 173, 20, 0.2)',
                    padding: '8px',
                    borderRadius: '6px',
                    margin: '6px 0',
                    color: '#fff',
                  }}
                >
                  {bottleneck}
                </Paragraph>
              ))}
            </div>
          )}
        </Card>
      )}
    </motion.div>
  );
}
