# Capturing real screens

Real screens beat mock-ups: the viewer sees the actual product, page or lesson. The capture takes the page **markup** from a browser the person is already signed in to, then renders it to PNG at 2x. A screen is data to look at, not an account to act in.

Rules, no exceptions:

- No passwords are typed. No cookies are copied. Nothing is saved, sent, bought or deleted. Opening a page or switching a view can still change small things on a site (marked as read, the last view), so open only what the video needs, and name what you opened in your final list.
- Only pages the person named, or public pages of what the speech talks about. Mail, banks, payment pages, messengers and key or token pages are not opened unless the person named that very page.
- Pages that show personal data (names, contacts, messages, payments), other people's or the person's own, and any key or token, are not captured. If a page mixes such blocks with the ones you need, cut them with `--hide` / `--rules` before the PNG is used, and still look at the PNG.
- Owner-only service blocks (preview banners, role switchers, admin summaries) are cut the same way: the viewer of the real product never sees them.
- No sign-in in the pane, or the sign-in has expired: do not try to sign in. Build the scenes on diagrams and cards, and name "no real screens, a sign-in is needed" in the open points.

## Steps

1. Open the page in the already signed-in browser pane (or the Chrome extension) and set the window to 1600 px wide. Switch the product to the view the audience has, if it has one (a student view, a guest view), and choose the data the video is about.
2. Start the receiver in the background (it listens on 127.0.0.1 only and prints a token):
   `node "<W>/tools-local/capture-receiver.mjs" "<W>/raw/snapshots" --port 7791`
3. For every page: navigate, then in a separate call run `capture-snippet.js` in the page, with `__NAME__` (latin file name, e.g. `home`), `__PORT__` and `__TOKEN__` replaced. The tab title becomes `ok saved ...` when the markup has arrived. Expand what the video needs to show (tabs, accordions) before running it.
4. Render the PNGs, light and dark, in the background:
   `node "<W>/tools-local/capture-render.mjs" --in "<W>/raw/snapshots" --out "<W>/public/screens" --origin https://the.site.example --hide ".some-banner"`
   Add `--rules rules.json` to cut elements by text, `--theme-attr data-theme` if the site switches themes by an attribute (the system colour scheme is emulated anyway), names at the end to redo one page. Real Chrome is used; nothing is downloaded.
5. Look at every PNG: no "Loading" skeletons, no other people's data, no owner-only blocks. Videos and lazy images of a page do not reach the snapshot, so scroll the page before step 3 and show the parts that came out whole. A site that does not switch themes gives two identical files: use one. The scene refers to a screen by its file name without `-dark.png` / `-light.png`.
6. Delete `<W>/raw/snapshots` once the PNGs are right: a snapshot holds the whole page, with hidden fields and signed links, and `--hide` only reaches the PNG. The markup also passed through the browser's address, so it can stay in the history of that browser: clear those entries if the page was not public.
7. Put the browser back as it was (switch the view off, restore the window size) and stop the receiver.

The page set that is usually enough: the home page, the list of things the video talks about, one or two detail pages. Do not capture anything the video does not mention.
