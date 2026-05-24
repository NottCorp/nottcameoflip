// Renders cameo-convert release info from _site/data/{releases.json,cards.json}.
// Both files are produced by scripts/build_site.py at deploy time.

const FORMATS = [
  ["json", "JSON"],
  ["jsonl", "JSON Lines"],
  ["yaml", "YAML"],
  ["toml", "TOML"],
  ["xml", "XML"],
  ["csv", "CSV"],
  ["tsv", "TSV"],
  ["md", "Markdown"],
  ["html", "HTML"],
  ["txt", "Plain text"],
  ["sqlite", "SQLite"],
  ["xlsx", "XLSX"],
  ["ods", "ODS"],
];

const $ = (id) => document.getElementById(id);

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toISOString().slice(0, 10);
}

function renderMarkdown(md) {
  if (!md) return "<p class=muted>No release notes.</p>";
  if (window.marked) return window.marked.parse(md);
  // Fallback: escape and keep newlines.
  const esc = md.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return "<pre>" + esc + "</pre>";
}

function pickAssetUrl(assets, name) {
  const a = assets.find((x) => x.name === name);
  return a ? a.browser_download_url : null;
}

function assetName(tag, variant, ext) {
  return `cameo-convert-${tag}-cards-${variant}.${ext}`;
}

function bundleName(tag, ext) {
  return `cameo-convert-${tag}-all-formats.${ext}`;
}

function populateFormatSelect() {
  const sel = $("format-select");
  for (const [v, label] of FORMATS) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = label;
    sel.appendChild(opt);
  }
  sel.value = "json";
}

function updateDownload(latest) {
  const fmt = $("format-select").value;
  const variant = $("variant-select").value;
  const tag = latest.tag_name;
  const name = assetName(tag, variant, fmt);
  const url = pickAssetUrl(latest.assets, name);
  const link = $("download-link");
  const urlEl = $("download-url");
  if (url) {
    link.href = url;
    link.removeAttribute("aria-disabled");
    urlEl.textContent = url;
  } else {
    link.href = "#";
    link.setAttribute("aria-disabled", "true");
    urlEl.textContent = `(no asset: ${name})`;
  }
}

function wireBundles(latest) {
  const tag = latest.tag_name;
  const zip = pickAssetUrl(latest.assets, bundleName(tag, "zip"));
  const tar = pickAssetUrl(latest.assets, bundleName(tag, "tar.gz"));
  if (zip) $("bundle-zip").href = zip;
  if (tar) $("bundle-tar").href = tar;
}

function renderLatest(latest) {
  if (!latest) {
    $("release-tag").textContent = "no releases yet";
    $("release-notes").innerHTML = "<p class=muted>No published releases.</p>";
    return;
  }
  $("release-tag").textContent = latest.tag_name;
  $("release-tag").href = latest.html_url;
  $("release-date").textContent = "Published " + fmtDate(latest.published_at);
  $("release-notes").innerHTML = renderMarkdown(latest.body);
  populateFormatSelect();
  updateDownload(latest);
  wireBundles(latest);
  $("format-select").addEventListener("change", () => updateDownload(latest));
  $("variant-select").addEventListener("change", () => updateDownload(latest));
  $("copy-link").addEventListener("click", async () => {
    const url = $("download-url").textContent;
    try { await navigator.clipboard.writeText(url); $("copy-link").textContent = "Copied!"; }
    catch { $("copy-link").textContent = "Copy failed"; }
    setTimeout(() => ($("copy-link").textContent = "Copy URL"), 1200);
  });
}

function renderStats(meta) {
  if (!meta) return;
  $("stat-cards").textContent = meta.total_cards?.toLocaleString() ?? "—";
  $("stat-cameos").textContent = meta.total_cameo_entries?.toLocaleString() ?? "—";
  $("stat-set").textContent = meta.source_last_updated || "—";
  $("stat-generated").textContent = fmtDate(meta.generated_at);
}

