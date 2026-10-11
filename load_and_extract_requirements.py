"""
Load LinkedIn vacancy JSON files, tag Seniority, deduplicate, and extract
candidate-requirements sections from descriptionText into requirements_text.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(r"D:\Downloads")

FILE_CONFIG: list[tuple[str, str]] = [
    ("brand&entry85.json", "Entry"),
    ("brand&senior85.json", "Senior"),
    ("content&creative&senior85.json", "Senior"),
    ("content&creative&entry.json", "Entry"),
    ("digital&performence&entry85.json", "Entry"),
    ("digital&performence&senior85.json", "Senior"),
]

# Headers that typically open a candidate-requirements / profile section.
REQUIREMENTS_START = re.compile(
    r"(?im)^[^\S\n]*(?:"
    r"(?:[💼🔥📈]\s*)?"
    r"(?:"
    # English
    r"Requirements(?:\s*&\s*Qualifications)?|"
    r"Job\s+Requirements|"
    r"(?:Your\s+)?Qualifications(?:\s*(?:&|and)\s*(?:Skills|Experience(?:\s+Requirements)?))?|"
    r"Qualifications\s+And\s+Experience\s+Requirements|"
    r"What\s+You(?:'|\u2019)?ll\s+(?:Need|Bring)|"
    r"What\s+You\s+Bring|"
    r"What\s+We(?:'|\u2019)?re\s+Looking\s+For|"
    r"Who\s+Are\s+We\s+Looking\s+For|"
    r"Who\s+We(?:'|\u2019)?re\s+Looking\s+For|"
    r"You\s+(?:bring|have)|"
    r"You\s+Could\s+Be\s+a\s+Great\s+Fit\s+If\s+You\s+Have|"
    r"Who\s+You\s+Are|"
    r"Your\s+(?:Skills\s+And\s+Experience|Experience\s*&\s*Skills)|"
    r"The\s+Skills\s+And\s+Knowledge\s+You(?:'|\u2019)?ll\s+Bring|"
    r"The\s+ideal\s+skills\s+and\s+experience|"
    r"This\s+Role\s+Requires|"
    r"Education\s+And\s+Experience\s+Required|"
    r"Other\s+Qualifications|"
    r"Skills\s+We(?:'|\u2019)?re\s+Seeking|"
    r"Skills\s+Were\s+Seeking|"
    r"Must[- ]Haves?|"
    r"Required|"
    r"About\s+You|"
    # Dutch
    r"Functie-?eisen|"
    r"Vereisten|"
    r"Kwalificaties|"
    r"Competenties|"
    r"Kandidaatprofiel|"
    r"Spelersprofiel|"
    r"Profiel|"
    r"Jouw\s+(?:profiel|skills)|"
    r"Jouw\s+opleiding,?\s+vaardigheden\s+en\s+ervaring|"
    r"Jouw\s+persoonlijkheid\s*&\s*competenties.*|"
    r"Wie\s+ben\s+jij(?:\s+en\s+wat\s+breng\s+je\s+mee)?|"
    r"Wie\s+jij\s+bent|"
    r"Wat\s+(?:wij\s+)?vragen|"
    r"Wat\s+breng\s+(?:je|jij)\s+mee|"
    r"Wat\s+zien\s+we\s+graag\s+in\s+jou|"
    r"Wat\s+jou\s+typeert|"
    r"Wat\s+zoeken\s+wij|"
    r"Wie\s+zoeken\s+wij|"
    r"Wie\s+ben\s+je|"
    r"Dit\s+is\s+wie\s+je\s+bent|"
    r"What\s+do\s+we\s+expect\s+from\s+you|"
    r"What\s+we\s+expect\s+from\s+you|"
    r"Basic\s+Qualifications|"
    r"Preferred\s+Qualifications|"
    r"Dit\s+vraag\s+je\s+(?:van\s+ons|ons)|"
    r"Dit\s+breng\s+(?:je|jij)\s+mee|"
    r"Daarnaast\s+breng\s+je\s+mee|"
    r"Daarnaast\s+zien\s+we\s+graag\s+dat\s+je\s+ervaring\s+hebt\s+met|"
    # Inline lead-ins that end on their own line (often with a colon)
    r".{0,90}\bbeschik(?:t)?\s+jij\b.{0,50}\bover|"
    r".{0,90}\bzoeken\s+wij\b.{0,50}\b(?:iemand|een\s+\w+)|"
    r".{0,90}\bwe\s+(?:are\s+)?looking\s+for\b.{0,50}(?:someone|a\s+\w+)?"
    r")"
    r")\s*[:?]*\s*$"
)

# Headers / cues that typically start the *next* section (stop extraction here).
SECTION_STOP = re.compile(
    r"(?im)^[^\S\n]*(?:"
    r"(?:🎁\s*)?"
    r"(?:"
    # Benefits / offer
    r"What\s+(?:We|you(?:'|\u2019)?ll)\s+(?:Offer|Get)|"
    r"What\s+We\s+Bring|"
    r"Benefits|"
    r"Our\s+Offer|"
    r"We\s+Offer|"
    r"Perks|"
    r"Wat\s+(?:bieden\s+wij|wij\s+bieden|je\s+krijgt|krijg\s+je\s+van\s+ons|mag\s+jij\s+verwachten)|"
    r"Dit\s+is\s+wat\s+wij\s+bieden|"
    r"Wij\s+bieden(?:\s+jou)?|"
    r"Ons\s+aanbod|"
    r"Jouw\s+(?:aanbod|rewards?|beloning)|"
    r"Arbeidsvoorwaarden|"
    r"What\s+can\s+you\s+expect\s+from\s+us|"
    r"Why\s+work\s+at|"
    r"How\s+does\s+the\s+process\s+work|"
    r"Wat\s+ga\s+je\s+doen|"
    r"Wat\s+zijn\s+je\s+belangrijkste\s+taken|"
    # About company / apply / responsibilities
    r"About\s+(?:Us|the\s+(?:Company|Role|Team))|"
    r"Over\s+(?:ons|het\s+bedrijf|de\s+(?:organisatie|functie))|"
    r"What\s+You(?:'|\u2019)?ll\s+Do|"
    r"What\s+You\s+Will\s+(?:Do|Own)|"
    r"Responsibilities|"
    r"Your\s+Role|"
    r"Jouw\s+(?:rol|taken|verantwoordelijkheden|werkweek|team|missie|uitdaging)|"
    r"Werkzaamheden|"
    r"Taken\s+en\s+verantwoordelijkheden|"
    r"Hoe\s+ziet\s+jouw|"
    r"Solliciteer|"
    r"Apply(?:\s+now)?|"
    r"Interested\??|"
    r"Iets\s+voor\s+jou\??|"
    r"Meer\s+over|"
    r"Wacht\s+niet|"
    r"Our\s+Culture|"
    r"Onze\s+(?:cultuur|bestemming)|"
    r"Kom\s+werken|"
    r"Upload\s+(?:hier\s+)?(?:je|jouw)|"
    r"Tip:|"
    r"Powered\s+by|"
    r"Visa\s+sponsorship|"
    r"Ready\s+to\s+apply"
    r")"
    r")\s*[:?]*\s*$"
    r"|"
    # Soft stop: quoted employee testimonials
    r'^\s*"[^"]{20,}"\s*$'
)


def extract_requirements(description_text: str | float | None) -> str:
    """
    Extract ONLY the candidate-requirements section from a job description.

    Looks for English/Dutch headers such as Requirements, You Bring,
    Jouw profiel, Functie-eisen, Wie ben jij?, etc., and captures text until
    the next major section header (benefits, about us, apply, ...).
    Returns an empty string when no requirements section is found.
    """
    if description_text is None or (isinstance(description_text, float) and pd.isna(description_text)):
        return ""

    text = str(description_text)
    # Normalise common HTML leftovers from scraped LinkedIn text.
    text = (
        text.replace("&amp;", "&")
        .replace("&nbsp;", " ")
        .replace("\u00a0", " ")
        .strip()
    )
    if not text:
        return ""

    start_match = REQUIREMENTS_START.search(text)
    if not start_match:
        return ""

    body = text[start_match.end() :]
    stop_match = SECTION_STOP.search(body)
    if stop_match:
        body = body[: stop_match.start()]

    return body.strip()


def load_vacancies(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load the six JSON files into one DataFrame with a Seniority column."""
    frames: list[pd.DataFrame] = []

    for filename, seniority in FILE_CONFIG:
        path = data_dir / filename
        with path.open(encoding="utf-8") as fh:
            records = json.load(fh)

        frame = pd.json_normalize(records)
        frame["Seniority"] = seniority
        frame["source_file"] = filename
        frames.append(frame)

    return pd.concat(frames, ignore_index=True)


