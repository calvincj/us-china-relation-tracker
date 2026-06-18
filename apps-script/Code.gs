// US-China Relations Tracker — Google Apps Script
//
// SETUP (one-time):
//   1. Open your tracker Google Doc → Extensions → Apps Script
//   2. Paste Code.gs here (no Sidebar.html needed)
//   3. Project Settings → Script Properties → add GEMINI_API_KEY = your key
//   4. Save and reopen the doc — an "Auto-Format" menu will appear
//
// USAGE:
//   1. Select text to format (or select nothing to format the whole doc)
//   2. Auto-Format → Format Entry — done

var GEMINI_MODEL   = 'gemini-2.5-flash';
var GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/' +
                     GEMINI_MODEL + ':generateContent';

// ── Menu ──────────────────────────────────────────────────────────────────────

function onOpen() {
  DocumentApp.getUi()
    .createMenu('Auto-Format')
    .addItem('▶ Run', 'runFormatter')
    .addToUi();
}

// ── Menu action — runs entirely server-side, no sidebar ──────────────────────

function runFormatter() {
  var ui   = DocumentApp.getUi();
  var doc  = DocumentApp.getActiveDocument();
  var body = doc.getBody();
  var rawText, indices;

  var selection = doc.getSelection();
  if (selection) {
    rawText = extractSelectionText_(selection);
    if (!rawText.trim()) { ui.alert('Selected text is empty.'); return; }
    indices = [];
    selection.getRangeElements().forEach(function(rangeEl) {
      try {
        var el = rangeEl.getElement();
        while (el.getParent() && el.getParent().getType() !== DocumentApp.ElementType.BODY_SECTION) {
          el = el.getParent();
        }
        var idx = body.getChildIndex(el);
        if (idx >= 0 && indices.indexOf(idx) === -1) indices.push(idx);
      } catch (e) {}
    });
  } else {
    var lines = [];
    indices = [];
    for (var i = 0; i < body.getNumChildren(); i++) {
      try {
        var text = body.getChild(i).asText().getText();
        if (text.trim()) lines.push(text);
      } catch (e) {}
      indices.push(i);
    }
    rawText = lines.join('\n');
    if (!rawText.trim()) { ui.alert('The document is empty.'); return; }
  }

  // Idempotency: if any selected paragraph is already indented it's already formatted.
  for (var fi = 0; fi < indices.length; fi++) {
    try {
      var fc = body.getChild(indices[fi]);
      if (fc.getType() === DocumentApp.ElementType.PARAGRAPH &&
          fc.asParagraph().getIndentStart() > 0) {
        ui.alert('This text looks already formatted (indented paragraphs found).\nSelect raw unformatted text and try again.');
        return;
      }
    } catch (e) {}
  }

  var paragraphs  = preprocessText_(rawText);
  var contentType = detectContentType_(paragraphs);
  var date        = extractDate_(rawText);
  var llm         = processWithLLM_(rawText, contentType, paragraphs);
  var summary     = llm.summary || '';

  // Insert in-place at the position of the first selected paragraph.
  var insertAt = indices.length > 0 ? Math.min.apply(null, indices) : body.getNumChildren();
  var counter  = { idx: insertAt };

  if (contentType === 'qa') {
    var exchanges = buildExchanges_(paragraphs, llm.exchanges || []);
    if (!exchanges.length) { ui.alert('No Q&A exchanges found — check text formatting.'); return; }

    // Split into separate entries when the answer speaker changes mid-document.
    var sections = splitExchangesBySpeaker_(exchanges);
    var totalQ = 0, totalA = 0;
    sections.forEach(function(section, si) {
      // First section reuses the summary already generated; extra sections get their own.
      var sectionSummary = (si === 0) ? summary : callLLM_(
        'You are writing for the Brookings Institution US-China Relations Tracker.\n' +
        'Write exactly ONE sentence summarizing this content.\n\n' +
        SUMMARY_RULES_ +
        '\nContent:\n' + section.map(function(ex) {
          return (ex.speaker ? ex.speaker + ': ' : '') + ex.text;
        }).join('\n').substring(0, 3000)
      );
      appendQAEntry_(body, counter, date, sectionSummary, section);
      totalQ += section.filter(function(e) { return e.type === 'Q'; }).length;
      totalA += section.filter(function(e) { return e.type === 'A'; }).length;
    });

    var doneMsg = '✓ Done — ' + fmtDate_(date);
    if (sections.length > 1) doneMsg += '  (' + sections.length + ' entries, ' + totalQ + ' Q, ' + totalA + ' A)';
    else doneMsg += '  (' + totalQ + ' Q, ' + totalA + ' A)';
    doneMsg += '\n\n' + summary;
    ui.alert(doneMsg);
  } else {
    var paras = llm.paragraphs || [];
    appendReleaseEntry_(body, counter, date, summary, paras);
    ui.alert('✓ Done — ' + fmtDate_(date) + '\n\n' + summary + '\n\n(' + paras.length + ' paragraphs)');
  }

  // Originals shifted down by however many paragraphs we inserted.
  var insertCount = counter.idx - insertAt;
  indices.sort(function(a, b) { return b - a; });
  indices.forEach(function(idx) {
    try { body.getChild(idx + insertCount).removeFromParent(); } catch (e) {}
  });
}

