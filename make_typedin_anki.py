import csv
import random
import genanki
import os

INPUT = "words.csv"
OUTPUT = "typed_in_deck_diff.apkg"


def rand_id():
    return random.randrange(1 << 30, 1 << 60)


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

  <div style="margin-top:12px; font-size:20px; color: #0a5;">
    <strong>{{pos}}</strong> &nbsp; — &nbsp; {{definition}}
  </div>

  <div style="margin-top:8px; font-size:12px; color:#666;">
    (Type your answer, then press Anki's "Show Answer" button.)
  </div>

  <script>
  (function(){
    var input = document.getElementById('userInput');
    var uidSpan = document.getElementById('uid');
    var uid = uidSpan ? uidSpan.innerText.trim() : 'no-uid';
    var key = 'anki_typed_' + uid;
    try {
      var stored = localStorage.getItem(key);
      if (stored && input) input.value = stored;
    } catch(e){}
    function save(){ try{ localStorage.setItem(key, input.value || ''); } catch(e){} }
    if (input) {
      input.addEventListener('input', save);
      input.addEventListener('blur', save);
      input.addEventListener('keydown', function(e){
        if (e.key === 'Enter') { save(); input.blur(); }
      });
      try { input.focus(); input.select(); } catch(e){}
    }
  })();
  </script>
</div>
"""

# Fixed BACK_HTML: meta.innerHTML is a single-line JS string (no raw newline inside quotes)
BACK_HTML = r"""
{{FrontSide}}
<hr>
<div style="text-align:center; margin-top:8px; font-family: 'Helvetica Neue', Arial;">
  <script>
  (function(){
    function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

    // Read UID and correct answer
    var uidSpan = document.getElementById('uid');
    var uid = uidSpan ? uidSpan.innerText.trim() : 'no-uid';
    var key = 'anki_typed_' + uid;
    var stored = '';
    try { stored = localStorage.getItem(key) || ''; } catch(e) { stored = ''; }

    var correctSpan = document.getElementById('correct');
    var correctRaw = correctSpan ? correctSpan.innerText.trim() : '';
    // canonical displayed answer is first alternative before '|'
    var canonical = correctRaw.split('|')[0];

    var a = canonical;           // expected
    var b = stored || '';        // user typed

    // compute Levenshtein DP table
    function levenshteinDP(A, B){
      var n = A.length, m = B.length;
      var dp = new Array(n+1);
      for (var i=0;i<=n;i++){ dp[i]=new Array(m+1); for (var j=0;j<=m;j++) dp[i][j]=0; }
      for (var i=0;i<=n;i++) dp[i][0]=i;
      for (var j=0;j<=m;j++) dp[0][j]=j;
      for (var i=1;i<=n;i++){
        for (var j=1;j<=m;j++){
          var cost = (A[i-1]===B[j-1])?0:1;
          dp[i][j] = Math.min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost);
        }
      }
      return dp;
    }

    var dp = levenshteinDP(a,b);
    var dist = dp[a.length][b.length];

    // backtrack to produce ops
    var ops = [];
    var i = a.length, j = b.length;
    while (i>0 || j>0){
      if (i>0 && j>0 && a[i-1]===b[j-1]){
        ops.push(['match', a[i-1], b[j-1]]);
        i--; j--;
      } else if (i>0 && j>0 && dp[i][j] === dp[i-1][j-1] + 1){
        ops.push(['replace', a[i-1], b[j-1]]);
        i--; j--;
      } else if (i>0 && dp[i][j] === dp[i-1][j] + 1){
        ops.push(['delete', a[i-1], '']);
        i--;
      } else { // insertion into B (extra char typed)
        ops.push(['insert', '', b[j-1]]);
        j--;
      }
    }
    ops.reverse();

    // construct highlighted spans
    var expectedHTML = '';
    var userHTML = '';
    ops.forEach(function(op){
      var t = op[0], ca = op[1], cb = op[2];
      if (t === 'match'){
        expectedHTML += '<span style="background:#ddffea;color:#084;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;">' + esc(ca) + '</span>';
        userHTML     += '<span style="background:#ddffea;color:#084;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;">' + esc(cb) + '</span>';
      } else if (t === 'replace'){
        expectedHTML += '<span style="background:#ffecec;color:#900;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;">' + esc(ca) + '</span>';
        userHTML     += '<span style="background:#ffecec;color:#900;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;">' + esc(cb) + '</span>';
      } else if (t === 'delete'){
        expectedHTML += '<span style="background:#ffecec;color:#900;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;">' + esc(ca) + '</span>';
        userHTML     += '<span style="opacity:0.4;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;color:#666;">' + '␣' + '</span>';
      } else { // insert
        expectedHTML += '<span style="opacity:0.4;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;color:#666;">' + '␣' + '</span>';
        userHTML     += '<span style="background:#ffecec;color:#900;padding:2px 6px;border-radius:4px;margin:1px;display:inline-block;">' + esc(cb) + '</span>';
      }
    });

    // decide acceptance threshold: small words tolerate 1 typo, longer tolerate 2
    var threshold = (canonical.length <= 5) ? 1 : 2;
    var very_close_threshold = Math.max(1, Math.floor(canonical.length * 0.15)); // very small relative tolerance
    var status = 'incorrect';
    if (dist === 0) status = 'correct';
    else if (dist <= very_close_threshold) status = 'close';
    else if (dist <= threshold) status = 'almost';

    // build the status box
    var container = document.currentScript.parentNode;
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
      box.innerHTML = '<div style="font-weight:800;font-size:28px;">Correct</div><div style="margin-top:8px;font-size:28px;">' + esc(canonical) + '</div>';
    } else if (status === 'close' || status === 'almost'){
      box.style.background = '#fff7e6';
      box.style.color = '#6a4d00';
      box.innerHTML = '<div style="font-weight:800;font-size:28px;">Close</div>'
                    + '<div style="margin-top:8px;font-size:24px;">' + esc(canonical) + '</div>'
                    + '<div style="font-size:14px;margin-top:8px;color:#333;">Small spelling differences shown below.</div>';
    } else {
      box.style.background = '#ffecec';
      box.style.color = '#900';
      box.innerHTML = '<div style="font-weight:800;font-size:28px;">Answer</div>'
                    + '<div style="margin-top:8px;font-size:24px;">' + esc(canonical) + '</div>'
                    + '<div style="font-size:14px;margin-top:8px;color:#333;">Your attempt shown below.</div>';
    }
    container.appendChild(box);

    // show diff lines
    var diffWrap = document.createElement('div');
    diffWrap.style.marginTop = '16px';
    diffWrap.style.fontSize = '18px';
    diffWrap.style.lineHeight = '1.6';
    diffWrap.innerHTML = '<div style="margin-bottom:6px;font-weight:700;">Expected:</div><div>' + expectedHTML + '</div>'
                       + '<div style="margin-top:8px;font-weight:700;">You typed:</div><div>' + userHTML + '</div>'
                       + '<div style="margin-top:8px;color:#666;font-size:14px;">Edit distance: ' + dist + '</div>';
    container.appendChild(diffWrap);

    // show example only on back (fixed single-line string)
    var meta = document.createElement('div');
    meta.style.marginTop = '14px';
    meta.style.fontSize = '18px';
    meta.style.fontWeight = 'bold';
    meta.style.color = '#222';
    meta.style.lineHeight = '1.4';
    meta.innerHTML = '<div style="font-style:italic;color:#006;margin-top:6px;"><strong>Example:</strong><br>{{example}}</div>';
    container.appendChild(meta);

  })();
  </script>
