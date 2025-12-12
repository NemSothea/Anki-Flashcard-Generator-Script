# Anki Flashcard Generator

Generate a typed-input Anki deck from a CSV word list using Python.

## Anki UI Preview
| Correct word | Incorrect word |
| ------------- | ------------- |
|<img width="1440" height="900" alt="correct-preview" src="https://github.com/user-attachments/assets/8e05847b-0aac-41a1-a62e-66945a059536" />|<img width="1440" height="900" alt="incorrect-preview" src="https://github.com/user-attachments/assets/586f4388-b9e7-4230-9d1a-44f6cfcffc52" />|

# Getting started
### Prerequisites
- Python 3.9+ and `pip`
- Anki installed to import the generated `.apkg`

### Quick start
```bash
git clone https://github.com/your-username/anki-flashcard-generator.git
cd anki-flashcard-generator
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python make_typedin_anki.py
```

Running the script creates `typed_in_deck_diff.apkg` in the project root. Import that file into Anki (double-click it or use File → Import).

### Add new words via AnkiConnect
Push words from `words.csv` directly into Anki using AnkiConnect:

1. Install the AnkiConnect add-on (ID 2055492159) in Anki and keep Anki running.
2. Open `ankiconnect_add_words.py` and set `DECK_NAME` and `MODEL_NAME` to match the deck/model you use.
3. Run:
   ```bash
   python ankiconnect_add_words.py
   ```

The script skips words already present (matching the `Word` field) and adds notes in batches to avoid AnkiConnect limits.

### CSV format
Place your source data in `words.csv` with headers:

- `word` (required)
- `pos`
- `definition`
- `example`
- `tags` (comma-separated list; optional)

Example:
```
word,pos,definition,example,tags
loquacious,adj.,tending to talk a great deal,"The loquacious host charmed everyone.",vocab,lesson1
pithy,adj.,concise and forcefully expressive,"Her pithy remark ended the debate.",vocab
```

Notes:
- Empty `word` rows are skipped.
- A random `uid` is added per note to store typed input locally in Anki.

### Configuration
- Input file: `words.csv`
- Output file: `typed_in_deck_diff.apkg`

You can change these defaults by editing `INPUT` and `OUTPUT` at the top of `make_typedin_anki.py`.

## Development tips
- Regenerate the deck after editing `words.csv` or the template HTML in `make_typedin_anki.py`.
- Use a virtual environment to keep dependencies isolated.

