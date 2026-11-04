(function () {
  var root = document.querySelector("[data-live]");
  if (!root) return;
  var endpoint = root.getAttribute("data-live");
  var activeFilter = "all";

  function applyFilter() {
    document.querySelectorAll(".bay").forEach(function (bay) {
      var show = activeFilter === "all" || bay.getAttribute("data-status") === activeFilter;
      bay.classList.toggle("hidden", !show);
    });
  }

  document.querySelectorAll(".filters button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".filters button").forEach(function (b) { b.classList.remove("on"); });
      btn.classList.add("on");
      activeFilter = btn.getAttribute("data-filter");
      applyFilter();
    });
  });

  function refresh() {
    fetch(endpoint, { headers: { "Accept": "application/json" }, credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(function (data) {
        data.slots.forEach(function (s) {
          var bay = document.querySelector('.bay[data-id="' + s.id + '"]');
          if (!bay) return;
          bay.setAttribute("data-status", s.status);
          bay.setAttribute("aria-label", "Slot " + s.label + ", " + s.status);
          if (s.status === "available") { bay.removeAttribute("aria-disabled"); bay.removeAttribute("tabindex"); }
          else { bay.setAttribute("aria-disabled", "true"); bay.setAttribute("tabindex", "-1"); }
        });
        Object.keys(data.counts).forEach(function (k) {
          document.querySelectorAll('[data-count="' + k + '"]').forEach(function (el) { el.textContent = data.counts[k]; });
        });
        applyFilter();
      })
      .catch(function () {});
  }
  setInterval(refresh, 5000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) refresh(); });
})();
