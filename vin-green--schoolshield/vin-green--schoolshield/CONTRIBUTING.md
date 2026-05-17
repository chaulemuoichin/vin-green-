# Contributing — Hackathon Team Guide

Quick orientation for teammates jumping into the SchoolShield codebase.

---

## Getting oriented

Read these first:
1. [`README.md`](README.md) — project overview, setup, run commands
2. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — how the pieces fit together
3. [`docs/API.md`](docs/API.md) — the backend contract the frontend depends on

---

## Branch workflow

We work on the `schoolshield` branch. Keep it simple for the hackathon:

```bash
git checkout schoolshield
git pull                         # sync before starting work
# ... make changes ...
git add <files>
git commit -m "short description of what you changed"
git push
```

If two people edit the same file at the same time, resolve conflicts by reading both versions carefully — don't just accept one side blindly.

---

## Where to make common changes

| What you want to change | File |
|---|---|
| School name, location text | `frontend/src/pages/Dashboard.jsx` |
| Parent view content | `frontend/src/pages/ParentView.jsx` |
| Health tips per risk level | `frontend/src/pages/ParentView.jsx` → `HEALTH` object |
| Alert messages (seeded) | `backend/routers/alerts.py` → `_store` list |
| PM2.5 peak times / heights | `backend/simulator.py` |
| Polling frequency | `frontend/src/hooks/useAQI.js` → `setInterval` |
| Global colours / fonts | `frontend/src/index.css` |
| Risk thresholds | `backend/simulator.py` → `risk_level()` |
| Chart data / forecast | `frontend/src/components/TrendChart.jsx` |

---

## Code conventions

**Vietnamese UI text** — all user-facing strings stay in Vietnamese. Don't translate to English for convenience.

**Inline styles** — this project uses `style={{}}` objects for component-level styling, not Tailwind. Tailwind is used for layout utilities (`flex`, `gap-4`, `p-6`, `grid`, `mb-4`, etc.) on the outer containers. Match whichever pattern is already on the element you're editing.

**No new dependencies without discussion** — the bundle is intentionally lean. If you want to add a library, check with the team first.

**No TypeScript** — plain `.jsx` and `.js` only.

**Component files** — one component per file, named to match the export. Put new UI building blocks in `frontend/src/components/`, new pages in `frontend/src/pages/`.

---

## Forcing specific states for development

**Always CAO (high risk) — fastest way to test high-risk UI:**
```python
# backend/simulator.py — top of current_pm25()
def current_pm25() -> float:
    return 90.0   # ← add this, remove when done
```
Restart backend after saving.

**Specific time-of-day simulation:**
The simulator uses real system time. To test morning peak (07:30), you can temporarily override the hour:
```python
def current_pm25() -> float:
    hour = 7.5   # ← force 07:30 simulation
    base = _base_pm25(hour)
    ...
```

**Add a test alert:**
Append to `_store` in `backend/routers/alerts.py`:
```python
{
    "id": "test1",
    "message": "Thử nghiệm cảnh báo mới",
    "level": "high",
    "created_at": datetime.now().isoformat(),
    "dismissed": False,
}
```

---

## Before you push

- [ ] Backend still starts without errors (`uvicorn main:app --reload --port 8000`)
- [ ] Frontend still compiles (`npm run dev` in `frontend/`)
- [ ] Any hardcoded test values (like `return 90.0`) are removed
- [ ] Vietnamese text is correct (run it past a native speaker if unsure)
- [ ] No `console.log` or debug print statements left in

---

## Questions?

If something in the codebase is confusing, check `docs/ARCHITECTURE.md` first — the component tree and data flow are both documented there. If it's still unclear, ask in the group chat.
