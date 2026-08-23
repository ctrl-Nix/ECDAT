# Frontend Track — Karan & Satyam

Owns: the dashboard everyone will actually look at — findings table, CBOM viewer, risk chart.

## How to run this

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`. You should see three tabs: Findings, CBOM Export, Risk Chart — all showing mock data.

## What's already done for you

- Vite + React scaffold, ready to run
- `src/mockData.js` — the shared mock data shape both of you build against (this is the Day 1 "agree the mock shape" step, already done — extend it if you need more fields)
- Three working screen stubs: `FindingsTable.jsx`, `CBOMViewer.jsx`, `RiskChart.jsx`
- `FindingsTable.jsx` already has a basic severity filter wired up — Day 3's task is to make this richer (add a file-name filter too)
- `RiskChart.jsx` uses plain divs, no chart library installed yet — swap it for Chart.js or Recharts whenever you're ready

## Suggested split with Satyam

- **Satyam** — owns `FindingsTable.jsx` and `CBOMViewer.jsx`
- **Karan** — owns `RiskChart.jsx` and the overall shell (`App.jsx`)

## Day 1 checklist

- [ ] Node LTS installed, `npm -v` works
- [ ] `npm install` succeeds with no errors
- [ ] `npm run dev` opens the app and all three tabs render
- [ ] Sketch/confirm the three screens match what the team agreed

## Day 2 checklist

- [ ] All three screens show mock data clearly (not blank, not crashing)
- [ ] Confirmed with Satyam who owns which component going forward
- [ ] Pushed this to the repo under `/frontend`

## Day 3 checklist (for reference — not today)

- [ ] Extend the severity filter, add a file-name filter
- [ ] This becomes the screen judges click around in most — make it feel responsive
