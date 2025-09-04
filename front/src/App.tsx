import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import Layout from './Layout';
import AnalyzerPage from './pages/Analyzer';
import HistoryPage from './pages/History';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/analyzer" element={<AnalyzerPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/" element={<Navigate to="/analyzer" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
