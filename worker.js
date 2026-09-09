const redirects = {
  "/home": "/",
  "/home/Team": "/about",
  "/Team": "/about",
  "/Sign-Details/Business-Services/Outdoor-Signage": "/business",
  "/land-use": "/Sign-Details/Land-Use-Signs",
  "/directional": "/Construction-Stages/directional-signage",
};

export default {
  fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/$/, "") || "/";
    const dest = redirects[path];
    if (dest) {
      return Response.redirect(new URL(dest, url.origin), 301);
    }
    return env.ASSETS.fetch(request);
  },
};
