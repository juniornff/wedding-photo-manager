import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { SSEProvider } from './context/SSEContext';
import Navbar from './components/Navbar';
import MainPage from './pages/MainPage';
import FotografoSecretoPage from './pages/FotografoSecretoPage';
import SecretDashboardPage from './pages/SecretDashboardPage';
import AdminPage from './pages/AdminPage';

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
          </Routes>
        </SSEProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
