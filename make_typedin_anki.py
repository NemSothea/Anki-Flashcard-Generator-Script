import csv
import random
import genanki
import os
import sys

INPUT = "words.csv"
OUTPUT = "my_vocabulary.apkg"


def rand_id():
    """Generate a random ID for Anki models/decks"""
    return random.randrange(1 << 30, 1 << 60)


# Use consistent IDs so reimporting doesn't create duplicates
MODEL_ID = rand_id()
DECK_ID = rand_id()

FRONT_HTML = r"""
<div style="text-align:center; font-family: 'Helvetica Neue', Arial; margin-top: 10px;">
  <div style="font-size:36px; margin-bottom:6px;">
    <input id="userInput" autocomplete="off" autocapitalize="none" autocorrect="off"
           type="text" placeholder="Type the word here"
           style="font-size:36px; width:76%; padding:8px; border:2px solid #e3a; border-radius:6px; text-align:left;" />
  </div>

  <span id="correct" style="display:none">{{Word}}</span>
  <span id="uid" style="display:none">{{uid}}</span>
  <span id="exampleText" style="display:none">{{example}}</span>

  <div style="margin-top:12px; font-size:20px;">
    <strong id="posField">{{pos}}</strong> &nbsp; — &nbsp; <span style="color: #333;">{{definition}}</span>
  </div>

  <div style="margin-top:8px; font-size:12px; color:#666;">
    (Type your answer, then press Anki's "Show Answer" button.)
  </div>

  <script>
  (function(){
    try {
      var input = document.getElementById('userInput');
      var uidSpan = document.getElementById('uid');
      var uid = uidSpan ? uidSpan.innerText.trim() : 'no-uid';
      var key = 'anki_typed_' + uid;
      
      function save(){ 
        try{ 
          if (typeof(Storage) !== "undefined") {
            localStorage.setItem(key, input ? (input.value || '') : ''); 
          }
        } catch(e){
          console.log('Save failed:', e);
        } 
      }
      
      // Load previously stored value
      try {
        if (typeof(Storage) !== "undefined") {
          var stored = localStorage.getItem(key);
          if (stored && input) input.value = stored;
        }
      } catch(e){
        console.log('Load failed:', e);
      }
      
      // CRITICAL: Save immediately when card loads
      save();
      
      if (input) {
        input.addEventListener('input', save);
        input.addEventListener('blur', save);
        input.addEventListener('keydown', function(e){
          if (e.key === 'Enter') { 
            save(); 
            input.blur(); 
          }
        });
        
        setTimeout(function(){
          try { 
            input.focus(); 
            input.select(); 
          } catch(e){}
        }, 10);
      }
    } catch(e) {
      console.log('Front script error:', e);
    }
  })();
  
  // Color-code part of speech
  (function(){
    try {
      var posField = document.getElementById('posField');
      if (!posField) return;
      
      var pos = posField.textContent.trim().toLowerCase();
      
      // Color mapping for different parts of speech
      var colors = {
        'adjective': '#2563eb',           // Blue
        'noun': '#16a34a',                // Green
        'verb': '#ea580c',                // Orange
        'adverb': '#7c3aed',              // Purple
        'idiom': '#db2777',               // Pink
        'phrase': '#ec4899',              // Hot pink
        'noun phrase': '#0891b2',         // Cyan
        'adjective phrase': '#3b82f6',    // Light blue
        'verb phrase': '#f97316',         // Amber
        'noun (technical)': '#059669',    // Emerald
        'noun/verb': '#84cc16'            // Lime
      };
      
      // Apply color
      var color = colors[pos] || '#0a5'; // Default green if not found
      posField.style.color = color;
      
    } catch(e) {
      console.log('POS color error:', e);
    }
  })();
  </script>
</div>
"""

