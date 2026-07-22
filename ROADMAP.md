# Brain — Feature Roadmap

> Prioritized backlog for building an **intelligent layer** that knows your complete financial situation and helps you make the best decisions — directing investments, keeping spending in check while you enjoy life, and aligning everything toward your goals.

Related docs: [README.md](README.md) (setup & deploy) · [VISION.md](VISION.md) (philosophy & architecture)

---

## North Star

Brain becomes a personal financial brain that:

1. **Invests** — portfolio moves serve your goals, not generic advice
2. **Spends** — enjoy life within limits; know when to splurge and when to pause
3. **Aligns** — goals, income, loans, and cash flow tell one coherent story

---

## Shipped Today

| Area | What's live |
|------|-------------|
| **Invest** | Robinhood (SnapTrade) + manual India FD/MF/stock; portfolio hero, P&L, allocation bars |
| **Spend** | Plaid bank/cards + Splitwise; unified timeline; monthly budget + remaining; purchase & daily budget push alerts |
| **Goals** | NL goal entry + LLM extraction; goal cards |
| **Income** | NL paycheck + allocation plan (PIN-gated) |
| **Infra** | PIN-protected PWA, Railway deploy, cron notifications, SQLite/Postgres |

**Not shipped (removed Jul 2026):** Spending history — partial backend only; removed until P3.1 rebuild (see backlog).

---

## Build Order (Priority Sequence)

Features are grouped by domain below, but **build in this order**:

```
P0 Foundation → P3 Early (spending structure) → P0 Full → P1 Chat → P2 Decisions → P3 Later → P4 Invest → P5 Proactive → P6 Polish
```

| Phase | Build | Outcome |
|-------|-------|---------|
| **1** | P0.1 + P3.2–P3.3, P3.6 | Structured spending + thin context snapshot |
| **2** | P0.2–P0.5 | Complete financial graph (loans, balances, rollups) |
| **3** | P1.1–P1.6 | Chat with rich spending context |
| **4** | P2.1–P2.5 | Goal/affordability/enjoy-life decisions |
| **5** | P3.4–P3.5 + P4 | Smarter nudges + investment direction |
| **6** | P5 + P6 | Proactive reviews + polish |

**MVP (feels intelligent):** Phases 1–3 + P2.1–P2.3  
**Full contextual knowledge:** Phase 2 + P1.5–P1.6 + P2.4–P2.5  
**Best-decisions north star:** Phases 5–6

---

## Backlog (by Priority Tier)

### Phase 1 — Foundation + Spending Structure

#### P0.1 — Financial context builder
- [ ] `integrations/financial_context.py` — single snapshot of portfolio + spending + goals + income for any AI call

#### P3 Early — Spending structure (before chat)
- [ ] **P3.1** Spending history — **removed from app (Jul 2026); rebuild later** — past billing periods (6th–6th), period totals aligned with budget meter, drill-down txn list, month-over-month trends. Prior partial API/UI was incomplete and removed; do not re-ship until spec + budget/history math are unified.
- [ ] **P3.2** Budget envelopes / categories (dining, travel, fun, etc.)
- [ ] **P3.3** Auto-categorization rules (Plaid categories → envelopes)
- [ ] **P3.6** Splitwise ↔ card dedupe UI (backend logic partially exists)

---

### Phase 2 — Complete Financial Graph

- [ ] **P0.2** Loan tracking (NL entry like Goals)
- [ ] **P0.3** Account balances in context (Plaid checking/savings)
- [ ] **P0.4** Spending history rollups in context (3–6 billing periods)
- [ ] **P0.5** Category & merchant summaries (trends without raw txn dumps)

---

### Phase 3 — Conversational Intelligent Layer

- [ ] **P1.1** Chat API (`POST /api/chat`, message persistence)
- [ ] **P1.2** Chat-capable LLM client (multi-turn, text mode)
- [ ] **P1.3** Financial advisor system prompt (cite data, respect goals, admit gaps)
- [ ] **P1.4** Chat UI tab (message thread, input, starter prompts)
- [ ] **P1.5** Income PIN unlock in chat
- [ ] **P1.6** Conversation memory (persist thread, last N messages)

**Starter prompts for chat v1:**
- "How am I doing on budget this month?"
- "Am I on track for my goals?"
- "Can I afford [X] without hurting my savings?"
- "Where is my money actually going?"
- "What should I prioritize paying off vs investing?"

---

### Phase 4 — Cross-Domain Decision Intelligence

