document.querySelectorAll("nav.menu details").forEach(function (d) {
  d.addEventListener("toggle", function () {
    if (!d.open) return;
    document.querySelectorAll("nav.menu details").forEach(function (other) {
      if (other !== d) other.removeAttribute("open");
    });
  });
});

(function () {
  var id = "G-Q29X75G87Z";
  var s = document.createElement("script");
  s.async = true;
  s.src = "https://www.googletagmanager.com/gtag/js?id=" + id;
  document.head.appendChild(s);
  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag("js", new Date());
  gtag("config", id);

  document.addEventListener("click", function (e) {
    var a = e.target.closest("a");
    if (!a) return;
    var href = a.getAttribute("href") || "";
    if (href.indexOf("tel:") === 0) {
      gtag("event", "phone_click", { event_category: "engagement", event_label: href });
    } else if (href.indexOf("mailto:") === 0) {
      gtag("event", "email_click", { event_category: "engagement", event_label: href });
    }
  });
})();