// ── Selection helpers ─────────────────────────────────────────────────────────

function extractSelectionText_(selection) {
  var lines = [];
  selection.getRangeElements().forEach(function(rangeEl) {
    try {
      var el   = rangeEl.getElement();
      var full = el.asText().getText();
      lines.push(
        rangeEl.isPartial()
          ? full.substring(rangeEl.getStartOffset(), rangeEl.getEndOffsetInclusive() + 1)
          : full
      );
    } catch (e) {}
  });
  return lines.join('\n');
}

// ── LLM calls (Gemini with Groq fallback) ────────────────────────────────────

function callGemini_(prompt) {
  var apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  if (!apiKey) throw new Error('Add GEMINI_API_KEY in Project Settings → Script Properties');

  for (var attempt = 0; attempt < 3; attempt++) {
    if (attempt > 0) Utilities.sleep(4000 * attempt);
    var resp = UrlFetchApp.fetch(GEMINI_API_URL + '?key=' + apiKey, {
      method:             'post',
      contentType:        'application/json',
      payload:            JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
      muteHttpExceptions: true,
    });
    var data = JSON.parse(resp.getContentText());
    if (data.error) {
      var code = data.error.code || 0;
      if ((code === 429 || code === 503) && attempt < 2) continue;
      throw new Error('Gemini error: ' + data.error.message);
    }
    return data.candidates[0].content.parts[0].text.trim();
  }
  throw new Error('Gemini failed after 3 attempts');
}

function callGroq_(prompt) {
  var apiKey = PropertiesService.getScriptProperties().getProperty('GROQ_API_KEY');
  if (!apiKey) throw new Error('Add GROQ_API_KEY in Project Settings → Script Properties');

  var resp = UrlFetchApp.fetch('https://api.groq.com/openai/v1/chat/completions', {
    method:             'post',
    contentType:        'application/json',
    headers:            { 'Authorization': 'Bearer ' + apiKey },
    payload:            JSON.stringify({
      model:       'llama-3.3-70b-versatile',
      messages:    [{ role: 'user', content: prompt }],
      temperature: 0.3,
    }),
    muteHttpExceptions: true,
  });

  var data = JSON.parse(resp.getContentText());
  if (data.error) throw new Error('Groq error: ' + (data.error.message || JSON.stringify(data.error)));
  return data.choices[0].message.content.trim();
}

// Try Gemini first; fall back to Groq if Gemini fails completely.
function callLLM_(prompt) {
  try {
    return callGemini_(prompt);
  } catch (geminiErr) {
    try {
      return callGroq_(prompt);
    } catch (groqErr) {
      throw new Error('Gemini: ' + geminiErr.message + ' | Groq: ' + groqErr.message);
    }
  }
}

// ── Text helpers ──────────────────────────────────────────────────────────────

