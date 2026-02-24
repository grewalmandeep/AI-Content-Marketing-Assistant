require('dotenv').config();
const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const axios = require('axios');

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const DRAFTS_FILE = path.join(__dirname, '.drafts.json');
let drafts = [];
try {
  if (fs.existsSync(DRAFTS_FILE)) drafts = JSON.parse(fs.readFileSync(DRAFTS_FILE, 'utf8')) || [];
} catch (e) {
  console.error('Could not read drafts file, starting empty', e);
  drafts = [];
}

function saveDrafts() {
  fs.writeFileSync(DRAFTS_FILE, JSON.stringify(drafts, null, 2));
}

// Simple retry controller
async function withRetry(fn, attempts = 3, delayMs = 500) {
  let lastErr;
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      await new Promise(r => setTimeout(r, delayMs * (i + 1)));
    }
  }
  throw lastErr;
}

// Minimal intent detector (rule-based)
function detectIntent({subject, body}) {
  const text = (subject + ' ' + body).toLowerCase();
  if (/meeting|schedule|reschedule|calendar/.test(text)) return 'schedule_meeting';
  if (/follow up|follow-up|following up|checking in/.test(text)) return 'follow_up';
  if (/thank|thanks|appreciate/.test(text)) return 'thank_you';
  if (/complain|issue|problem|support/.test(text)) return 'support_request';
  return 'general';
}

// Tone stylizer: simple templates
function stylizeTone(tone, content) {
  switch (tone) {
    case 'casual':
      return content + '\n\nCheers,\n[Your Name]';
    case 'formal':
      return 'Dear ' + (content.to ? content.to : 'Sir/Madam') + ',\n\n' + content.body + '\n\nSincerely,\n[Your Name]';
    case 'concise':
      return content.body.split('\n').slice(0,2).join('\n') + '\n\nBest,\n[Your Name]';
    default:
      return content.body + '\n\nBest,\n[Your Name]';
  }
}

// Draft writer: either call Claude (if configured) or use a simple local generator
async function callClaude(prompt) {
  const CLAUDE_API_KEY = process.env.CLAUDE_API_KEY;
  if (!CLAUDE_API_KEY) throw new Error('Claude API key not configured');
  // Note: Actual Claude API shape may differ; this is a placeholder for integration.
  const res = await axios.post('https://api.anthropic.com/v1/complete', {
    prompt,
    model: 'claude-3',
    max_tokens_to_sample: 600
  }, { headers: { 'x-api-key': CLAUDE_API_KEY } });
  return res.data;
}

async function generateDraft(payload) {
  // pipeline: intent -> tone -> draft
  const intent = detectIntent(payload);
  const tone = payload.tone || 'default';

  const baseContent = {
    to: payload.to || '',
    subject: payload.subject || '',
    body: payload.body || ''
  };

  // If CLAUDE configured, call it with the orchestrated prompt, with retry
  if (process.env.CLAUDE_API_KEY) {
    const prompt = `You are an email assistant. Intent: ${intent}. Tone: ${tone}. Compose a professional email from the following fields:\nTo: ${baseContent.to}\nSubject: ${baseContent.subject}\nBody: ${baseContent.body}`;
    const res = await withRetry(() => callClaude(prompt), 3, 700);
    // naive mapping
    const text = res?.completion || res?.output || JSON.stringify(res);
    return { to: baseContent.to, subject: baseContent.subject || ('Re: ' + intent), body: text };
  }

  // Local generator (deterministic)
  let body = '';
  switch (intent) {
    case 'schedule_meeting':
      body = `Hi ${baseContent.to || ''},\n\nI'd like to schedule a meeting to discuss ${baseContent.subject || 'the topic'}. Are you available next week for a 30-minute call? Please let me know a few times that work for you.\n\nThanks,`;
      break;
    case 'follow_up':
      body = `Hi ${baseContent.to || ''},\n\nI'm following up on my previous message about ${baseContent.subject || 'this'}. Do you have any updates?\n\nBest regards,`;
      break;
    case 'thank_you':
      body = `Hi ${baseContent.to || ''},\n\nThank you for ${baseContent.body || 'your help'}. I really appreciate it.\n\nWarmly,`;
      break;
    case 'support_request':
      body = `Hi ${baseContent.to || ''},\n\nI'm experiencing an issue: ${baseContent.body || 'describe problem'}. Could you please help or advise on next steps?\n\nThanks,`;
      break;
    default:
      body = `Hi ${baseContent.to || ''},\n\n${baseContent.body || 'I hope you are well.'}\n\nRegards,`;
  }

  // apply tone
  const stylized = stylizeTone(tone, { to: baseContent.to, body });
  return { to: baseContent.to, subject: baseContent.subject || ('Re: ' + intent), body: stylized };
}

// Routes
app.post('/api/generate', async (req, res) => {
  try {
    const payload = req.body;
    const draft = await withRetry(() => generateDraft(payload), 3, 400);
    res.json({ ok: true, draft });
  } catch (err) {
    console.error('generate error', err);
    res.status(500).json({ ok: false, error: err.message });
  }
});

app.post('/api/save', (req, res) => {
  const { draft, name } = req.body;
  const id = Date.now().toString(36);
  const entry = { id, name: name || draft.subject || ('Draft ' + id), draft, createdAt: new Date().toISOString() };
  drafts.unshift(entry);
  saveDrafts();
  res.json({ ok: true, entry });
});

app.get('/api/drafts', (req, res) => {
  res.json({ ok: true, drafts });
});

app.get('/api/drafts/:id', (req, res) => {
  const d = drafts.find(x => x.id === req.params.id);
  if (!d) return res.status(404).json({ ok: false });
  res.json({ ok: true, draft: d });
});

const PORT = process.env.PORT || 3333;
app.listen(PORT, () => console.log(`AI Email Assistant running on http://localhost:${PORT}`));
