(function () {
  const tip = document.createElement('div');
  tip.className = 'tip';
  document.body.appendChild(tip);

  const AUTO = [
    ['.daypick label', e => 'Click to toggle ' + e.textContent.trim()],
    ['.tl-item.next', () => 'Your next upcoming shift'],
    ['.donut', () => 'Resilience Index: coverage, buffer, skills and rules'],
    ['.cell', () => 'Assigned staff holding this skill'],
    ['.chip.cert.expired', () => 'Certification expired. Renew in Training Academy'],
    ['.badge.bad', () => 'Needs attention'],
    ['.btn.d', e => e.textContent.trim() ? e.textContent.trim() + ' (this changes the schedule)' : ''],
    ['.nav-item', e => 'Open ' + e.textContent.replace(/\d+$/, '').trim()],
  ];
  AUTO.forEach(([sel, fn]) =>
    document.querySelectorAll(sel).forEach(el => {
      if (!el.dataset.tip && !el.title) { const t = fn(el); if (t) el.dataset.tip = t; }
    }));

  function show(el) {
    if (el.title) { el.dataset.tip = el.title; el.removeAttribute('title'); }
    const t = el.dataset.tip;
    if (!t) return;
    tip.textContent = t;
    tip.classList.add('show');
    const r = el.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
    let top = r.top - h - 10;
    if (top < 8) top = r.bottom + 10;
    let left = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), innerWidth - w - 8);
    tip.style.top = top + 'px';
    tip.style.left = left + 'px';
  }

  document.addEventListener('mouseover', e => {
    const el = e.target.closest('[data-tip],[title]');
    el ? show(el) : tip.classList.remove('show');
  });
  document.addEventListener('mouseout', e => {
    if (!e.relatedTarget || !e.relatedTarget.closest('[data-tip]')) tip.classList.remove('show');
  });
  document.addEventListener('scroll', () => tip.classList.remove('show'), true);
})();