import argparse
import json
from collections import Counter
from pathlib import Path

PROJECT = Path("/opt/kirana/projects/layered-barrier-optimization")
DATA_DIR = PROJECT / "data" / "crossref"
ALLOWED_STATUSES = {"full_text_reviewed", "candidate_not_reviewed"}

def main():
    parser = argparse.ArgumentParser(
        description="Показать проверенные работы и непроверенных кандидатов Оли"
    )
    parser.add_argument(
        "register",
        type=Path,
        help="Путь к JSON-реестру, например data/crossref/review-20260926.json",
    )
    args = parser.parse_args()

    path = args.register.resolve()
    if DATA_DIR.resolve() not in path.parents:
        parser.error("Реестр должен находиться внутри каталога data/crossref")
    if not path.is_file():
        parser.error(f"Файл не найден: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        records = data["records"]
        if not isinstance(records, list):
            raise ValueError("records должен быть списком")

        seen = set()
        for number, record in enumerate(records, 1):
            doi = record["doi"]
            title = record["title"]
            review = record["review"]
            status = review["status"]
            if not isinstance(doi, str) or not doi:
                raise ValueError(f"Запись {number}: пустой DOI")
            if doi in seen:
                raise ValueError(f"Повтор DOI: {doi}")
            seen.add(doi)
            if not isinstance(title, str) or not title:
                raise ValueError(f"Запись {number}: пустое название")
            if status not in ALLOWED_STATUSES:
                raise ValueError(f"Запись {number}: неизвестный статус {status!r}")
            if status == "full_text_reviewed":
                if not review.get("evidence") or not review.get("notes") or not review.get("limits"):
                    raise ValueError(f"Запись {number}: неполная проверенная карточка")
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        parser.error(f"Некорректный реестр: {exc}")

    statuses = Counter(record["review"]["status"] for record in records)
    print(f"Реестр: {path.name}")
    print(f"Всего работ: {len(records)}")
    print(f"Проверены по полному тексту: {statuses['full_text_reviewed']}")
    print(f"Кандидаты без проверки: {statuses['candidate_not_reviewed']}")

    for status, heading in (
        ("full_text_reviewed", "Проверены по полному тексту"),
        ("candidate_not_reviewed", "Ожидают проверки"),
    ):
        print(f"\n{heading}:")
        for record in records:
            if record["review"]["status"] != status:
                continue
            print(f"- {record['doi']} | {record['title']}")
            if status == "full_text_reviewed":
                review = record["review"]
                print(f"  Роль: {review['role']}")
                for note in review["notes"]:
                    print(f"  Тезис: {note}")
                print(f"  Ограничение: {review['limits']}")

if __name__ == "__main__":
    main()
