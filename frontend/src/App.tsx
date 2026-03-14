import { ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Clients from './pages/Clients';
import ClientDetail from './pages/ClientDetail';
import Services from './pages/Services';
import Invoices from './pages/Invoices';
import ClosuresPage from './pages/plugins/ClosuresPage';
import DailyMenusPage from './pages/plugins/DailyMenusPage';
import BroadcastsPage from './pages/plugins/BroadcastsPage';
import InstagramDMPage from './pages/plugins/InstagramDMPage';
import AdvancedCRMPage from './pages/plugins/AdvancedCRMPage';
import AudioTranscriptionPage from './pages/plugins/AudioTranscriptionPage';
import RestaurantBookingsPage from './pages/plugins/RestaurantBookingsPage';
import OwnerAgentPage from './pages/plugins/OwnerAgentPage';
import ConsentFormsPage from './pages/plugins/ConsentFormsPage';
import ShiftViewPage from './pages/plugins/ShiftViewPage';
import VoiceAgentPage from './pages/plugins/VoiceAgentPage';
import BookingsPage from './pages/plugins/BookingsPage';
import RemindersPage from './pages/plugins/RemindersPage';
import { useAuth } from './hooks/useAuth';

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white">Cargando...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<Dashboard />} />
          <Route path="clients" element={<Clients />} />
          <Route path="clients/:slug" element={<ClientDetail />} />
          <Route path="services" element={<Services />} />
          <Route path="invoices" element={<Invoices />} />
          <Route path="plugins/closures" element={<ClosuresPage />} />
          <Route path="plugins/daily-menus" element={<DailyMenusPage />} />
          <Route path="plugins/broadcasts" element={<BroadcastsPage />} />
          <Route path="plugins/instagram-dm" element={<InstagramDMPage />} />
          <Route path="plugins/advanced-crm" element={<AdvancedCRMPage />} />
          <Route path="plugins/audio-transcription" element={<AudioTranscriptionPage />} />
          <Route path="plugins/restaurant-bookings" element={<RestaurantBookingsPage />} />
          <Route path="plugins/owner-agent" element={<OwnerAgentPage />} />
          <Route path="plugins/consent-forms" element={<ConsentFormsPage />} />
          <Route path="plugins/shift-view" element={<ShiftViewPage />} />
          <Route path="plugins/voice-agent" element={<VoiceAgentPage />} />
          <Route path="plugins/bookings" element={<BookingsPage />} />
          <Route path="plugins/reminders" element={<RemindersPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
