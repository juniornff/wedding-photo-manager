import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { AuthProvider } from './context/AuthProvider';
import { SSEProvider } from './context/SSEProvider';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Toaster from './components/Toaster';
import ScrollToTop from './components/ScrollToTop';
import MainPage from './pages/MainPage';
import FotografoSecretoPage from './pages/FotografoSecretoPage';
import SecretDashboardPage from './pages/SecretDashboardPage';
import AdminPage from './pages/AdminPage';
import PrivacyPage from './pages/PrivacyPage';
import TermsPage from './pages/TermsPage';

function NotFound() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4 px-4">
      <h1 className="text-5xl font-bold text-[var(--color-primary)]">404</h1>
      <p className="text-gray-500">Página no encontrada</p>
      <Link
        to="/"
        className="px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white hover:brightness-110 transition"
      >
        Volver al inicio
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ScrollToTop />
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
            <Route path="*" element={<NotFound />} />
          </Routes>
          <Footer />
          <Toaster />
        </SSEProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}