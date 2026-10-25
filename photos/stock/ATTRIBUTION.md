# Stock photo attribution

All 16 photos in this folder were sourced from Wikimedia Commons under
free licenses (CC0, CC BY, CC BY-SA, or Public Domain) and downloaded on
2026-08-18. Keep this file alongside the photos — CC BY / CC BY-SA license
terms require attribution if these are ever reused publicly.

| File | Source title (Wikimedia Commons) | License |
|---|---|---|
| STOCK_01.jpeg | Hazy Foggy Sunset (99501377) | CC BY 3.0 |
| STOCK_02.jpg | Seriously orange and peach sky, clouds and fog on the ridge, sky blue in the water... (7618156296) | CC BY-SA 2.0 |
| STOCK_03.jpg | Vibrant sunset view featuring electric pole and sky filled with clouds overcast with warm hues | CC BY 2.0 |
| STOCK_04.jpg | Bright red-pink clouds at sunset over SF Bay | CC BY-SA 4.0 |
| STOCK_05.jpg | Sunset with wildfire smoke (55421633515) | CC BY 4.0 |
| STOCK_06.jpg | Hazy sunset, Woolsey Fire | Public domain |
| STOCK_07.jpg | DSCF1295 Golden sun melting into the horizon as gentle waves shimmer beneath a painted sky | CC BY-SA 4.0 |
| STOCK_08.jpg | Flaming sky - Bluebird Estates | CC BY 2.0 |
| STOCK_09.jpg | Barbados Cirrus Clouds at Sunset | CC BY-SA 2.0 |
| STOCK_10.jpg | Sunset with Cirrus clouds at Land's End in San Francisco | CC BY-SA 3.0 |
| STOCK_11.jpg | Cirrus at sunset 7th Brigade Park Chermside P1050017 | CC BY-SA 4.0 |
| STOCK_12.jpg | Dramatic golden sunset. (Unsplash) | CC0 |
| STOCK_13.jpg | DFC 1560 A lone boat drifts on a shimmering sea as a dramatic golden sunset lights up towering storm clouds on the horizon | CC BY-SA 4.0 |
| STOCK_14.jpg | Dusk Sunset Sky | CC0 |
| STOCK_15.jpg | Sunset Sky (11422997305) | Public domain |
| STOCK_16.jpg | Sails in a Red Sunset, Carlsbad, CA 8-1987 (6053993420) | CC BY-SA 2.0 |

Full source URLs and page titles are in `analysis/stock_manifest.json`.

## A note on the selection

These were chosen (via Wikimedia Commons search) to fill gaps the original
8 camera photos didn't cover well — marine layer/fog, overcast, wildfire
smoke, cirrus-heavy vivid skies, and a couple of flatter/plainer skies —
plus a spread of apparent quality. Source-site titles were not reliable
descriptors of actual sky condition or quality (two were visibly
mistagged and corrected in `stock_manifest.json`); treat the `tag` field
as loose selection guidance only, not ground truth. The real signal is
whatever Sandy and Aaron actually rate them.

On 2026-08-18, a visual review found 4 of the original 16 weren't actually
sunset photos (STOCK_02 had no visible sun/horizon and was likely sunrise
fog rather than sunset; STOCK_04 and STOCK_16 were plain daytime shots
with no sunset color at all; STOCK_07 was mostly blue daytime sky with
only a faint pink hint). All 4 were replaced with confirmed sunset photos
under the same STOCK_02/04/07/16 filenames — see the `note` field on
those entries in `stock_manifest.json`.
