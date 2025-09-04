import { useState } from 'react';

import QueryEditor from '../components/analyzer/QueryEditor';
import AnalysisResults from '../components/analyzer/AnalysisResults';
import OptimizationSuggestions from '../components/analyzer/OptimizationSuggestions';

import { mockAnalysisResult } from '../mock/mockAnalysisResult';
import mockAnalyses from '../mock/mockAnalyses.json';
import type { Analysis } from '../components/analyzer/types';

const generateId = () => Math.random().toString(36).substr(2, 9);

export default function AnalyzerPage() {
  const [query, setQuery] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  const analyzeQuery = async () => {
    if (!query.trim()) {
      setError('Введите SQL-запрос для анализа');
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      await new Promise(resolve => setTimeout(resolve, 1500));
      const result = mockAnalysisResult(query);

      const newAnalysis: Analysis = {
        id: generateId(),
        created_date: new Date().toISOString(),
        ...result,
      };

      (mockAnalyses as Analysis[]).unshift(newAnalysis);

      setAnalysis(newAnalysis);
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
          {analysis && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <AnalysisResults analysis={analysis} />
              <OptimizationSuggestions suggestions={analysis.optimization_suggestions} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