function renderHistory(releases) {
  const wrap = $("history-list");
  wrap.innerHTML = "";
  if (!releases.length) {
    wrap.innerHTML = "<p class=muted>No releases.</p>";
    return;
  }
  for (const r of releases) {
    const d = document.createElement("details");
    const s = document.createElement("summary");
    s.innerHTML = `${r.tag_name}<span class="release-meta">${fmtDate(r.published_at)}${r.prerelease ? " · pre-release" : ""}</span>`;
    d.appendChild(s);
    const notes = document.createElement("div");
    notes.className = "notes";
    notes.innerHTML = renderMarkdown(r.body);
    d.appendChild(notes);
    if (r.assets && r.assets.length) {
      const ul = document.createElement("ul");
      ul.className = "assets";
      for (const a of r.assets) {
        const li = document.createElement("li");
        const link = document.createElement("a");
        link.href = a.browser_download_url;
        link.textContent = a.name;
        li.appendChild(link);
        ul.appendChild(li);
      }
      d.appendChild(ul);
    }
    wrap.appendChild(d);
  }
}

let CARDS_INDEX = null;

function buildCardsIndex(cards) {
  const rows = [];
  for (const [key, c] of Object.entries(cards || {})) {
    const cameos = (c.cameos || []).map((x) => x.subject).filter(Boolean);
    const haystack = [
      c.card_name,
      c.set,
      c.collector_number,
      ...cameos,
    ].join(" ").toLowerCase();
    rows.push({
      key,
      set: c.set || "",
      number: c.collector_number || "",
      name: c.card_name || "",
      cameos,
      haystack,
    });
  }
  rows.sort((a, b) =>
    a.set.localeCompare(b.set) || a.number.localeCompare(b.number, undefined, { numeric: true })
  );
  return rows;
}

function renderTable(rows) {
  const tbody = $("cards-tbody");
  const max = 500;
  const slice = rows.slice(0, max);
  tbody.innerHTML = "";
  if (!slice.length) {
    tbody.innerHTML = "<tr><td colspan=4 class=muted>No matches.</td></tr>";
  } else {
    const frag = document.createDocumentFragment();
    for (const r of slice) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${r.set}</td><td>${r.number}</td><td>${r.name}</td><td class=cameos>${
        r.cameos.map((c) => `<b>${c}</b>`).join(", ")
      }</td>`;
      frag.appendChild(tr);
    }
    tbody.appendChild(frag);
  }
  const more = rows.length > max ? ` (showing first ${max})` : "";
  $("filter-count").textContent = `${rows.length.toLocaleString()} card${rows.length === 1 ? "" : "s"}${more}`;
}

function wireBrowse() {
  const input = $("filter-text");
  let last = "";
  const apply = () => {
    const q = input.value.trim().toLowerCase();
    if (q === last) return;
    last = q;
    if (!CARDS_INDEX) return;
    const filtered = q ? CARDS_INDEX.filter((r) => r.haystack.includes(q)) : CARDS_INDEX;
    renderTable(filtered);
  };
  input.addEventListener("input", () => {
    clearTimeout(input._t);
    input._t = setTimeout(apply, 80);
  });
}

async function loadCards() {
  try {
    const res = await fetch("data/cards.json");
    if (!res.ok) throw new Error(res.statusText);
    const data = await res.json();
    renderStats(data.metadata);
    CARDS_INDEX = buildCardsIndex(data.cards);
    renderTable(CARDS_INDEX);
  } catch (e) {
    $("cards-tbody").innerHTML = `<tr><td colspan=4 class=muted>Could not load cards: ${e.message}</td></tr>`;
  }
}

async function main() {
  try {
    const res = await fetch("data/releases.json");
    if (!res.ok) throw new Error(res.statusText);
    const data = await res.json();
    const releases = data.releases || [];
    const latest = releases.find((r) => !r.draft && !r.prerelease) || releases[0] || null;
    renderLatest(latest);
    renderHistory(releases);
  } catch (e) {
    $("release-notes").innerHTML = `<p class=muted>Could not load releases: ${e.message}</p>`;
  }
  wireBrowse();
  loadCards();
}

main();
