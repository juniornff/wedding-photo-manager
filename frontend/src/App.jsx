import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthProvider';
import { SSEProvider } from './context/SSEProvider';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import MainPage from './pages/MainPage';
import FotografoSecretoPage from './pages/FotografoSecretoPage';
import SecretDashboardPage from './pages/SecretDashboardPage';
import AdminPage from './pages/AdminPage';
import PrivacyPage from './pages/PrivacyPage';
import TermsPage from './pages/TermsPage';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <SSEProvider>
          <Navbar />
          <Routes>
            <Route path="/" element={<MainPage />} />
            <Route path="/fotografo-secreto" element={<SecretDashboardPage />} />
            <Route path="/fotografo-secreto/:qr_code" element={<FotografoSecretoPage />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/privacidad" element={<PrivacyPage />} />
            <Route path="/terminos" element={<TermsPage />} />
          </Routes>
          <Footer />
        </SSEProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}