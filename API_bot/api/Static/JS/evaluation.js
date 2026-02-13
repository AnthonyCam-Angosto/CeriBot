// Accessible 5-star widget: click/hover/keyboard support + optional POST to backend.
// Place this file at API_bot\api\Static\JS/evaluation.js

(function () {
  const group = document.getElementById('starGroup');
  const stars = Array.from(group.querySelectorAll('.star'));
  const feedback = document.getElementById('feedback');
  const submitBtn = document.getElementById('submitBtn');
  const clearBtn = document.getElementById('clearBtn');

  let current = 0; // selected rating (0 = none)
  let hoverValue = 0;

  function updateVisuals(value) {
    stars.forEach(s => {
      const v = Number(s.dataset.value);
      const filled = v <= value;
      s.classList.toggle('filled', filled);
      s.setAttribute('aria-checked', String(v === value));
    });
    feedback.textContent = value === 0 ? 'No rating yet' : `You selected ${value} star${value > 1 ? 's' : ''}`;
  }

  function setRating(value, send = false) {
    current = value;
    updateVisuals(current);
    // Optionally send immediately:
    if (send) sendRating(current);
  }

  function preview(value) {
    hoverValue = value;
    updateVisuals(value);
  }

  function clearPreview() {
    hoverValue = 0;
    updateVisuals(current);
  }

  // Click / tap handlers
  stars.forEach(s => {
    s.addEventListener('click', (e) => {
      const v = Number(s.dataset.value);
      setRating(v);
    });

    s.addEventListener('mouseover', () => {
      preview(Number(s.dataset.value));
    });
    s.addEventListener('focus', () => {
      preview(Number(s.dataset.value));
    });
    s.addEventListener('mouseout', clearPreview);
    s.addEventListener('blur', clearPreview);

    // keyboard on each star: Space/Enter select
    s.addEventListener('keydown', (ev) => {
      if (ev.key === ' ' || ev.key === 'Enter') {
        ev.preventDefault();
        setRating(Number(s.dataset.value));
      }
    });
  });

  // radiogroup keyboard: arrows and number keys
  group.addEventListener('keydown', (e) => {
    const max = stars.length;
    if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
      e.preventDefault();
      setRating(Math.min(max, current + 1 || 1));
      stars[current - 1]?.focus();
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
      e.preventDefault();
      setRating(Math.max(1, current - 1));
      stars[current - 1]?.focus();
      if (current === 0) { setRating(0); }
    } else if (/^[1-5]$/.test(e.key)) {
      setRating(Number(e.key));
      stars[Number(e.key) - 1].focus();
    } else if (e.key === 'Home') {
      setRating(1); stars[0].focus();
    } else if (e.key === 'End') {
      setRating(max); stars[max - 1].focus();
    }
  });

  // Submit rating to backend endpoint (adjust URL as needed)
  async function sendRating(value) {
    if (!value || value < 1) {
      feedback.textContent = 'Please select at least 1 star before submitting.';
      return;
    }
    feedback.textContent = 'Sending...';

    try {
      const res = await fetch('/api/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating: value })
      });

      if (!res.ok) throw new Error(`Status ${res.status}`);
      const json = await res.json().catch(() => ({}));
      feedback.textContent = (json && json.message) ? json.message : 'Thank you — your rating has been recorded.';
    } catch (err) {
      console.error('Submit failed', err);
      feedback.textContent = 'Could not send rating. It has been saved locally.';
      // Fallback: save locally
      const pending = JSON.parse(localStorage.getItem('pending_ratings') || '[]');
      pending.push({ rating: value, ts: Date.now() });
      localStorage.setItem('pending_ratings', JSON.stringify(pending));
    }
  }

  submitBtn.addEventListener('click', () => {
    sendRating(current);
  });

  clearBtn.addEventListener('click', () => {
    current = 0;
    updateVisuals(current);
  });

  // Initialize visuals
  updateVisuals(0);

  // Optional: resend any pending ratings on load
  window.addEventListener('load', async () => {
    const pending = JSON.parse(localStorage.getItem('pending_ratings') || '[]');
    if (pending.length === 0) return;
    for (const item of pending.slice()) {
      try {
        const r = await fetch('/api/evaluate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ rating: item.rating, ts: item.ts })
        });
        if (r.ok) {
          // remove first pending
          pending.shift();
          localStorage.setItem('pending_ratings', JSON.stringify(pending));
        } else break;
      } catch {
        break;
      }
    }
  });
})();