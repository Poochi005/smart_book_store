// Client-side validation and confirmation prompts.
document.querySelectorAll("form[data-confirm]").forEach(function (form) {
  form.addEventListener("submit", function (e) {
    if (!window.confirm(form.dataset.confirm)) e.preventDefault();
  });
});

document.querySelectorAll("form[data-validate]").forEach(function (form) {
  form.addEventListener("submit", function (e) {
    var ok = true;
    form.querySelectorAll("input[required], textarea[required]").forEach(function (el) {
      var bad = !el.value.trim();
      el.classList.toggle("invalid", bad);
      if (bad) ok = false;
    });
    if (!ok) e.preventDefault();
  });
});

// Hide flash messages after a few seconds.
setTimeout(function () {
  document.querySelectorAll(".alert").forEach(function (a) { a.style.display = "none"; });
}, 6000);
