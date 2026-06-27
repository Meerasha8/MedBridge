// Shared small UI helpers: toast dismiss, simple modal open/close.
function dismissToast(el) {
  el.style.transition = "opacity 0.2s";
  el.style.opacity = "0";
  setTimeout(() => el.remove(), 200);
}
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove("hidden");
}
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add("hidden");
}
