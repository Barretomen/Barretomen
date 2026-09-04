"""Generate a checked-in profile card from the GitHub public API."""
import collections
import datetime
import html
import json
import os
import pathlib
import urllib.request

LOGIN = "Barretomen"
ROOT = pathlib.Path(__file__).resolve().parents[1]


def get(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "barretomen-profile"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    request = urllib.request.Request("https://api.github.com/" + path, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def collect():
    profile = get(f"users/{LOGIN}")
    repos = []
    page = 1
    while True:
        batch = get(f"users/{LOGIN}/repos?type=owner&per_page=100&page={page}")
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    original = [repo for repo in repos if not repo["fork"] and not repo["private"]]
    languages = collections.Counter(repo["language"] for repo in original if repo.get("language"))
    return {
        "updated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "public_repositories": len(repos),
        "stars_on_original_public_repositories": sum(repo["stargazers_count"] for repo in original),
        "followers": profile["followers"],
        "primary_languages_by_original_repository": dict(languages.most_common()),
    }


def render(stats):
    language_text = " · ".join(f"{name}: {count}" for name, count in stats["primary_languages_by_original_repository"].items())
    values = [
        ("Repositórios públicos", stats["public_repositories"]),
        ("Estrelas recebidas", stats["stars_on_original_public_repositories"]),
        ("Seguidores", stats["followers"]),
    ]
    metrics = "".join(
        f'<text x="{30+i*260}" y="98" class="number">{value}</text>'
        f'<text x="{30+i*260}" y="124" class="label">{label}</text>'
        for i, (label, value) in enumerate(values)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="232" viewBox="0 0 800 232" role="img" aria-labelledby="title description">
<title id="title">Estatísticas públicas de {LOGIN}</title>
<desc id="description">{stats['public_repositories']} repositórios públicos, {stats['stars_on_original_public_repositories']} estrelas em repositórios próprios e {stats['followers']} seguidores. Atualizado em {stats['updated_at']}. Dados da API do GitHub.</desc>
<style>text{{font-family:Arial,Helvetica,sans-serif}}.number{{font-size:34px;font-weight:600;fill:#efefef}}.label{{font-size:14px;fill:#bbb}}</style>
<rect x=".5" y=".5" width="799" height="231" rx="8" fill="#202020" stroke="#444"/>
<text x="30" y="34" class="label">ATIVIDADE PÚBLICA NO GITHUB</text>
{metrics}
<path d="M30 148H770" stroke="#444"/>
<text x="30" y="174" class="label">Linguagem principal por repositório: {html.escape(language_text)}</text>
<text x="30" y="208" font-size="12" fill="#999">Fonte: GitHub API · Atualizado em {stats['updated_at']} UTC · Repositórios privados não incluídos</text>
</svg>
'''


if __name__ == "__main__":
    stats = collect()
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "github-stats.svg").write_text(render(stats), encoding="utf-8")
    (assets / "github-stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))