BACK_HTML = r"""
{{FrontSide}}
<hr>
<div id="backContent" style="text-align:center; margin-top:8px; font-family: 'Helvetica Neue', Arial;"></div>
<script>
(function(){
  try {
    // Get container immediately - this is more reliable than document.currentScript
    var container = document.getElementById('backContent');
    if (!container) {
      console.error('backContent container not found');
      return;
    }

    function esc(s){ 
      if (s === null || s === undefined) return '';
      return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); 
    }

    // Read UID and correct answer
    var uidSpan = document.getElementById('uid');
    if (!uidSpan) {
      container.innerHTML = '<div style="color:#900;padding:20px;">Error: UID not found</div>';
      return;
    }
    
    var uid = uidSpan.innerText.trim() || 'no-uid';
    var key = 'anki_typed_' + uid;
    var stored = '';
    
    try { 
      if (typeof(Storage) !== "undefined") {
        stored = (localStorage.getItem(key) || '').trim(); 
      }
    } catch(e) { 
      stored = ''; 
      console.log('Storage read error:', e);
    }

    var correctSpan = document.getElementById('correct');
    if (!correctSpan) {
      container.innerHTML = '<div style="color:#900;padding:20px;">Error: Answer not found</div>';
      return;
    }
    
    var correctRaw = correctSpan.innerText.trim() || '';
    if (!correctRaw) {
      container.innerHTML = '<div style="color:#900;padding:20px;">Error: No correct answer</div>';
      return;
    }
    
    // Handle alternative answers separated by |
    var canonical = (correctRaw.split('|')[0] || '').trim();
    
    var a = canonical;
    var b = stored || '';
    var A = a.toLowerCase();
    var B = b.toLowerCase();

    // Levenshtein DP
    function levenshteinDP(X, Y){
      var n = X.length, m = Y.length;
      var dp = [];
      for (var i=0; i<=n; i++){
        dp[i] = [];
        for (var j=0; j<=m; j++) {
          dp[i][j] = 0;
        }
      }
      for (var i=0; i<=n; i++) dp[i][0] = i;
      for (var j=0; j<=m; j++) dp[0][j] = j;
      
      for (var i=1; i<=n; i++){
        for (var j=1; j<=m; j++){
          var cost = (X[i-1] === Y[j-1]) ? 0 : 1;
          dp[i][j] = Math.min(
            dp[i-1][j] + 1,
            dp[i][j-1] + 1,
            dp[i-1][j-1] + cost
          );
        }
      }
      return dp;
    }

    var dp = levenshteinDP(A, B);
    var dist = dp[A.length][B.length];

    // Backtrack
    var ops = [];
    var i = A.length, j = B.length;
    var maxIter = (A.length + B.length) * 2;
    var iter = 0;
    
    while ((i > 0 || j > 0) && iter < maxIter){
      iter++;
      if (i > 0 && j > 0 && A[i-1] === B[j-1]){
        ops.push(['match', a.charAt(i-1), b.charAt(j-1)]);
        i--; j--;
      } else if (i > 0 && j > 0 && dp[i][j] === dp[i-1][j-1] + 1){
        ops.push(['replace', a.charAt(i-1), b.charAt(j-1)]);
        i--; j--;
      } else if (i > 0 && dp[i][j] === dp[i-1][j] + 1){
        ops.push(['delete', a.charAt(i-1), '']);
        i--;
      } else if (j > 0){
        ops.push(['insert', '', b.charAt(j-1)]);
        j--;
      } else {
        break;
      }
    }
    ops.reverse();

    // Build diff HTML
    var expectedHTML = '';
    var userHTML = '';
    
    if (ops.length === 0 && b === '') {
      // Empty input case
      expectedHTML = '<span style="background:#ffecec;color:#900;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;">' + esc(a) + '</span>';
      userHTML = '<span style="opacity:0.4;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;color:#666;">(empty)</span>';
    } else {
      ops.forEach(function(op){
        var t = op[0], ca = op[1], cb = op[2];
        if (t === 'match'){
          expectedHTML += '<span style="background:#ddffea;color:#084;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;">' + esc(ca) + '</span>';
          userHTML += '<span style="background:#ddffea;color:#084;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;">' + esc(cb) + '</span>';
        } else if (t === 'replace'){
          expectedHTML += '<span style="background:#ffecec;color:#900;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;">' + esc(ca) + '</span>';
          userHTML += '<span style="background:#ffecec;color:#900;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;">' + esc(cb) + '</span>';
        } else if (t === 'delete'){
          expectedHTML += '<span style="background:#ffecec;color:#900;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;">' + esc(ca) + '</span>';
          userHTML += '<span style="opacity:0.4;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;color:#666;">␣</span>';
        } else if (t === 'insert'){
          expectedHTML += '<span style="opacity:0.4;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;color:#666;">␣</span>';
          userHTML += '<span style="background:#ffecec;color:#900;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;">' + esc(cb) + '</span>';
        }
      });
    }

    // Determine status
    var threshold = (a.length <= 5) ? 1 : 2;
    var very_close_threshold = Math.max(1, Math.floor(a.length * 0.15));
    var status = 'incorrect';
    
    if (dist === 0) {
      status = 'correct';
    } else if (dist <= very_close_threshold) {
      status = 'close';
    } else if (dist <= threshold) {
      status = 'almost';
    }

    // Clear storage
    try { 
      if (typeof(Storage) !== "undefined") {
        localStorage.removeItem(key); 
      }
    } catch(e) {
      console.log('Clear storage error:', e);
    }

    // Build status box
    var box = document.createElement('div');
    box.style.display = 'inline-block';
    box.style.padding = '14px';
    box.style.borderRadius = '10px';
    box.style.minWidth = '300px';
    box.style.fontSize = '26px';
    box.style.boxShadow = '0 2px 6px rgba(0,0,0,0.06)';
    
    if (status === 'correct'){
      box.style.background = '#ddffea';
      box.style.color = '#084';
      box.innerHTML = '<div style="font-weight:800;font-size:28px;">✓ Correct!</div><div style="margin-top:8px;font-size:28px;">' + esc(a) + '</div>';
    } else if (status === 'close' || status === 'almost'){
      box.style.background = '#fff7e6';
      box.style.color = '#6a4d00';
      box.innerHTML = '<div style="font-weight:800;font-size:28px;">~ Close!</div>'
                    + '<div style="margin-top:8px;font-size:24px;">' + esc(a) + '</div>'
                    + '<div style="font-size:14px;margin-top:8px;color:#333;">Small spelling differences shown below.</div>';
    } else {
      box.style.background = '#ffecec';
      box.style.color = '#900';
      box.innerHTML = '<div style="font-weight:800;font-size:28px;">✗ Answer</div>'
                    + '<div style="margin-top:8px;font-size:24px;">' + esc(a) + '</div>'
                    + '<div style="font-size:14px;margin-top:8px;color:#333;">Your attempt shown below.</div>';
    }
    container.appendChild(box);

    // Show diff
    var diffWrap = document.createElement('div');
    diffWrap.style.marginTop = '16px';
    diffWrap.style.fontSize = '18px';
    diffWrap.style.lineHeight = '1.6';
    diffWrap.innerHTML = '<div style="margin-bottom:6px;font-weight:700;">Expected:</div><div>' + expectedHTML + '</div>'
                       + '<div style="margin-top:8px;font-weight:700;">You typed:</div><div>' + userHTML + '</div>'
                       + '<div style="margin-top:8px;color:#666;font-size:14px;">Edit distance: ' + dist + '</div>';
    container.appendChild(diffWrap);

    // Show example - use a hidden span to avoid JS string escaping issues
    var exampleSpan = document.getElementById('exampleText');
    var exampleText = exampleSpan ? exampleSpan.textContent : '';
    
    if (exampleText && exampleText.trim()) {
      var meta = document.createElement('div');
      meta.style.marginTop = '14px';
      meta.style.fontSize = '18px';
      meta.style.color = '#222';
      meta.style.lineHeight = '1.4';
      
      var exampleDiv = document.createElement('div');
      exampleDiv.style.fontStyle = 'italic';
      exampleDiv.style.color = '#006';
      exampleDiv.style.marginTop = '6px';
      
      var strong = document.createElement('strong');
      strong.textContent = 'Example:';
      exampleDiv.appendChild(strong);
      exampleDiv.appendChild(document.createElement('br'));
      
      var textSpan = document.createElement('span');
      textSpan.textContent = exampleText;
      exampleDiv.appendChild(textSpan);
      
      meta.appendChild(exampleDiv);
      container.appendChild(meta);
    }
    
  } catch(e) {
    console.error('Back script error:', e);
    var container = document.getElementById('backContent');
    if (container) {
      container.innerHTML = '<div style="color:#900;padding:20px;border:2px solid #900;border-radius:8px;background:#ffe;">Error displaying answer. Details: ' + e.message + '</div>';
    }
  }
})();
</script>
"""

