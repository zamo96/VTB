import type { Analysis } from '../components/analyzer/types';

export const mockAnalysisResult = (query: string): Omit<Analysis, 'id' | 'created_date'> => {
  const complexity_score = Math.min(2 + Math.floor(query.length / 100), 10);
  const estimated_cost = complexity_score * 15 + Math.random() * 20;
  const execution_time = complexity_score * 30 + Math.random() * 100;

  return {
    query,
    estimated_cost,
    execution_time: Math.round(execution_time),
    complexity_score,
    recommendations: [
      {
        type: 'critical',
        title: 'Отсутствует индекс на условие WHERE',
        description:
          'Добавьте индекс на поля, используемые в WHERE, чтобы избежать full table scan.',
        impact: 'high',
      },
      {
        type: 'optimization',
        title: 'Оптимизация JOIN',
        description: 'Рассмотрите порядок таблиц в JOIN: более узкие результаты должны быть слева.',
        impact: 'medium',
      },
    ],
    performance_insights: {
      scan_operations: ['Sequential Scan on users (cost=1200)'],
      index_usage: 'Не используется ни один индекс',
      join_operations: ['Nested Loop Join (users → orders)'],
      potential_bottlenecks: ['Большое количество строк после фильтрации', 'Медленный JOIN'],
    },
    optimization_suggestions: [
      {
        suggestion: 'Добавить индекс',
        optimized_query: `CREATE INDEX CONCURRENTLY idx_users_email ON users(email);`,
        expected_improvement: 'Ускорение на 60%',
      },
      {
        suggestion: 'Переписать с CTE',
        optimized_query: `WITH filtered_users AS (SELECT id FROM users WHERE status = 'active') SELECT * FROM filtered_users u JOIN orders o ON u.id = o.user_id;`,
        expected_improvement: 'Снижение стоимости на 45%',
      },
    ],
  };
};
