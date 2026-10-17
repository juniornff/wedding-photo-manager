export function showToast({ title, message = '', type = 'info', link = null, duration }) {
  window.dispatchEvent(
    new CustomEvent('app-toast', {
      detail: {
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        title,
        message,
        type,
        link,
        duration,
      },
    })
  );
}
