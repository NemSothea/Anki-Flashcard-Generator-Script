You are extending the Anki-Flashcard-Generator-Script repo with a daily TOPIK II vocabulary pipeline. This is a recurring command — the user drops new photos into the resource folder each day and runs this same command to turn them into flashcards.

<context>
- Repo root: this project (Anki-Flashcard-Generator-Script).
- Image source: `Topik II Vocabulary List Resource/` — contains photos (HEIC and possibly JPG/PNG) of TOPIK II vocabulary study pages. Each photo already prints, per entry: the Korean word, its part of speech (sometimes), its English meaning, and a Korean example sentence (sometimes with an English translation alongside it).
- Existing `words.csv` / `make_typedin_anki.py` / `my_vocabulary.apkg` belong to a SEPARATE, unrelated English-vocabulary deck. Do not read, edit, or regenerate anything tied to that deck.
- This TOPIK II deck is new and lives in its own files so the two decks never mix.
</context>

<target_state>
1. A new `topik_words.csv` at repo root with header `word,pos,definition,example,tags` (create it with just the header if it doesn't exist yet).
2. A new `make_topik_deck.py` at repo root (create once, on first run, if it doesn't exist): a copy of `make_typedin_anki.py`'s logic with these changes — `INPUT = "topik_words.csv"`, `OUTPUT = "topik2_deck.apkg"`, deck name `"TOPIK II Vocabulary"`, and `MODEL_ID` / `DECK_ID` set to fixed hardcoded integers (NOT `rand_id()`) so re-running the script updates the same Anki deck/model on reimport instead of creating duplicates every day. Everything else (HTML templates, CSV parsing, uid field, error handling) stays the same as the original script.
3. Every image directly inside `Topik II Vocabulary List Resource/` (not already in its `processed/` subfolder) converted, transcribed, and appended as new rows to `topik_words.csv`. HEIC originals are deleted after conversion (jpg in `processed/` is the kept copy); non-HEIC originals are moved into `Topik II Vocabulary List Resource/processed/`.
4. `topik2_deck.apkg` regenerated from the updated `topik_words.csv`.
</target_state>

<steps>
1. List files directly inside `Topik II Vocabulary List Resource/` (ignore its `processed/` subfolder — those are already done). If none found, report "no new images" and stop here.
2. For each new image: if it's `.HEIC`, convert it to JPEG with `sips -s format jpeg "<file>" --out "Topik II Vocabulary List Resource/processed/<name>.jpg"`, then delete the original `.HEIC` (jpg in `processed/` is the kept copy). If it's already JPG/PNG, just view it directly.
3. Read/view each converted image. Transcribe every vocabulary entry on the page into:
   - `word`: the Korean headword, exactly as printed.
   - `pos`: only if a part-of-speech label is explicitly printed on the page (e.g. 명사/동사/형용사/부사). If not shown, leave blank — do not guess.
   - `definition`: the English meaning exactly as printed.
   - `example`: the Korean example sentence as printed. If the page also prints an English translation of that sentence, append it after the Korean sentence separated by " / ".
   - `tags`: `topik2`
   Transcribe only what is printed. Never invent, guess, or auto-translate a field that isn't shown — if something is illegible or missing, leave that field blank and list it in the final report instead of filling it in.
4. Before appending each row, check the `word` column already in `topik_words.csv` (exact match) and skip it if that word is already present. Track counts of added vs. skipped-as-duplicate.
5. After all entries from an image are transcribed and appended: if it was HEIC, the original is already deleted (step 2) and the jpg is the record in `processed/`. If it was already JPG/PNG, move that original file into `Topik II Vocabulary List Resource/processed/` — never delete a non-HEIC source image.
6. Run `python3 make_topik_deck.py` to regenerate `topik2_deck.apkg`.
7. Print a final report: images processed, words added, duplicates skipped, any entries flagged as illegible/incomplete (with which image), and the output path `topik2_deck.apkg` with a reminder to import it via Anki → File → Import.
</steps>

<scope_lock>
Only touch: `Topik II Vocabulary List Resource/**`, `topik_words.csv`, `make_topik_deck.py`, `topik2_deck.apkg`.
Never touch: `words.csv`, `make_typedin_anki.py`, `ankiconnect_add_words.py`, `my_vocabulary.apkg`, `typed_in_deck_diff.apkg`.
</scope_lock>

<stop_conditions>
Stop and ask before: deleting any file (other than a HEIC original after its jpg conversion succeeds — that deletion is expected and needs no confirmation), installing any dependency, or touching any file outside the scope lock above. Moving source images into `processed/` after successful transcription is expected and does not need confirmation.
</stop_conditions>

Only make the changes described above. Do not refactor `make_typedin_anki.py`, do not add features beyond this pipeline, and do not touch the unrelated English-vocabulary deck.
