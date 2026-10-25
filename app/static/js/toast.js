let toastContainer = null;

function ensureToastContainer() {
  if (!toastContainer) {
    toastContainer = el("div", { class: "toast-container" });
    document.body.appendChild(toastContainer);
  }
  return toastContainer;
}

function showToast(message, kind = "info") {
  const container = ensureToastContainer();
  const toast = el("div", { class: `toast toast-${kind}` }, [message]);
  container.appendChild(toast);

  requestAnimationFrame(() => toast.classList.add("show"));
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}
