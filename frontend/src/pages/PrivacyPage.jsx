import LegalLayout, { Section, P, Li } from '../components/LegalLayout';

export default function PrivacyPage() {
  return (
    <LegalLayout title="Política de Privacidad" updated="15 de septiembre de 2026">
      <Section title="1. Responsable del tratamiento">
        <P>
          Esta web (la "Wedding Photo Manager") es gestionada por los novios, responsables del tratamiento de
          los datos recogidos a través de la misma. Para cualquier consulta puedes escribir a{' '}
          <a href="mailto:juniornff@gmail.com" className="text-[var(--color-accent)] underline">
            juniornff@gmail.com
          </a>
          .
        </P>
      </Section>

      <Section title="2. Datos que recopilamos">
        <ul>
          <Li>
            Si inicias sesión con Google: tu <strong>nombre</strong>, tu <strong>correo
            electrónico</strong> y tu <strong>foto de perfil</strong> (los datos que Google te
            muestra y que tú autorizas al aceptar el inicio de sesión). No recibimos ningún otro
            dato de tu cuenta de Google.
          </Li>
          <Li>
            Si entras como invitado (sin Google): el <strong>apodo o nombre</strong> que tú elijas y
            un <strong>identificador anónimo</strong> generado por el servidor.
          </Li>
          <Li>
            Las <strong>fotos y mensajes</strong> que subas a la galería o a los retos del
            "Fotógrafo Secreto".
          </Li>
          <Li>
            Datos de uso: la fecha de tu primer acceso y, si participas en el Fotógrafo Secreto, la{' '}
            <strong>mesa</strong> que los administradores te asignen o que cojas mediante el código
            QR.
          </Li>
        </ul>
      </Section>

      <Section title="3. Finalidad del tratamiento">
        <ul>
          <Li>Mostrar y compartir las fotos de la boda con los invitados.</Li>
          <Li>Permitir los retos del "Fotógrafo Secreto" organizados por mesas.</Li>
          <Li>
            Identificarte al subir fotos y mostrar tu nombre y foto de perfil si entras con Google.
          </Li>
          <Li>
            Si entras con Google, recuperar tu identidad entre dispositivos para que tus fotos
            queden asociadas a ti.
          </Li>
        </ul>
      </Section>

      <Section title="4. Base legal">
        <P>
          Tratamos tus datos con tu <strong>consentimiento</strong>: al escribir tu apodo o al
          iniciar sesión con Google. Puedes retirar ese consentimiento en cualquier momento
          escribiéndonos al correo de contacto, sin que ello afecte a la licitud del tratamiento
          previo.
        </P>
      </Section>

      <Section title="5. Almacenamiento y conservación">
        <ul>
          <Li>
            Los datos se guardan en un <strong>servidor propio</strong>: las fotos en disco (carpetas
            de fotos y miniaturas) y el resto en una base de datos SQLite.
          </Li>
          <Li>
            Las fotos se conservan mientras la web esté activa o hasta que solicites su eliminación
            o los administradores las borren.
          </Li>
          <Li>
            Cuando se elimina una cuenta de usuario, sus fotos pueden quedar publicadas como{' '}
            <strong>"Anónimo"</strong> (sin vincular a ningún nombre) o eliminarse completamente,
            según decida el administrador.
          </Li>
        </ul>
      </Section>

      <Section title="6. Visibilidad de la información">
        <P>
          <strong>Importante:</strong> la información de la boda, la galería de fotos y el tablero
          público del "Fotógrafo Secreto" son visibles para <strong>cualquier persona que tenga el
          enlace de la web</strong>, sin necesidad de identificarse. Las fotos que subas a la
          galería o a los retos podrán ser vistas por otros invitados. En los retos del Fotógrafo
          Secreto, cada participante ve su propia foto y las de su mesa según la dinámica del juego.
        </P>
      </Section>

      <Section title="7. Compartición con terceros">
        <ul>
          <Li>No vendemos ni cedemos tus datos a terceros con fines comerciales.</Li>
          <Li>
            <strong>Google</strong> interviene únicamente como proveedor de autenticación (inicio de
            sesión). El uso de tus datos por parte de Google se rige por su propia{' '}
            <a
              href="https://policies.google.com/privacy"
              target="_blank"
              rel="noreferrer"
              className="text-[var(--color-accent)] underline"
            >
              Política de Privacidad
            </a>
            .
          </Li>
          <Li>
            La web está alojada en un <strong>servidor privado</strong> de los novios (no se utiliza
            ningún proveedor de hosting externo). Cloudflare actúa únicamente como gestor de dominio
            y DNS, sin almacenar las fotos ni los datos de la web.
          </Li>
          <Li>No utilizamos herramientas de analítica ni de publicidad de terceros.</Li>
        </ul>
      </Section>

      <Section title="8. Tus derechos">
        <P>
          Puedes ejercer tus derechos de <strong>acceso, rectificación, supresión, limitación del
          tratamiento, oposición y portabilidad</strong> sobre tus datos escribiendo a{' '}
          <a href="mailto:juniornff@gmail.com" className="text-[var(--color-accent)] underline">
            juniornff@gmail.com
          </a>
          . Te responderemos en un plazo razonable.
        </P>
      </Section>

      <Section title="9. Almacenamiento local en tu dispositivo">
        <P>
          El navegador guarda un identificador y tu apodo en <strong>localStorage</strong> para
          reconocerte en visitas posteriores. Si eres administrador de la boda, se usa además una{' '}
          <strong>cookie de sesión</strong>. Puedes borrar estos datos en cualquier momento desde la
          configuración de tu navegador.
        </P>
      </Section>

      <Section title="10. Contacto">
        <P>
          Para cualquier pregunta sobre esta política, escríbenos a{' '}
          <a href="mailto:juniornff@gmail.com" className="text-[var(--color-accent)] underline">
            juniornff@gmail.com
          </a>
          .
        </P>
      </Section>
    </LegalLayout>
  );
}