CSS = r"""
.card {
  font-family: 'Helvetica Neue', Arial;
  text-align: center;
  background: white;
  color: #111;
}
"""


def create_deck():
    """Create the Anki deck from CSV input"""

    my_model = genanki.Model(
        MODEL_ID,
        "SahilKsVocabularyModel",
        fields=[
            {"name": "Word"},
            {"name": "pos"},
            {"name": "definition"},
            {"name": "example"},
            {"name": "uid"},
        ],
        templates=[{"name": "TypeIn", "qfmt": FRONT_HTML, "afmt": BACK_HTML}],
        css=CSS,
    )

    deck = genanki.Deck(DECK_ID, "My Vocabulary")

    if not os.path.exists(INPUT):
        print(f"Error: Input CSV file '{INPUT}' not found!")
        print(
            f"Please create a CSV file named '{INPUT}' with columns: word,pos,definition,example,tags"
        )
        sys.exit(1)

    count = 0
    skipped = 0
    errors = []

    try:
        with open(INPUT, encoding="utf-8", newline="") as csvfile:
            reader = csv.DictReader(csvfile)

            if reader.fieldnames is None:
                print("Error: CSV file appears to be empty or invalid")
                sys.exit(1)

            required_cols = {"word", "pos", "definition", "example"}
            missing_cols = required_cols - set(reader.fieldnames)
            if missing_cols:
                print(f"Warning: Missing columns in CSV: {missing_cols}")
                print(f"Available columns: {reader.fieldnames}")

            for row_num, row in enumerate(reader, start=2):
                try:
                    word = (row.get("word") or "").strip()
                    pos = (row.get("pos") or "").strip()
                    definition = (row.get("definition") or "").strip()
                    example = (row.get("example") or "").strip()
                    tags_raw = (row.get("tags") or "").strip()

                    if tags_raw:
                        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
                    else:
                        tags = []

                    if not word:
                        skipped += 1
                        continue

                    if not definition:
                        errors.append(f"Row {row_num}: Word '{word}' has no definition")
                        skipped += 1
                        continue

                    uid = str(random.randrange(1 << 30, 1 << 60))

                    note = genanki.Note(
                        model=my_model,
                        fields=[word, pos, definition, example, uid],
                        tags=tags,
                    )
                    deck.add_note(note)
                    count += 1

                except Exception as e:
                    errors.append(f"Row {row_num}: Error processing - {str(e)}")
                    skipped += 1

    except UnicodeDecodeError:
        print(
            f"Error: Could not read '{INPUT}'. Make sure it's a valid UTF-8 encoded CSV file."
        )
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV: {str(e)}")
        sys.exit(1)

    if errors:
        print("\nWarnings/Errors:")
        for error in errors[:10]:
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")

    if count == 0:
        print("Error: No valid cards were created. Please check your CSV file.")
        sys.exit(1)

    try:
        package = genanki.Package(deck)
        package.write_to_file(OUTPUT)
        print(f"\n✓ Success! Created '{OUTPUT}' with {count} card(s).")
        if skipped > 0:
            print(f"  ({skipped} row(s) skipped)")
        print(f"\nTo use: Open Anki → File → Import → Select '{OUTPUT}'")
    except Exception as e:
        print(f"Error writing output file: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    create_deck()
