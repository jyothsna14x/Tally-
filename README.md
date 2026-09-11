# tally cli

A portfolio tracker in one file. The database is `data/transactions.txt` —
one trade per line:

```
stock,side,qty,price
wipro,BUY,40,220.0
wipro,SELL,10,230.0
```

```bash
python main.py
```

**Menu** — view transactions · add transaction · view portfolio · performance
stats · exit.

## How it works

Every view replays the ledger chronologically through one function,
`compute_portfolio()`. The math is the **average cost method**:

- **BUY** — quantity and cost basis grow by `q · price`; average = `basis / qty`
- **SELL** — profit `(price − avg) · q` is *realized*; basis shrinks by `q · avg`
  (what the shares **cost**, never what they sold for); cash increases by `q · price`

The original version subtracted sale *proceeds* from the basis — one line that
silently corrupted every average after a profitable trade. See the root README
for the full before/after.

## Edge cases

- Selling more than you hold → skipped, counted, surfaced as a warning
- Corrupt ledger lines → ignored, never a crash
- Bad input → re-prompts until sane
