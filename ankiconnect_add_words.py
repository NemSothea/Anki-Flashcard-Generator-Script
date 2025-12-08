# ankiconnect_add_words.py
import csv
import requests
import random
import time

ANKI_CONNECT_URL = "http://127.0.0.1:8765"  # default

# Edit these to match the deck/model names that exist in your Anki (the ones created by your .apkg)
DECK_NAME = "My Vocabulary"
MODEL_NAME = "SahilKsVocabularyModel"  # the model name used in the .apkg generator

INPUT_CSV = (
    "words.csv"  # must have header: word,pos,definition,example,tags (tags optional)
)


def invoke(action, params=None):
    payload = {"action": action, "version": 6}
    if params is not None:
        payload["params"] = params
    r = requests.post(ANKI_CONNECT_URL, json=payload)
    r.raise_for_status()
    res = r.json()
    if res.get("error") is not None:
        raise Exception(f"AnkiConnect error: {res['error']}")
    return res.get("result")


def note_exists(deck, field_name, field_value):
    # Search for notes in deck that contain the exact field (search string using fieldName:term)
    # Note: Anki's search is flexible; for exact match we wrap value in quotes
    query = f'deck:"{deck}" {field_name}:"{field_value}"'
    try:
        note_ids = invoke("findNotes", {"query": query})
        return len(note_ids) > 0
    except Exception as e:
        print("Warning: findNotes failed:", e)
        return False


def add_notes_batch(notes):
    # notes: list of note dicts as required by AnkiConnect addNotes
    return invoke("addNotes", {"notes": notes})


if __name__ == "__main__":
    with open(INPUT_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        to_add = []
        for row in reader:
            word = (row.get("word") or "").strip()
            pos = (row.get("pos") or "").strip()
            definition = (row.get("definition") or "").strip()
            example = (row.get("example") or "").strip()
            tags_raw = (row.get("tags") or "").strip()
            tags = [t.strip() for t in tags_raw.split(",")] if tags_raw else []

            if not word:
                continue

            # skip if a note with same Word already exists in deck
            if note_exists(DECK_NAME, "Word", word):
                print(f"Skipped (exists): {word}")
                continue

            uid = str(random.randrange(1 << 30, 1 << 60))
            note = {
                "deckName": DECK_NAME,
                "modelName": MODEL_NAME,
                "fields": {
                    "Word": word,
                    "pos": pos,
                    "definition": definition,
                    "example": example,
                    "uid": uid,
                },
                "tags": tags,
            }
            to_add.append(note)

            # AnkiConnect has practical limits; add in moderate batches
            if len(to_add) >= 50:
                res = add_notes_batch(to_add)
                print("Batch added:", res)
                to_add = []
                time.sleep(0.2)

        if to_add:
            res = add_notes_batch(to_add)
            print("Final batch added:", res)

    print("Done.")
