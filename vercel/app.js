const form = document.getElementById('updateForm');
const buttons = [...document.querySelectorAll('.update-button')];
const passphraseInput = document.getElementById('passphrase');
const message = document.getElementById('message');

function showMessage(text, kind = '') {
  message.className = kind;
  message.textContent = text;
  message.style.display = 'block';
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const mode = event.submitter?.value;
  buttons.forEach((button) => {
    button.disabled = true;
  });
  showMessage('更新を受け付けています…');

  try {
    const response = await fetch('/api/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ passphrase: passphraseInput.value, mode }),
    });
    const result = await response.json();
    showMessage(result.message || '処理結果を確認できませんでした。', result.ok ? 'success' : 'error');
    if (result.ok) {
      passphraseInput.value = '';
    }
  } catch (_error) {
    showMessage('通信エラーが発生しました。時間を置いて再度お試しください。', 'error');
  } finally {
    buttons.forEach((button) => {
      button.disabled = false;
    });
  }
});