- [ ] **P2.1** Goal progress math (passive income target vs portfolio; capital gap)
- [ ] **P2.2** Budget vs income allocation (planned vs actual savings rate)
- [ ] **P2.3** Affordability checks ("$X spend → goal slips N months")
- [ ] **P2.4** Loan + goal linkage (EMI impact on free cash and timelines)
- [ ] **P2.5** Enjoy-life framing (discretionary vs fixed; "you have room for this")

---

### Phase 5 — Spending Proactive + Investment Intelligence

#### P3 Later — Proactive spending (after P2)

- [ ] **P3.4** Drift detection ("dining 40% over usual pace")
- [ ] **P3.5** Smarter purchase nudges (category envelope + goals, not just total budget)

#### P4 — Investment intelligence

- [ ] **P4.1** Safe ↔ Risk posture setting
- [ ] **P4.2** Goal-linked allocation view
- [ ] **P4.3** AI portfolio analysis (news, price action, goal relevance)
- [ ] **P4.4** Rebalance suggestions
- [ ] **P4.5** Watchlist
- [ ] **P4.6** Price alerts (±% on holdings or watchlist)

---

### Phase 6 — Proactive Brain + Polish

#### P5 — Proactive nudges & reviews

- [ ] **P5.1** Weekly financial review push (LLM summary)
- [ ] **P5.2** Goal milestone alerts
- [ ] **P5.3** Spending pace warnings (mid-period envelope overshoot)
- [ ] **P5.4** Investment drift / concentration alerts

#### P6 — Polish & scale

- [ ] **P6.1** Chat streaming (SSE)
- [ ] **P6.2** Context cache + smart refresh
- [ ] **P6.3** Token/cost logging + rate limits
- [ ] **P6.4** Chat + context tests
- [ ] **P6.5** Postgres / job queue (when SQLite or cron limits bite)
- [ ] **P6.6** RAG / document upload (defer — tax docs, loan PDFs)

---

## Domain Reference

Quick lookup by area (same items as above, different grouping):

| Tier | Domain | Focus |
|------|--------|-------|
| P0 | Complete financial graph | Context builder, loans, balances, rollups, summaries |
| P3 Early | Spending structure | Envelopes, categorization, dedupe; **history deferred (P3.1)** |
| P1 | Chat | API, LLM client, UI, income unlock, memory |
| P2 | Cross-domain decisions | Goal progress, affordability, enjoy-life framing |
| P3 Later | Spending proactive | Drift detection, smarter nudges |
| P4 | Investment intelligence | Risk posture, goal allocation, analysis, watchlist, alerts |
| P5 | Proactive brain | Weekly reviews, milestone & pace alerts |
| P6 | Polish & scale | Streaming, caching, tests, infra |

---

## What We're Building Next

**Current focus:** Phase 1 — P0.1 context builder + P3 Early (envelopes, categorization, dedupe). **Spending history (P3.1) deferred** until current-period Spend/Budget is stable.

---

## Final App Snapshot

What Brain looks like when every phase in this roadmap is complete — a single PIN-protected PWA on your iPhone Home Screen with five tabs and an intelligent layer running underneath everything.

### App Shell

| Element | Final behavior |
|---------|----------------|
| **Navigation** | Bottom tabs: **Chat** · **Invest** · **Budget** · **Goals** · **Loans** (+ Settings gear) |
| **Auth** | PIN unlock on launch; income/salary details require a second PIN unlock inside Budget and Chat |
| **Design** | Dark theme, hero metrics at top of each tab, scrollable detail lists, allocation bars, status pills (Live / Cached) |
| **Platform** | PWA — Add to Home Screen, push notifications, works offline for cached data |

---

### Chat — The Intelligent Layer

The primary way you interact with Brain. Every answer is grounded in your real data, not generic finance advice.

| Capability | What you experience |
|------------|---------------------|
| **Conversational Q&A** | Ask anything in natural language; multi-turn memory remembers context within a session |
| **Full financial context** | Brain knows portfolio, cash balances, spending (current + history), envelopes, goals, loans, income allocations |
| **Starter prompts** | Tap suggestions like "How am I doing on budget?", "Can I afford a $500 trip?", "Am I on track for FI?" |
| **Cited answers** | Replies reference specific numbers: "$847 left in Dining", "portfolio at $42,300", "home goal 38% funded" |
| **Affordability checks** | "If I buy this, here's what's left and how it affects goal X" |
| **Enjoy-life framing** | Brain distinguishes fixed vs discretionary spend and tells you when you genuinely have room to splurge |
| **Investment guidance** | Rebalance ideas, risk posture drift, which holdings align with which goals |
| **Income privacy** | Salary/allocation hidden until PIN unlock; Brain says when answers are approximate |
| **Streaming replies** | Responses stream token-by-token on mobile for a responsive feel |

