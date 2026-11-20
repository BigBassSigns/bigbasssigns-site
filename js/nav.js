document.querySelectorAll("nav.menu details").forEach(function (d) {
  d.addEventListener("toggle", function () {
    if (!d.open) return;
    document.querySelectorAll("nav.menu details").forEach(function (other) {
      if (other !== d) other.removeAttribute("open");
    });
  });
});

(function () {
  var viewport = document.querySelector('meta[name="viewport"]');
  if (viewport) {
    var content = viewport.getAttribute("content") || "";
    if (content.indexOf("viewport-fit") === -1) {
      viewport.setAttribute("content", content + ", viewport-fit=cover");
    }
  }

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

  var composingQuote = false;

  document.addEventListener("click", function (e) {
    if (composingQuote) return;
    var a = e.target.closest("a");
    if (!a) return;
    var href = a.getAttribute("href") || "";
    if (href.indexOf("tel:") === 0) {
      gtag("event", "phone_click", {
        event_category: "engagement",
        event_label: href,
        link_text: linkText(a),
        transport_type: "beacon"
      });
    } else if (href.indexOf("mailto:") === 0) {
      gtag("event", "email_click", {
        event_category: "engagement",
        event_label: href.split("?")[0],
        link_text: linkText(a),
        transport_type: "beacon"
      });
    } else if (a.classList.contains("btn") && isContactHref(href)) {
      gtag("event", "quote_click", {
        event_category: "engagement",
        event_label: href,
        link_text: linkText(a),
        transport_type: "beacon"
      });
    }
  });

  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (!form || !form.classList || !form.classList.contains("quote")) return;
    e.preventDefault();
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }
    var data = new FormData(form);
    var what = field(data, "what");
    var lines = [];
    pushLine(lines, "Name", field(data, "name"));
    pushLine(lines, "Phone", field(data, "phone"));
    pushLine(lines, "What it is", what);
    pushLine(lines, "Size and quantity", field(data, "size"));
    pushLine(lines, "Due date", field(data, "due"));
    pushLine(lines, "City or county", field(data, "place"));
    pushLine(lines, "Details", field(data, "details"));
    if (document.referrer) lines.push("From: " + document.referrer);

    gtag("event", "generate_lead", {
      method: "contact_form",
      form_name: "quote",
      event_label: what || "quote",
      transport_type: "beacon"
    });

    var status = form.querySelector(".form-status");
    if (status) {
      status.hidden = false;
      status.textContent = "Opening an email to Sales@BigBassSigns.com.";
    }

    var href = "mailto:Sales@BigBassSigns.com?subject="
      + encodeURIComponent(what ? "Quote request: " + what : "Quote request")
      + "&body=" + encodeURIComponent(lines.join("\n"));
    var mail = document.createElement("a");
    mail.href = href;
    composingQuote = true;
    mail.click();
    composingQuote = false;
  });

  var bar = document.createElement("nav");
  bar.className = "lead-bar";
  bar.setAttribute("aria-label", "Call or email");
  var call = document.createElement("a");
  call.className = "btn btn-gold";
  call.href = "tel:+14254050118";
  call.textContent = "Call (425) 405-0118";
  var email = document.createElement("a");
  email.className = "btn btn-ghost";
  email.href = "mailto:Sales@BigBassSigns.com?subject=Quote%20request";
  email.textContent = "Email quote";
  bar.appendChild(call);
  bar.appendChild(email);
  document.body.appendChild(bar);
  document.body.classList.add("has-lead-bar");

  var navToggle = document.getElementById("nav-toggle");
  if (navToggle) {
    navToggle.addEventListener("change", function () {
      bar.hidden = navToggle.checked;
    });
  }

  function linkText(a) {
    return (a.textContent || "").replace(/\s+/g, " ").trim().slice(0, 80);
  }

  function isContactHref(href) {
    return href === "/contact" || href.indexOf("/contact#") === 0 || href.indexOf("/contact?") === 0;
  }

  function field(data, key) {
    return (data.get(key) || "").toString().trim();
  }

  function pushLine(lines, label, value) {
    if (value) lines.push(label + ": " + value);
  }
})();
