import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppShell from './components/AppShell';
import Overview from './pages/Overview';
import TerminologyExplorer from './pages/TerminologyExplorer';
import MappingIntelligence from './pages/MappingIntelligence';
import FhirWorkspace from './pages/FhirWorkspace';
import Settings from './pages/Settings';
import './index.css';

const qc = new QueryClient({ defaultOptions: { queries: { retry: 2, staleTime: 30000 } } });

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<Navigate to="/overview" replace />} />
            <Route path="/overview" element={<Overview />} />
            <Route path="/terminology" element={<TerminologyExplorer />} />
            <Route path="/mapping" element={<MappingIntelligence />} />
            <Route path="/fhir" element={<FhirWorkspace />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
