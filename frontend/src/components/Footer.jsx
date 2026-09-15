import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="border-t border-[var(--color-secondary)] py-6 mt-12">
      <div className="max-w-6xl mx-auto px-4 flex flex-col items-center gap-2 sm:flex-row sm:justify-center sm:gap-6 text-sm text-gray-500">
        <Link to="/privacidad" className="hover:text-[var(--color-accent)] transition">
          Política de Privacidad
        </Link>
        <Link to="/terminos" className="hover:text-[var(--color-accent)] transition">
          Términos del Servicio
        </Link>
      </div>
    </footer>
  );
}