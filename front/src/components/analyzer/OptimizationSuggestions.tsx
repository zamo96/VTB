import { motion } from 'framer-motion';
import { Card, Typography, Badge, Button, message } from 'antd';
import { RiseOutlined, CodeOutlined, CopyOutlined } from '@ant-design/icons';

interface Suggestion {
  suggestion: string;
  expected_improvement?: string;
  optimized_query?: string;
}

interface OptimizationSuggestionsProps {
  suggestions?: Suggestion[];
}

const { Text } = Typography;

export default function OptimizationSuggestions({
  suggestions = [],
}: OptimizationSuggestionsProps) {
  if (!suggestions.length) return null;

  const copyToClipboard = (text: string) => {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        message.success('Скопировано в буфер обмена!');
      })
      .catch(() => {
        message.error('Не удалось скопировать');
      });
  };

  return (
    <Card
      className="glass-effect border border-slate-600 bg-slate-800/50"
      title={
        <span
          style={{
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <RiseOutlined style={{ color: '#52c41a' }} />
          Предложения по оптимизации
        </span>
      }
    >
      {suggestions.map((suggestion, index) => (
        <motion.div
          key={index}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
          style={{
            border: '1px solid rgba(71, 85, 105, 0.5)',
            borderRadius: '8px',
            padding: '16px',
            backgroundColor: 'rgba(30, 41, 59, 0.3)',
            marginBottom: '12px',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
              marginBottom: '12px',
            }}
          >
            <Text strong style={{ color: '#fff', fontSize: '15px' }}>
              {suggestion.suggestion}
            </Text>
            {suggestion.expected_improvement && (
              <Badge
                color="#52c41a"
                text={<span style={{ color: '#fff' }}>{suggestion.expected_improvement}</span>}
                style={{
                  backgroundColor: 'rgba(82, 196, 26, 0.2)',
                  border: '1px solid rgba(82, 196, 26, 0.3)',
                  padding: '0 8px',
                  fontSize: '12px',
                }}
              />
            )}
          </div>
          {suggestion.optimized_query && (
            <div style={{ marginTop: '8px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  marginBottom: '8px',
                }}
              >
                <CodeOutlined style={{ color: '#fff', fontSize: '14px' }} />
                <Text style={{ fontSize: '13px', color: '#fff' }}>Оптимизированный запрос:</Text>
              </div>
              <div style={{ position: 'relative' }}>
                <pre
                  style={{
                    backgroundColor: '#1e293b',
                    padding: '12px',
                    borderRadius: '6px',
                    border: '1px solid #334155',
                    color: '#fff',
                    fontSize: '13px',
                    marginBottom: 0,
                    overflowX: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all',
                  }}
                >
                  {suggestion.optimized_query}
                </pre>
                <Button
                  type="text"
                  icon={<CopyOutlined style={{ fontSize: '14px', color: '#fff' }} />}
                  onClick={() => copyToClipboard(suggestion.optimized_query!)}
                  style={{
                    position: 'absolute',
                    top: '8px',
                    right: '8px',
                    color: '#fff',
                    padding: '4px',
                    background: 'rgba(30, 41, 59, 0.5)',
                  }}
                />
              </div>
            </div>
          )}
        </motion.div>
      ))}
    </Card>
  );
}