**Example interactions:**
- *"Should I pay extra on my car loan or invest this month?"* → compares loan rate, goal timeline, and free cash
- *"Where did my money go last month?"* → category breakdown, top merchants, vs your envelopes
- *"Am I being too tight on fun spending?"* → discretionary pace vs income plan and goals

---

### Invest Tab

Portfolio view tied to goals and risk posture — not a standalone brokerage mirror.

| Section | Final behavior |
|---------|----------------|
| **Hero card** | Total portfolio value (USD), combined US + India; P&L badge and return % |
| **Metrics row** | Invested · Return % · Holdings count · **Goal alignment %** |
| **Risk posture** | Safe ↔ Risk band you set; pill shows current posture vs target; alert when drifted |
| **Goal-linked allocation** | Breakdown: how much of portfolio maps to each goal (FI, house fund, etc.) |
| **Holdings list** | Grouped: US stocks (Robinhood) · Indian stocks · Mutual funds · Fixed deposits |
| **Per-holding row** | Ticker, shares/units, allocation bar, USD value, P&L; tap for **AI analysis card** (news, price action, goal relevance) |
| **Watchlist** | Names you track but don't hold; same analysis and price alerts |
| **Rebalance suggestions** | Card or chat-driven: "You're 12% overweight tech vs your Safe posture" |
| **Actions** | Connect Robinhood · Add manual India investment (FD / MF / Stock) |

---

### Budget Tab

Two sub-views: **Spend** and **Income**. Spending is structured, historical, and proactive — not just a transaction dump.

#### Spend view

| Section | Final behavior |
|---------|----------------|
| **Hero card** | Budget remaining for current billing period (6th–5th); progress bar; period label |
| **Metrics row** | Used · Card spend · Splitwise net · **Envelope health** (how many categories on track) |
| **Envelope cards** | Per-category limits: Dining, Travel, Fun, Groceries, etc. — spent / limit / pace indicator |
| **Drift warnings** | Inline flags: "Dining 40% over usual pace with 12 days left" |
| **Unified expense list** | Bank / Card / Splitwise tags; institution logos; category badge; exclude or edit amount |
| **Dedupe** | Splitwise charges that match a card txn shown once, clearly linked |
| **Spending history** *(P3.1 — not shipped)* | Past billing periods, trends, category charts — rebuild after budget/history math spec |
| **Cash snapshot** | Checking + savings balances from Plaid (for "can I afford this?" context) |

#### Income view (PIN-gated)

| Section | Final behavior |
|---------|----------------|
| **Paycheck description** | NL textarea describing take-home and pay frequency |
| **Brain summary card** | LLM-parsed monthly take-home, pay schedule |
| **Allocation chips** | % to savings, rent, fun, investments, etc. |
| **Planned vs actual** | Compare allocation plan to real spending this period — surfaced here and in Chat |

---

### Goals Tab

Your north star — everything else orients toward these.

| Section | Final behavior |
|---------|----------------|
| **Goal cards** | Title, summary, last updated; tier badges (life goal, milestone, etc.) |
| **Progress indicators** | Capital required vs saved; passive income target vs portfolio yield; timeline |
| **Goal editor** | NL textarea → Brain extracts structured goals (amounts, timelines, intent) |
| **Linkage hints** | Each goal shows: linked portfolio slice, spending envelope impact, loan constraints |
| **Milestone alerts** | Push when you hit 25% / 50% / 75% of a goal |

**Example goals Brain understands:**
- Financial independence with $4k/mo passive income by 2035
- House down payment $80k in 3 years
- Pay off student loan while maintaining 20% savings rate

---

### Loans Tab

Dedicated view for liabilities — NL entry like Goals, fully wired into Chat and affordability math.

| Section | Final behavior |
|---------|----------------|
| **Loan cards** | Lender, type (student, car, mortgage, personal), remaining balance, rate, monthly payment |
| **Loan editor** | Describe loans in plain English → Brain extracts structured fields |
| **Impact summary** | Total monthly EMI · % of take-home · effect on goal timelines |
| **Payoff context** | Chat and cards answer: extra payment vs invest, refinance worth it?, priority order |

---

### Settings

