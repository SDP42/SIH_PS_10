import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppShell from './components/AppShell';
import Overview from './pages/Overview';
import TerminologyExplorer from './pages/TerminologyExplorer';
import MappingIntelligence from './pages/MappingIntelligence';
import AiMappingLab from './pages/AiMappingLab';
import ReviewQueue from './pages/ReviewQueue';
import FhirWorkspace from './pages/FhirWorkspace';
import WhoSync from './pages/WhoSync';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';
import DemoLogin from './pages/DemoLogin';
import Landing from './pages/Landing';
import { DemoAuthProvider, useDemoAuth } from './auth/DemoAuthContext';
import { LanguageProvider } from './i18n/LanguageContext';
import './index.css';

const qc = new QueryClient({ defaultOptions: { queries: { retry: 2, staleTime: 30000 } } });

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useDemoAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <LanguageProvider>
      <DemoAuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<DemoLogin />} />
            <Route element={<RequireAuth><AppShell /></RequireAuth>}>
              <Route path="/overview" element={<Overview />} />
              <Route path="/terminology" element={<TerminologyExplorer />} />
              <Route path="/mapping" element={<MappingIntelligence />} />
              <Route path="/ai-lab" element={<AiMappingLab />} />
              <Route path="/review-queue" element={<ReviewQueue />} />
              <Route path="/fhir" element={<FhirWorkspace />} />
              <Route path="/who-sync" element={<WhoSync />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </DemoAuthProvider>
      </LanguageProvider>
    </QueryClientProvider>
  );
}
