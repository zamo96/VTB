export interface Recommendation {
  type: 'critical' | 'warning' | 'info' | 'optimization';
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
}

export interface PerformanceInsights {
  scan_operations: string[];
  index_usage: string;
  join_operations: string[];
  potential_bottlenecks: string[];
}

export interface OptimizationSuggestion {
  suggestion: string;
  optimized_query: string;
  expected_improvement: string;
}

export interface Analysis {
  id: string;
  query: string;
  created_date: string;
  estimated_cost: number;
  execution_time: number;
  complexity_score: number;
  recommendations: Recommendation[];
  performance_insights: PerformanceInsights;
  optimization_suggestions: OptimizationSuggestion[];
}