</div>
"""

CSS = r"""
.card {
  font-family: 'Helvetica Neue', Arial;
  text-align: center;
  background: white;
  color: #111;
}
"""

my_model = genanki.Model(
    MODEL_ID,
    "TypedInputModelWithDiff",
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

deck = genanki.Deck(DECK_ID, "Typed Input Vocab Deck (diff)")

if not os.path.exists(INPUT):
    raise FileNotFoundError(f"Input CSV not found: {INPUT}")

with open(INPUT, encoding="utf-8", newline="") as csvfile:
    reader = csv.DictReader(csvfile)
    count = 0
    for row in reader:
        word = (row.get("word") or "").strip()
        pos = (row.get("pos") or "").strip()
        definition = (row.get("definition") or "").strip()
        example = (row.get("example") or "").strip()
        tags_raw = (row.get("tags") or "").strip()
        tags = [t.strip() for t in tags_raw.split(",")] if tags_raw else []

        if not word:
            continue

        uid = str(random.randrange(1 << 30, 1 << 60))
        note = genanki.Note(
            model=my_model, fields=[word, pos, definition, example, uid], tags=tags
        )
        deck.add_note(note)
        count += 1

package = genanki.Package(deck)
package.write_to_file(OUTPUT)
print(
    f"Wrote {OUTPUT} with {count} notes. Import into Anki (double-click or File → Import)."
)