| Section | Final behavior |
|---------|----------------|
| **Connections** | Robinhood (SnapTrade) · Plaid bank/cards · Splitwise API key — status + connect/disconnect |
| **Budget** | Set monthly total budget; configure envelope limits and categorization rules |
| **Risk posture** | Set Safe ↔ Risk target band for portfolio |
| **Notifications** | Enable push · Send test · toggles for purchase alerts, daily budget, weekly review, goal milestones, price alerts |
| **Chat** | Clear conversation history |
| **Account** | Change PIN · data source status (Live / Mock) |

---

### Notifications & Proactive Brain

Brain reaches out at the right moment — not only when you ask.

| Notification | When it fires | What it says |
|--------------|---------------|--------------|
| **Daily portfolio summary** | 12:00 PM Central | Portfolio value, P&L, holdings count |
| **Daily budget remaining** | 9:00 AM Central | Remaining budget for the period |
| **Purchase alert** | New card charge or Splitwise split | Amount + **envelope impact** + budget/category remaining |
| **Spending pace warning** | Mid-period | "On track to overshoot Dining by $120" |
| **Weekly financial review** | Sunday morning (LLM) | Budget, goals, portfolio, loans — one paragraph summary |
| **Goal milestone** | Progress threshold hit | "You're 50% to your house fund" |
| **Price alert** | ±X% on holding or watchlist | "AAPL down 5% — still 8% of portfolio" |
| **Investment drift** | Risk posture or concentration breach | "Tech is 18% over your Safe band" |

Tapping any notification opens the relevant tab (Spend, Invest, Goals, or Chat).

---

### Data & Integrations

| Source | What Brain reads | Used for |
|--------|------------------|----------|
| **SnapTrade / Robinhood** | US equity holdings, values, P&L | Invest tab, portfolio context, goal progress |
| **Plaid** | Bank + credit card transactions, account balances | Spend tab, envelopes, cash snapshot, affordability |
| **Splitwise** | Group expense shares, settlements | Spend tab, dedupe with card charges |
| **Manual India investments** | FD, mutual funds, stocks (INR) | Invest tab, merged portfolio with FX |
| **Goals (NL + LLM)** | Structured life goals | Goals tab, Chat, allocation view |
| **Income (NL + LLM, PIN)** | Paycheck + allocation plan | Budget income view, planned vs actual |
| **Loans (NL + LLM)** | Liabilities, EMI, rates | Loans tab, affordability, payoff advice |
| **Envelopes & rules** | Category limits, Plaid → category mapping | Spend structure, drift, smart nudges |

All integrations are **read-only**. No broker passwords stored. Single-user, privacy-first.

---

### Intelligence Engine (Under the Hood)

Not visible directly, but powers Chat, notifications, and insight cards.

| Component | Role |
|-----------|------|
| **Financial context builder** | Assembles a fresh snapshot before every Chat message and weekly review |
| **Cross-domain math** | Goal progress, allocation gaps, affordability, loan impact, enjoy-life discretionary room |
| **LLM layer** | OpenAI for Chat (multi-turn), goal/income/loan extraction (JSON), weekly review prose |
| **Category rollups** | Merchant and Plaid category trends across billing periods — no raw txn dumps to LLM |
| **Context cache** | Smart refresh so Plaid isn't hit on every chat message |
| **Conversation memory** | Persisted thread; last N messages sent to LLM; older turns summarized |

---

### End-State User Journey

```
Morning  →  Push: "$1,240 budget left · Dining on pace · Portfolio +0.8%"
           Tap → Spend tab or ask Chat "anything I should watch today?"

Purchase →  Push: "Okay Uber!! · $890 left · Dining envelope 72% used"
           Brain knows it's discretionary and you're still within enjoy-life room

Weekly   →  Push: LLM review — spending, goals, portfolio, loans in one paragraph
           Tap → Chat to dig deeper: "Should I move $500 from fun to investments?"

Anytime  →  Chat: "Can I book a $600 flight without hurting the house goal?"
           Brain cites envelopes, cash, loan EMI, goal timeline — specific answer
```

---

### What Success Looks Like

When the roadmap is complete, Brain is not four separate tabs — it is **one financial brain**:

- **Invest** answers "are my assets working toward my goals?"
- **Budget** answers "am I enjoying life without drifting off plan?"
- **Goals** answers "where am I going and am I on track?"
- **Loans** answers "what do I owe and what's the smartest payoff order?"
- **Chat** ties all of it together into decisions you can act on today

Simple on the surface. Complete underneath.

---

*Last updated: July 2026*
