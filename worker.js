const redirects = {
  "/home": "/",
  "/home/team": "/about",
  "/team": "/about",
  "/sign-details/business-services/outdoor-signage": "/business",
  "/land-use": "/Sign-Details/Land-Use-Signs",
  "/directional": "/Construction-Stages/directional-signage",
  "/service-area/mill-creek": "/service-area/Mill-Creek",
  "/vehicles-stickers/domed-boat-letters": "/boat-letters",

  // Dead Ads / Google Sites slugs → matching product page (never homepage)
  "/construction-stages/public-notice-signs-land-use": "/Sign-Details/Land-Use-Signs",
  "/construction-stages/construction-site-safety-signs": "/Sign-Details/Construction-Safety-Signs",
  "/schedule-consultation": "/contact",
  "/contact-us": "/contact",
  "/quote": "/contact",
  "/specials": "/specials/truck-logo-packages",
  "/truck-logo-packages": "/specials/truck-logo-packages",
  "/truck-logos": "/specials/truck-logo-packages",
  "/business-services": "/business",
  "/business-services/outdoor-signage": "/business/banners",
  "/business-services/vehicle-graphics": "/vehicles",
  "/business-services/interior-signage": "/business/storefront",
  "/business-services/moveable-signage-street-level-signs": "/business/banners",
  "/vehicle-graphics": "/vehicles",
  "/boat-lettering": "/boat-letters",
  "/banners": "/business/banners",
  "/storefront": "/business/storefront",
  "/construction-signs": "/Sign-Details/Construction-Signs",
  "/safety-signs": "/Sign-Details/Construction-Safety-Signs",
  "/swppp": "/Construction-Stages/environmental-swppp-tree-protection",
  "/land-use-signs": "/Sign-Details/Land-Use-Signs",
  "/service-area/seattle-sdci-signs": "/Sign-Details/Land-Use-Signs",
};

const canonicalPaths = [
  "/",
  "/about",
  "/boat-letters",
  "/business",
  "/business/banners",
  "/business/storefront",
  "/carpet-decals",
  "/construction",
  "/contact",
  "/faq",
  "/directional",
  "/equipment",
  "/home/equipment",
  "/home/sponsorships",
  "/land-use",
  "/privacy-policy",
  "/vehicles",
  "/specials/truck-logo-packages",
  "/Sign-Details",
  "/Sign-Details/Land-Use-Signs",
  "/Sign-Details/Construction-Signs",
  "/Sign-Details/Construction-Safety-Signs",
  "/Sign-Details/Grant-Agency-Funded",
  "/Construction-Stages",
  "/Construction-Stages/environmental-swppp-tree-protection",
  "/Construction-Stages/directional-signage",
  "/Construction-Stages/construction-site-safety-signs",
  "/Construction-Stages/who-you-are/Developer-land-use-planner",
  "/service-area",
  "/service-area/Lynnwood",
  "/service-area/Everett",
  "/service-area/Kirkland",
  "/service-area/Mill-Creek",
  "/service-area/Sammamish",
  "/service-area/Woodinville",
  "/service-area/Bothell-Construction-Signage",
  "/service-area/monroe-site-development",
  "/service-area/redmond-signage-services",
];

const canonicalByLower = Object.fromEntries(
  canonicalPaths.map((p) => [p.toLowerCase(), p])
);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const rawPath = url.pathname;
    const path = rawPath.replace(/\/$/, "") || "/";
    const lower = path.toLowerCase();

    if (lower === "/robots.txt" || lower === "/sitemap.xml") {
      const assetPath = lower === "/robots.txt" ? "/robots.txt" : "/sitemap.xml";
      const assetRes = await env.ASSETS.fetch(new Request(new URL(assetPath, url.origin), request));
      const assetType = assetRes.headers.get("content-type") || "";
      if (assetRes.ok && !assetType.includes("text/html")) {
        const headers = new Headers(assetRes.headers);
        headers.set(
          "content-type",
          lower === "/robots.txt"
            ? "text/plain; charset=utf-8"
            : "application/xml; charset=utf-8"
        );
        return new Response(assetRes.body, { status: 200, headers });
      }
    }

    const dest = redirects[lower];
    if (dest && dest.toLowerCase() !== lower) {
      return Response.redirect(new URL(dest + url.search, url.origin), 301);
    }

    const canon = canonicalByLower[lower];
    if (canon && canon !== path) {
      return Response.redirect(new URL(canon + url.search, url.origin), 301);
    }

    return env.ASSETS.fetch(request);
  },
};
