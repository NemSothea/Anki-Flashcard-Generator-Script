# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Python scripts that turn a CSV word list into an Anki `.apkg` deck with a custom "type the word" card (via `genanki`). Two **independent decks** live side by side and must never be mixed:

| Deck | CSV | Generator | Output |
|---|---|---|---|
| English vocabulary ("My Vocabulary") | `words.csv` | `make_typedin_anki.py` | `my_vocabulary.apkg` |
| TOPIK II Korean ("TOPIK II Vocabulary") | `topik_words.csv` | `make_topik_deck.py` | `topik2_deck.apkg` |

`ankiconnect_add_words.py` belongs to the English deck. It pushes `words.csv` rows straight into a running Anki through the AnkiConnect add-on (`http://127.0.0.1:8765`) and skips notes whose `Word` field already exists. `DECK_NAME` and `MODEL_NAME` are hardcoded at the top of that script.

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # Homebrew python3 refuses global pip (PEP 668)
.venv/bin/python make_topik_deck.py          # build topik2_deck.apkg
.venv/bin/python make_typedin_anki.py        # build my_vocabulary.apkg
.venv/bin/python ankiconnect_add_words.py    # needs Anki open with AnkiConnect (add-on 2055492159)
```

There are no tests and no linter. `*.apkg` is gitignored, so you check a change by regenerating the deck and importing it into Anki (File → Import).

## Architecture

- `make_topik_deck.py` is a near copy of `make_typedin_anki.py`. Only these differ: `INPUT` and `OUTPUT`, the model name (`TopikIIVocabularyModel`), the deck name, and the **fixed** `MODEL_ID` and `DECK_ID`. The English script still calls `rand_id()` even though its comment says the IDs are consistent. A change to the card template or the parsing logic usually has to go into both files.
- The card is one note type with fields `Word, pos, definition, example, uid`. All behaviour is in the inline JS of `FRONT_HTML` and `BACK_HTML`:
  - The front saves what you type to `localStorage` under `anki_typed_<uid>`. It also colours the part of speech, so only English POS labels (`noun`, `verb`, `adjective`, `adverb`, `idiom`, …) get colours.
  - The back reads the stored input and runs a Levenshtein diff against the first `|`-separated alternative in `Word`. It grades the answer as correct, close or incorrect, clears the stored value, and shows the example sentence.
- Each run creates a random `uid` for every note (used only as the `localStorage` key). genanki's default note GUID is a hash of all fields, so the English script produces new GUIDs on every rebuild and duplicates notes on reimport. `make_topik_deck.py` passes `guid=genanki.guid_for(word)`, so its notes keep the same GUID across rebuilds and a reimport updates them instead.
- CSV header: `word,pos,definition,example,tags`. Tags are split on commas. A row with no `word` or no `definition` is skipped.

## TOPIK II daily pipeline

The recurring workflow is the project slash command `/add-topik-vocab` (`.claude/commands/add-topik-vocab.md`). It is the source of truth: read it before changing anything about the TOPIK flow. In short:

- New photos go directly in `Topik II Vocabulary List Resource/`. HEIC files are converted with `sips -s format jpeg … --out "…/processed/<name>.jpg"` and the original HEIC is deleted. JPG and PNG files are moved into `processed/`, never deleted.
- Transcribe only what is printed on the page. Tag every row `topik2`, and skip any `word` that already exists (exact match).
- The book prints POS as 명/동/형/부. Existing rows store them as `noun`/`verb`/`adjective`/`adverb` so that the colour mapping works.
- Fields in `topik_words.csv` are all quoted (`csv.QUOTE_ALL`).
- An iPhone sometimes saves a HEIC file with a `.jpg` extension. Check with `file` (HEIC shows `ftyp`) and convert it with `sips` before reading the image.
- The command's scope lock says never to touch the English-deck files: `words.csv`, `make_typedin_anki.py`, `ankiconnect_add_words.py`, `my_vocabulary.apkg`, `typed_in_deck_diff.apkg`.