def build_dataset(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load, deduplicate by companyName+title, and extract requirements_text."""
    df = load_vacancies(data_dir)

    before = len(df)
    df = df.drop_duplicates(subset=["companyName", "title"], keep="first").copy()
    after = len(df)

    df["requirements_text"] = df["descriptionText"].map(extract_requirements)

    print(f"Loaded rows: {before}")
    print(f"After dedupe (companyName + title): {after} (removed {before - after})")
    print("Seniority counts:")
    print(df["Seniority"].value_counts().to_string())
    extracted = (df["requirements_text"].str.len() > 0).sum()
    print(f"requirements_text extracted: {extracted}/{after} ({extracted / after:.1%})")

    return df


if __name__ == "__main__":
    jobs = build_dataset()

    # Quick spot-checks
    sample = jobs.loc[jobs["requirements_text"].str.len() > 0, ["title", "companyName", "Seniority", "requirements_text"]].head(3)
    for _, row in sample.iterrows():
        preview = row["requirements_text"][:280].replace("\n", " | ")
        print(f"\n[{row['Seniority']}] {row['companyName']} — {row['title']}")
        print(f"  {preview}...")

    out_dir = Path(__file__).resolve().parent
    pkl_path = out_dir / "vacancies_with_requirements.pkl"
    csv_path = out_dir / "vacancies_with_requirements.csv"
    jobs.to_pickle(pkl_path)
    jobs.to_csv(csv_path, index=False)
    print(f"\nSaved: {pkl_path}")
    print(f"Saved: {csv_path}")