function preprocessText_(text) {
  var lines = text.split('\n').map(function(l) { return l.trim(); }).filter(Boolean);
  if (lines.length >= 3) return lines;

  var combined = lines.join(' ');
  var parts    = combined.split(/(?<=[.?!])\s+(?=[A-Z][A-Za-z0-9 \-'\.]{1,40}:\s)/);
  if (parts.length >= 2) {
    return parts.map(function(p) { return p.trim(); }).filter(Boolean);
  }
  return combined ? [combined.trim()] : [];
}

function detectContentType_(paragraphs) {
  var hits = paragraphs.filter(function(p) {
    return /^[A-Z][A-Za-z0-9 \-'\.]{1,40}:\s+/.test(p);
  }).length;
  return hits >= 2 ? 'qa' : 'release';
}

function extractDate_(text) {
  var m = text.match(/\b(\d{4}-\d{2}-\d{2})\b/);
  if (m) return new Date(m[1] + 'T12:00:00');

  var MONTHS = {
    January:0, February:1, March:2, April:3, May:4, June:5,
    July:6, August:7, September:8, October:9, November:10, December:11,
  };
  m = text.match(
    /\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})\b/
  );
  if (m) return new Date(parseInt(m[3]), MONTHS[m[1]], parseInt(m[2]));

  return new Date();
}

function fmtDate_(date) {
  var MONTHS = ['January','February','March','April','May','June',
                'July','August','September','October','November','December'];
  return MONTHS[date.getMonth()] + ' ' + date.getDate() + ', ' + date.getFullYear();
}

// ── Hardcoded speaker lookup (built from past tracker data) ──────────────────

var KNOWN_Q_ = (function() {
  var s = {};
  [
    // Generic roles
    'reporter','the press','press','question','journalist','host',
    'interviewer','member of the press','a reporter asked','congressperson',
    // Wire services & outlets
    'afp','bloomberg','reuters','ap','associated press',
    'fox news','fox business','fox','cnbc','nbc','abc news','abc','cnn','cbs',
    'cctv','global times','nhk','ria novosti','time',
    'the new york times','new york times','nyt',
    'wall street journal','wsj','financial times','ft',
    'anadolu agency','china news service','beijing youth daily',
    'shenzhen tv','china-arab tv','telesur',
    // Named reporters seen in trackers
    'sean hannity','laura ingraham','maria bartiromo','kristen welker',
    'andrew ross sorkin','david e. sanger','joe kernen','martha raddatz',
    'michael froman','tom llamas','jake tapper','david muir',
  ].forEach(function(k) { s[k] = true; });
  return s;
})();

var KNOWN_A_ = (function() {
  var s = {};
  [
    // US officials
    'president trump','donald trump','trump','the president',
    'president donald trump','karoline leavitt','ms. leavitt','ms leavitt','leavitt',
    'jd vance','vice president vance','vance',
    'secretary bessent','scott bessent','bessent','treasury secretary bessent',
    'secretary rubio','marco rubio','rubio','secretary of state rubio',
    'ambassador greer','jamieson greer','ustr greer',
    'u.s. trade representative greer','u.s. trade representative jamieson greer',
    'secretary lutnick','howard lutnick','lutnick',
    'secretary hegseth','pete hegseth','hegseth',
    'secretary wright','chris wright',
    'secretary burgum','doug burgum','burgum',
    'kash patel','david perdue','ambassador perdue','david purdue',
    'elbridge colby','jacob helberg','kevin hassett','hassett',
    'peter navarro','navarro','stephen miller','adam smith',
    'ms. bruce','ms bruce',
    // Chinese officials
    'lin jian','mao ning','guo jiakun','he yongqian','he yadong',
    'zhang xiaogang','jiang bin','wang yi','spokesperson mao ning',
    'spokesperson lin jian',
    // Generic
    'spokesperson','the spokesperson',
  ].forEach(function(k) { s[k] = true; });
  return s;
})();

// Title prefixes that reliably indicate an official (A)
var A_PREFIXES_ = [
  'secretary ','ambassador ','president ','vice president ',
  'under secretary ','deputy secretary ','ustr ',
  'national security advisor ','director ','representative ',
];

function classifyBySpeaker_(name) {
  var lower = name.toLowerCase().trim();
  if (KNOWN_Q_[lower]) return 'Q';
  if (KNOWN_A_[lower]) return 'A';
  for (var i = 0; i < A_PREFIXES_.length; i++) {
    if (lower.indexOf(A_PREFIXES_[i]) === 0) return 'A';
  }
  // "Rep. X" querying a witness → Q
  if (/^rep\.\s/.test(lower) || /^senator\s/.test(lower)) return 'Q';
  return null; // unknown — needs Gemini
}

// Returns array where each element is {type, speaker} if the speaker is
// recognized, or null if unknown (those get sent to Gemini).
function getHardcodedLabels_(paragraphs) {
  var SPEAKER_RE = /^([A-Z][A-Za-z0-9 \-'\.,]{1,70}):\s*/;
  return paragraphs.map(function(para) {
    var m = para.match(SPEAKER_RE);
    if (!m) return { type: 'CONT', speaker: null };
    var type = classifyBySpeaker_(m[1].trim());
    return type ? { type: type, speaker: m[1].trim() } : null;
  });
}

function parseGeminiJson_(raw) {
  var cleaned = raw.replace(/^```(?:json)?\s*|\s*```$/gm, '').trim();
  try { return JSON.parse(cleaned); } catch (e) {}
  var m = cleaned.match(/\{[\s\S]*\}/);
  if (m) { try { return JSON.parse(m[0]); } catch (e2) {} }
  return null;
}

// ── LLM ───────────────────────────────────────────────────────────────────────

var SUMMARY_RULES_ =
  '- Start with the official\'s title + name (e.g. "Foreign Ministry Spokesperson Lin Jian")\n' +
  '- Use active verbs: "addressed reporters\' questions on", "held a press briefing on",\n' +
  '  "released a statement on", "issued a readout on"\n' +
  '- Name the specific topic (tariffs, Taiwan, semiconductors, etc.)\n' +
  '- Do NOT start with "The"\n' +
  '- Output the sentence only — no JSON, no quotes, no extra text\n';

function processWithLLM_(rawText, contentType, paragraphs) {

  if (contentType === 'qa') {
    var labels = getHardcodedLabels_(paragraphs);
    var unknownIdx = [];
    labels.forEach(function(l, i) { if (!l) unknownIdx.push(i); });

    if (unknownIdx.length === 0) {
      // Every speaker recognized — only need a summary from Gemini
      var sum = callLLM_(
        'You are writing for the Brookings Institution US-China Relations Tracker.\n' +
        'Write exactly ONE sentence summarizing the content below.\n\n' +
        SUMMARY_RULES_ + '\nContent:\n' + rawText.substring(0, 4000)
      );
      return { summary: sum, exchanges: labels };
    }

    // Send Gemini only the unrecognized paragraphs + ask for summary
    var unknownParas  = unknownIdx.map(function(i) { return paragraphs[i]; });
    var numbered = unknownParas.map(function(p, j) {
      return '[' + (j + 1) + '] ' + p;
    }).join('\n');

    var qaPrompt =
      'You are working for the Brookings Institution US-China Relations Tracker.\n\n' +
      'Do TWO things and return a single JSON object.\n\n' +
      '1. SUMMARY — write exactly one sentence:\n' + SUMMARY_RULES_ + '\n' +
      '2. CLASSIFY each numbered paragraph as Q, A, or CONT:\n' +
      '   Q = journalist / media outlet asking a question\n' +
      '   A = government official, spokesperson, or department responding\n' +
      '   CONT = continuation of previous A, no new speaker label\n' +
      '   "speaker" = name before the colon, or null for CONT.\n\n' +
      'Return ONLY this JSON:\n' +
      '{"summary":"...","exchanges":[{"type":"Q","speaker":"Reuters"},{"type":"A","speaker":"Lin Jian"}]}\n\n' +
      'Full content (context):\n' + rawText.substring(0, 3000) +
      '\n\nParagraphs to classify:\n' + numbered;

    var result = null;
    for (var attempt = 0; attempt < 2; attempt++) {
      result = parseGeminiJson_(callLLM_(qaPrompt));
      if (result) break;
    }
    if (!result) throw new Error('Gemini returned unparseable JSON twice — try again');

    // Merge Gemini's answers back at the exact positions that were unknown
    (result.exchanges || []).forEach(function(ex, j) {
      if (j < unknownIdx.length) {
        labels[unknownIdx[j]] = {
          type:    (ex.type || 'A').toUpperCase(),
          speaker: (ex.speaker || '').replace(/:$/, '').trim(),
        };
      }
    });
    // Safety: fill any still-null positions as CONT
    labels = labels.map(function(l) { return l || { type: 'CONT', speaker: null }; });

    return { summary: result.summary || '', exchanges: labels };
  }

  // release / press statement — always needs Gemini for both summary + paragraphs
  var releasePrompt =
    'You are working for the Brookings Institution US-China Relations Tracker.\n\n' +
    'Do TWO things and return a single JSON object.\n\n' +
    '1. SUMMARY — write exactly one sentence:\n' + SUMMARY_RULES_ + '\n' +
    '2. PARAGRAPHS — extract the 5 most informative verbatim paragraphs about\n' +
    '   US-China relations (trade, tariffs, technology, Taiwan, diplomacy).\n' +
    '   Copy verbatim — no paraphrasing. Preserve any speaker labels.\n\n' +
    'Return ONLY this JSON:\n' +
    '{"summary":"...","paragraphs":["para1","para2","para3","para4","para5"]}\n\n' +
    'Text:\n' + rawText.substring(0, 8000);

  var res = null;
  for (var attempt2 = 0; attempt2 < 2; attempt2++) {
    res = parseGeminiJson_(callLLM_(releasePrompt));
    if (res) break;
  }
  if (!res) throw new Error('Gemini returned unparseable JSON twice — try again');
  return res;
}

// Splits exchanges into separate sections when the A speaker changes.
// Each section becomes its own dated entry.
function splitExchangesBySpeaker_(exchanges) {
  var sections   = [];
  var current    = [];
  var curSpeaker = null;

  exchanges.forEach(function(ex) {
    if (ex.type === 'A' && ex.speaker) {
      if (curSpeaker && ex.speaker !== curSpeaker) {
        sections.push(current);
        current = [];
      }
      curSpeaker = ex.speaker;
    }
    current.push(ex);
  });
  if (current.length) sections.push(current);
  return sections.length ? sections : [exchanges];
}

function buildExchanges_(paragraphs, labels) {
  var SPEAKER_RE = /^([A-Z][A-Za-z0-9 \-'\.]{1,40}):\s*/;
  var exchanges  = [];

  paragraphs.forEach(function(para, i) {
    var label   = labels[i] || { type: 'A', speaker: null };
    var type    = String(label.type || 'A').toUpperCase();
    if (['Q', 'A', 'CONT'].indexOf(type) === -1) type = 'A';
    var speaker = (label.speaker || '').trim().replace(/:$/, '');
    var text;

    if (speaker) {
      var escaped = speaker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      text = para.replace(new RegExp('^' + escaped + '\\s*:\\s*', 'i'), '').trim();
      if (text === para.trim()) text = para.replace(SPEAKER_RE, '').trim();
    } else {
      var m2 = para.match(SPEAKER_RE);
      if (m2 && type === 'CONT') {
        speaker = m2[1].trim();
        text    = para.substring(m2[0].length).trim();
        type    = 'A';
      } else {
        text = para.trim();
      }
    }

    if (text) exchanges.push({ type: type, speaker: speaker, text: text });
  });

  return exchanges;
}

// ── Document writing ──────────────────────────────────────────────────────────

function baseStyle_() {
  var A = DocumentApp.Attribute;
  var s = {};
  s[A.FONT_FAMILY]   = 'Times New Roman';
  s[A.FONT_SIZE]     = 12;
  s[A.LINE_SPACING]  = 1.15;
  s[A.SPACING_AFTER] = 8;
  s[A.BOLD]          = false;
  s[A.ITALIC]        = false;
  return s;
}

function appendDateHeading_(body, counter, dateStr) {
  var para = body.insertParagraph(counter.idx++, dateStr);
  para.setAttributes(baseStyle_());
  para.editAsText().setBold(true);
}

function appendSummaryPara_(body, counter, text) {
  body.insertParagraph(counter.idx++, text).setAttributes(baseStyle_());
}

function appendIndentedPara_(body, counter, parts) {
  var para = body.insertParagraph(counter.idx++, '');
  para.setAttributes(baseStyle_());
  para.setIndentStart(36);
  para.setIndentFirstLine(36);

  parts.forEach(function(part) {
    if (!part.text) return;
    var t = para.appendText(part.text);
    t.setFontFamily('Times New Roman');
    t.setFontSize(12);
    t.setBold(!!part.bold);
    t.setItalic(!!part.italic);
  });
}

function appendSeparator_(body, counter) {
  var A     = DocumentApp.Attribute;
  var style = {};
  style[A.SPACING_AFTER]  = 0;
  style[A.SPACING_BEFORE] = 0;
  body.insertParagraph(counter.idx++, '').setAttributes(style);
}

function appendQAEntry_(body, counter, date, summary, exchanges) {
  appendDateHeading_(body, counter, fmtDate_(date));
  appendSummaryPara_(body, counter, summary);

  exchanges.forEach(function(ex) {
    if (ex.type === 'Q') {
      appendIndentedPara_(body, counter, [
        { text: ex.speaker + ': ', bold: true,  italic: true  },
        { text: ex.text,           bold: false, italic: true  },
      ]);
    } else if (ex.type === 'A') {
      appendIndentedPara_(body, counter, [
        { text: ex.speaker + ':',  bold: true,  italic: false },
        { text: ' ' + ex.text,    bold: false, italic: false },
      ]);
    } else {
      appendIndentedPara_(body, counter, [{ text: ex.text, bold: false, italic: false }]);
    }
  });

  appendSeparator_(body, counter);
}

function appendReleaseEntry_(body, counter, date, summary, paragraphs) {
  appendDateHeading_(body, counter, fmtDate_(date));
  appendSummaryPara_(body, counter, summary);

  var SPEAKER_RE = /^([A-Z][A-Za-z0-9 \-'\.]{1,50}):\s+(.+)$/s;

  paragraphs.forEach(function(paraText) {
    var m = paraText.match(SPEAKER_RE);
    if (m) {
      appendIndentedPara_(body, counter, [
        { text: m[1] + ':',  bold: true,  italic: false },
        { text: ' ' + m[2], bold: false, italic: false },
      ]);
    } else {
      appendIndentedPara_(body, counter, [{ text: paraText, bold: false, italic: false }]);
    }
  });

  appendSeparator_(body, counter);
}
