import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/opt/kirana")
PROJECT = ROOT / "projects/layered-barrier-optimization"
ENV_FILE = PROJECT / "crossref.env"
QUERY = "three-layer target projectile penetration"
FIELDS = "DOI,title,author,published,container-title,type,URL"
ROWS = 5


def contact_email():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("CROSSREF_EMAIL="):
            return line.partition("=")[2].strip()
    raise ValueError("CROSSREF_EMAIL не найден")


def main():
    email = contact_email()
    if not email or "@" not in email:
        raise ValueError("Некорректный контактный email")

    params = urllib.parse.urlencode({
        "query.bibliographic": QUERY,
        "rows": ROWS,
        "select": FIELDS,
        "mailto": email,
    })
    url = "https://api.crossref.org/works?" + params
    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"KiranaResearchGroup/0.1 (mailto:{email})"},
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            print(
                "Crossref ограничил частоту запросов (429). "
                f"Retry-After: {exc.headers.get('Retry-After', 'не указан')}. "
                "Повторный запрос не выполнялся.",
                file=sys.stderr,
            )
            return 2
        print(f"Ошибка Crossref: HTTP {exc.code}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError) as exc:
        print("Ошибка соединения с Crossref; адрес запроса скрыт.", file=sys.stderr)
        return 1

    output_dir = PROJECT / "data" / "crossref"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc)
    record = {
        "retrieved_at_utc": timestamp.isoformat(),
        "source": "Crossref REST API",
        "query": QUERY,
        "rows_requested": ROWS,
        "total_results_reported": payload["message"].get("total-results"),
        "selection_status": "candidates_not_reviewed",
        "items": payload["message"]["items"],
    }
    filename = timestamp.strftime("%Y%m%dT%H%M%SZ") + ".json"
    destination = output_dir / filename
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)

    print(f"Сохранено кандидатов: {len(record['items'])}")
    print(f"Файл: {destination}")
    for number, work in enumerate(record["items"], 1):
        title = (work.get("title") or ["Без названия"])[0]
        print(f"{number}. {title} | DOI: {work.get('DOI', 'нет')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
