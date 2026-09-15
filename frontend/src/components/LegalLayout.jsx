import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';

export default function LegalLayout({ title, updated, children }) {
  const [couple, setCouple] = useState(null);

  useEffect(() => {
    api('/api/wedding-info')
      .then((info) => setCouple(`${info.novio1_name} y ${info.novio2_name}`))
      .catch(() => setCouple('la organización de la boda'));
  }, []);

  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      <div className="max-w-3xl mx-auto px-4 py-10">
        <Link to="/" className="text-sm text-gray-400 hover:text-[var(--color-accent)] transition">
          ← Volver a la web
        </Link>
        <header className="mt-6 mb-8">
          <h1 className="text-3xl font-bold" style={{ color: 'var(--color-primary)' }}>
            {title}
          </h1>
          <p className="text-sm text-gray-400 mt-2">Última actualización: {updated}</p>
          <p className="text-sm text-gray-500 mt-1">
            Responsable: <strong>{couple}</strong>
          </p>
        </header>
        <div className="text-gray-700 space-y-8 leading-relaxed">{children}</div>
      </div>
    </div>
  );
}