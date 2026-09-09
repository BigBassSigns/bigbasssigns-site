document.querySelectorAll("nav.menu details").forEach(function (d) {
  d.addEventListener("toggle", function () {
    if (!d.open) return;
    document.querySelectorAll("nav.menu details").forEach(function (other) {
      if (other !== d) other.removeAttribute("open");
    });
  });
});
