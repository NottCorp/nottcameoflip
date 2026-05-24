"""Self-contained HTML page grouped by primary Pokémon with client-side filter."""

from pathlib import Path

from jinja2 import Template

from cameo_convert.model import Card, InvertedDataset
from cameo_convert.writers.base import group_by_primary_pokemon, metadata_dict

_TEMPLATE = Template(
    """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Cameo Pokémon Card Database — {{ dataset.variant }}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; }
    h1 { margin-bottom: 0.2rem; }
    .meta { color: #555; font-size: 0.85rem; margin-bottom: 1rem; }
    .filter { width: 100%; padding: 0.5rem; font-size: 1rem; margin: 1rem 0; box-sizing: border-box; }
    h2 { border-bottom: 1px solid #eee; padding-bottom: 0.25rem; margin-top: 2rem; }
    table { border-collapse: collapse; width: 100%; margin: 0.5rem 0 1.5rem; font-size: 0.92rem; }
    th, td { padding: 0.4rem 0.6rem; border-bottom: 1px solid #f1f1f1; text-align: left; vertical-align: top; }
    th { background: #fafafa; }
    .card-name { font-weight: 600; }
    .num { color: #888; }
    .set { color: #666; font-size: 0.85rem; }
    .flag { display: inline-block; padding: 0 0.4rem; margin-right: 0.2rem; border-radius: 0.25rem; background: #eef; font-size: 0.8rem; }
  </style>
</head>
<body>
  <h1>Cameo Pokémon Card Database — {{ dataset.variant }}</h1>
  <div class="meta">
    Source: <code>{{ meta.source_file }}</code> · last updated {{ meta.source_last_updated }} ·
    generated {{ meta.generated_at }} · release <code>{{ meta.release_tag }}</code> ·
    {{ meta.total_cards }} cards · {{ meta.total_cameo_entries }} cameo entries ·
    grouped by primary Pokémon
  </div>
  <input id="filter" class="filter" placeholder="Type to filter by Pokémon, card, set, or cameo subject…" autocomplete="off">
  {% for bucket_name, cards in grouped %}
  <section data-bucket="{{ bucket_name | e }}">
    <h2>{{ bucket_name | e }}</h2>
    <table>
      <thead><tr><th>Card</th><th>Set / #</th><th>Cameos</th></tr></thead>
      <tbody>
      {% for card in cards %}
        <tr data-search="{{ search_blob(bucket_name, card) | e }}">
          <td class="card-name">{{ (card.card_name or "(blank)") | e }}</td>
          <td class="set">{{ card.set_name | e }} <span class="num">#{{ card.collector_number | e }}</span></td>
          <td>
          {% for c in card.cameos %}
            <div>
              <strong>{{ c.subject | e }}</strong>{% if c.parent_species %} <em>(form of {{ c.parent_species | e }})</em>{% endif %}
              · {{ c.kind | e }}{% if c.ndex %} #{{ c.ndex }}{% endif %}{% if c.region %} · {{ c.region | e }}{% endif %}
              {% if c.notes %}· <em>{{ c.notes | e }}</em>{% endif %}
              {% for f in c.flags|sort(attribute='value') %}<span class="flag">{{ f.value }}</span>{% endfor %}
            </div>
          {% endfor %}
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </section>
  {% endfor %}
  <script>
    const input = document.getElementById('filter');
    input.addEventListener('input', () => {
      const q = input.value.toLowerCase();
      document.querySelectorAll('tbody tr').forEach(tr => {
        tr.style.display = tr.dataset.search.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  </script>
</body>
</html>
"""
)


def _search_blob(bucket_name: str, card: Card) -> str:
    parts = [bucket_name, card.card_name or "", card.set_name, card.collector_number]
    for c in card.cameos:
        parts.append(c.subject)
        if c.parent_species:
            parts.append(c.parent_species)
        if c.notes:
            parts.append(c.notes)
        if c.region:
            parts.append(c.region)
    return " | ".join(parts)


class HtmlWriter:
    name = "html"
    extension = "html"

    def write(self, dataset: InvertedDataset, path: Path) -> None:
        grouped = group_by_primary_pokemon(dataset)
        html = _TEMPLATE.render(
            dataset=dataset,
            meta=metadata_dict(dataset),
            grouped=grouped,
            search_blob=_search_blob,
        )
        path.write_text(html, encoding="utf-8")
