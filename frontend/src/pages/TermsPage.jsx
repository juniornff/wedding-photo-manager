import LegalLayout from '../components/LegalLayout';

function Section({ title, children }) {
  return (
    <section>
      <h2 className="text-xl font-semibold mb-3" style={{ color: 'var(--color-text)' }}>
        {title}
      </h2>
      <div className="text-gray-700 space-y-3">{children}</div>
    </section>
  );
}

function P({ children }) {
  return <p>{children}</p>;
}

function Li({ children }) {
  return (
    <li className="ml-5 list-disc">
      <span>{children}</span>
    </li>
  );
}

export default function TermsPage() {
  return (
    <LegalLayout title="Condiciones del Servicio" updated="15 de septiembre de 2026">
      <Section title="1. Aceptación de las condiciones">
        <P>
          Al usar la web de la boda (la "Boda Photo"), y especialmente al subir fotos o iniciar
          sesión con Google, aceptas estas condiciones del servicio. Si no estás de acuerdo, por
          favor no utilices la web.
        </P>
      </Section>

      <Section title="2. Descripción del servicio">
        <P>
          La web permite a los invitados y a los novios compartir y ver las fotos de la boda:
          consultar información del evento, subir fotos y mensajes a la galería, descargar fotos y
          participar en los retos del "Fotógrafo Secreto" organizados por mesas. Los administradores
          gestionan el contenido (carrusel, galería, mesas, retos, ganador y usuarios).
        </P>
      </Section>

      <Section title="3. Cuentas de usuario">
        <P>
          No necesitas crear una cuenta: entras con un <strong>apodo</strong> que elijas y un
          identificador anónimo que conserva tu navegador. El inicio de sesión con{' '}
          <strong>Google</strong> es opcional y sirve para recuperar tu identidad en otros
          dispositivos. Debes usar datos veraces y no suplantar a otras personas.
        </P>
      </Section>

      <Section title="4. Contenido que subes">
        <P>
          Eres el único responsable del contenido que subes. Declaras que:
        </P>
        <ul>
          <Li>Eres titular de las fotos que publicas o tienes permiso para publicarlas.</Li>
          <Li>
            Las personas que aparecen en tus fotos (mayores de edad o sus tutores) han consentido su
            publicación dentro de la web.
          </Li>
          <Li>El contenido no es ilegal, ofensivo, difamatorio ni vulnera derechos de terceros.</Li>
          <Li>Los mensajes que acompañan a las fotos son respetuosos y de buen gusto.</Li>
        </ul>
      </Section>

      <Section title="5. Propiedad y licencia">
        <P>
          Conservas todos los derechos sobre las fotos que subes. Al publicarlas, nos otorgas una
          licencia para <strong>almacenarlas, reproducirlas y mostrarlas</strong> dentro de la web,
          incluidas la galería y el tablero público del "Fotógrafo Secreto", durante el tiempo que
          el servicio esté activo.
        </P>
      </Section>

      <Section title="6. Conducta prohibida">
        <ul>
          <Li>Subir contenido ilegal, violento, discriminatorio o sexualmente explícito.</Li>
          <Li>Publicar fotos de otras personas sin su consentimiento.</Li>
          <Li>Intentar dañar, sobrecargar o acceder sin autorización a la web o a sus datos.</Li>
          <Li>
            Suplantar la identidad de otra persona o usar un correo que no te pertenece al iniciar
            sesión con Google.
          </Li>
        </ul>
      </Section>

      <Section title="7. Moderación y retirada de contenido">
        <P>
          Los administradores de la boda pueden revisar, ocultar o eliminar fotos, mensajes o
          cuentas que infrinjan estas condiciones, así como desasignar usuarios de las mesas. Si un
          contenido te afecta o crees que infringe estas reglas, escríbenos al correo de contacto.
        </P>
      </Section>

      <Section title="8. Disponibilidad del servicio">
        <P>
          La web es un servicio para un evento privado y se ofrece con fines de entretenimiento
          entre los invitados. Haremos un esfuerzo razonable por mantenerlo operativo, pero no
          garantizamos una disponibilidad continua ni la ausencia de errores.
        </P>
      </Section>

      <Section title="9. Responsabilidad">
        <P>
          La web se ofrece <strong>"tal cual"</strong>. En la medida máxima permitida por la ley, los
          responsables no serán responsables por daños derivados del uso del servicio ni por el
          contenido publicado por terceros. Debes usar el servicio de forma responsable.
        </P>
      </Section>

      <Section title="10. Cambios en las condiciones">
        <P>
          Podemos actualizar estas condiciones cuando sea necesario. La versión vigente, con su
          fecha de actualización, estará siempre publicada en esta página.
        </P>
      </Section>

      <Section title="11. Contacto">
        <P>
          Para cualquier cuestión sobre estas condiciones, escríbenos a{' '}
          <a href="mailto:juniornff@gmail.com" className="text-[var(--color-accent)] underline">
            juniornff@gmail.com
          </a>
          .
        </P>
      </Section>
    </LegalLayout>
  );
}