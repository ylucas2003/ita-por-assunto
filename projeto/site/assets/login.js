const RA_LIST_URL = 'assets/allowed-ras.json';
const LOGIN_STORAGE_KEY = 'banco-user-ra';
let allowedRAs = null;

function toggleRA() {
  const input = document.getElementById('ra');
  const eye = document.getElementById('ra-eye');
  const showing = input.type === 'text';
  input.type = showing ? 'password' : 'text';
  eye.innerHTML = showing
    ? '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>'
    : '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>';
}

function setLoginError(message) {
  const error = document.getElementById('login-error');
  if (!error) return;
  error.textContent = message || '';
}

async function loadAllowedRAs() {
  if (allowedRAs) return allowedRAs;
  try {
    const response = await fetch(RA_LIST_URL);
    if (!response.ok) throw new Error('Falha ao carregar lista de RAs');
    allowedRAs = await response.json();
    return allowedRAs;
  } catch (err) {
    allowedRAs = [];
    console.error(err);
    return allowedRAs;
  }
}

async function submitLogin(e) {
  e.preventDefault();
  setLoginError('');
  const email = document.getElementById('email').value.trim();
  const ra = document.getElementById('ra').value.trim();
  const btn = document.querySelector('.submit span');
  if (!email || !ra) {
    setLoginError('Preencha e-mail e RA para entrar.');
    return false;
  }

  btn.textContent = 'Validando...';
  const allowed = await loadAllowedRAs();
  const isAllowed = new Set(allowed).has(ra);

  if (!isAllowed) {
    setLoginError('RA não autorizado. Verifique se o RA consta no banco.');
    btn.textContent = 'Acessar o banco';
    return false;
  }

  sessionStorage.setItem(LOGIN_STORAGE_KEY, ra);
  window.location.href = 'banco_unificado.html';
  return false;
}

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('login-form');
  if (form) form.addEventListener('submit', submitLogin);
  const toggle = document.getElementById('ra-toggle');
  if (toggle) toggle.addEventListener('click', toggleRA);
});
