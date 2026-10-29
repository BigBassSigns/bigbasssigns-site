# SEO page template

Use this when a row in `seo/locations.csv` moves from `unbuilt` to `built`.

## Pick the next pages

- County hub: `type` is `county`.
- City or town: `type` is `city` or `town`, `status` is `unbuilt`, smallest `distance_from_lynnwood_miles` first.
- Do not build a page that is not in the CSV.

## Files to touch

- New HTML at the `url` path (`service-area/{Name}.html`).
- `sitemap.xml`.
- `worker.js` `canonicalPaths`, so a lowercase request 301s to the real path.
- `service-area/index.html`, and the county hub once that hub exists.
- Set `status` to `built` on the row.
- Branch and pull request. Never push to `main`. Never merge.

## Page structure

Match `service-area/Lynnwood.html` for header, nav, hero, prose section, and footer. Use `css/styles.css`. Do not invent a new layout.

### Head

- Unique `<title>`: primary service + place + `WA | Big Bass Signs`. Do not reuse another city's title.
- Unique meta description. One or two sentences: place name, service, printed in Lynnwood, and the jurisdiction to confirm.
- Canonical `https://www.bigbasssigns.com` plus the `url` column.
- Same CSS and favicon links as the other service-area pages.

### JSON-LD

Three `application/ld+json` blocks:

1. `LocalBusiness` for Big Bass Signs: name, url `https://www.bigbasssigns.com`, email `Sales@BigBassSigns.com`, telephone `+1-425-405-0118`, `areaServed` set to this place and its county. Address locality Lynnwood, region WA. No street address. No review, rating, or `aggregateRating`.
2. `Service`: name and description specific to this place, `serviceType`, provider LocalBusiness, `areaServed`, and the `url` of this page.
3. `FAQPage` with the same questions and answers that appear in the body.

### Body

- `hero inner`: kicker (the place name), a unique `h1`, the email line to `Sales@BigBassSigns.com`, and a gold button to `/contact`.
- `section` > `wrap prose`:
  - Unique local copy. Name the jurisdiction (city letter vs county letter), where the place sits relative to Lynnwood, and what to send. Do not paste another city's paragraphs.
  - Link to `/service-area`.
  - Link to the county hub: `/service-area/Snohomish-County`, `/service-area/King-County`, `/service-area/Whatcom-County`, `/service-area/Skagit-County`, or `/service-area/Island-County`.
  - Link the service pages that fit (land use, construction signs, the county notice page, banners). Link a neighboring city only when that page exists.
  - Visible FAQ: `h2` Common questions, then `h3` plus a paragraph, matching the FAQ schema word for word.
- Footer: copy from the other service-area pages. License `BIGBABS743C4` stays in the footer only.

### County hub

Same skeleton. List every city and town in that county from the CSV. Link a city only when its `status` is `built`. Bothell is on the King County and Snohomish County line, so both hubs link to `/service-area/Bothell-Construction-Signage`.

## Copy rules

- Never invent jobs, clients, reviews, or photos. Do not add a photo unless the file is already in `photos/` and it shows that subject.
- Never advertise wraps.
- No prompt language. No house street address in the body.
- Customer-facing. Email `Sales@BigBassSigns.com` first.

## Location data

`seo/locations.csv` columns: `name`, `county`, `type`, `population`, `distance_from_lynnwood_miles`, `status`, `url`.

- `type`: `city`, `town`, or `county`. Town vs city follows the Census place legal class (LSAD town or city).
- `population`: Washington OFM April 1, 2026 official estimate. A city OFM splits across counties uses the sum of those parts (the whole city). County rows use the county total.
- `county`: the county in this file. Bothell is `King/Snohomish`. Auburn, Enumclaw, Pacific, and Milton also meet Pierce County; they stay under King. Milton's OFM split is King 1,770 and Pierce 7,195; the population cell is the full city, 8,965.
- `distance_from_lynnwood_miles`: straight-line statute miles from the Census 2024 gazetteer internal point of Lynnwood city (47.828979, -122.300672) to that place's internal point, one decimal. A county row uses the county seat: Everett, Seattle, Bellingham, Mount Vernon, Coupeville.
- `status`: `built` or `unbuilt`.
- `url`: pages that already exist keep the live path. New pages use `/service-area/` plus the name with spaces turned into hyphens (`Mountlake Terrace` becomes `/service-area/Mountlake-Terrace`). County hubs use `/service-area/Snohomish-County` and the same pattern for the other counties.
- Covered counties: every incorporated city and town in Snohomish, King, Whatcom, Skagit, and Island, plus one hub row per county. Census designated places are not rows.

## Keywords

`seo/keywords.csv` is the service seed, taken from the live service pages and the site rules. A `localizable` value of `yes` may be paired with a place name in a title. Do not add wrap keywords.
