# ================== TALLY — Financial Technology ==================
# A tiny stock portfolio tracker that reads a plain text ledger:
#   data/{username}/transactions.txt -> one trade per line
#
# THE CORE MATH (average cost method):
#   BUY  -> qty += q   |  total_cost += q * price
#           average_cost = total_cost / qty
#   SELL -> realized_pnl += (sell_price - average_cost) * q
#           total_cost -= q * average_cost   <-- FIX: cost basis, not proceeds!
#           qty -= q
#
# Why the fix matters: when you sell, the money leaving your position is
# what those shares *cost you*, not what you sold them for.

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_BASE = os.path.join(BASE_DIR, "data")

MONEY = "{:,.2f}"  # 1234.5 -> 1,234.50


def fmt(x):
    """Format a number as money, e.g. 1234.5 -> '1,234.50'."""
    return MONEY.format(x)


def ensure_user_folder(username):
    """Create user's data folder if it doesn't exist."""
    user_folder = os.path.join(DATA_BASE, username)
    os.makedirs(user_folder, exist_ok=True)
    return user_folder


def get_data_file(username):
    """Get the path to user's transaction file."""
    user_folder = ensure_user_folder(username)
    return os.path.join(user_folder, "transactions.txt")


# ------------------------------------------------------------------
# Username system
# ------------------------------------------------------------------

def get_username():
    """Ask user for their username at startup."""
    username = input("\n  Enter your username: ").strip()
    while not username:
        print("  ! Username can't be empty.")
        username = input("  Enter your username: ").strip()
    return username


# ------------------------------------------------------------------
# Input helpers — keep asking until the user types something valid
# ------------------------------------------------------------------

def ask_side():
    side = input("  BUY or SELL? ").strip().upper()
    while side not in ("BUY", "SELL"):
        print("  ! Please type BUY or SELL.")
        side = input("  BUY or SELL? ").strip().upper()
    return side


def ask_int(prompt):
    while True:
        try:
            value = int(input(f"  {prompt}"))
            if value > 0:
                return value
            print("  ! Quantity must be a positive whole number.")
        except ValueError:
            print("  ! Please enter a whole number (e.g. 10).")


def ask_float(prompt):
    while True:
        try:
            value = float(input(f"  {prompt}"))
            if value > 0:
                return value
            print("  ! Price must be a positive number.")
        except ValueError:
            print("  ! Please enter a number (e.g. 123.45).")


# ------------------------------------------------------------------
# Ledger I/O
# ------------------------------------------------------------------

def load_transactions(username):
    """Read the ledger, silently skipping corrupt lines."""
    data_file = get_data_file(username)
    if not os.path.exists(data_file):
        return []
    
    trades = []
    with open(data_file, "r") as file:
        for line in file:
            parts = line.strip().split(",")
            if len(parts) != 4:
                continue
            stock, side, qty, price = parts
            try:
                trades.append((stock.strip(), side.strip().upper(), int(qty), float(price)))
            except ValueError:
                continue
    return trades


def add_transaction(username):
    """Add a new transaction to the ledger."""
    stock = input("  Name of the stock: ").strip()
    while not stock:
        print("  ! Stock name can't be empty.")
        stock = input("  Name of the stock: ").strip()
    
    side = ask_side()
    qty = ask_int("Quantity of shares: ")
    price = ask_float("Price per share: ")

    data_file = get_data_file(username)
    with open(data_file, "a") as file:
        file.write(f"{stock},{side},{qty},{price}\n")

    print(f"\n  ✓ Logged: {side} {qty} x {stock} @ {fmt(price)}  (value: {fmt(qty * price)})")


# ------------------------------------------------------------------
# Portfolio engine — walks the ledger chronologically
# ------------------------------------------------------------------

def compute_portfolio(username):
    """Replay every trade in order and return the full state."""
    stocks = {}
    cash = 0.0
    realized = 0.0
    sales = []
    oversells = 0

    for stock_name, side, qty, price in load_transactions(username):
        if stock_name not in stocks:
            stocks[stock_name] = {"quantity": 0, "total_cost": 0.0,
                                  "average_cost": 0.0, "realized_pnl": 0.0}
        pos = stocks[stock_name]

        if side == "BUY":
            pos["quantity"] += qty
            pos["total_cost"] += qty * price
            cash -= qty * price
            if pos["quantity"] > 0:
                pos["average_cost"] = pos["total_cost"] / pos["quantity"]

        elif side == "SELL":
            if pos["quantity"] >= qty and pos["average_cost"] > 0:
                pnl = (price - pos["average_cost"]) * qty
                realized += pnl
                cash += qty * price
                pos["total_cost"] -= qty * pos["average_cost"]  # THE FIX
                pos["quantity"] -= qty
                pos["realized_pnl"] += pnl
                sales.append((stock_name, qty, price, pnl))
            else:
                oversells += 1

        if pos["quantity"] > 0:
            pos["average_cost"] = pos["total_cost"] / pos["quantity"]

    return {"stocks": stocks, "cash": cash, "realized": realized,
            "sales": sales, "oversells": oversells}


# ------------------------------------------------------------------
# Display functions with USERNAME
# ------------------------------------------------------------------

def view_transactions(username):
    """Display all transactions for this user."""
    trades = load_transactions(username)
    if not trades:
        print(f"\n  (no transactions yet)")
        return
    
    print(f"\n  ╔ {username.upper()}'S TRANSACTIONS ╗")
    print(f"  {'STOCK':<12}{'SIDE':<7}{'QTY':>6}{'PRICE':>12}{'VALUE':>14}")
    print("  " + "-" * 51)
    for stock, side, qty, price in trades:
        print(f"  {stock:<12}{side:<7}{qty:>6}{fmt(price):>12}{fmt(qty * price):>14}")
    print("  " + "-" * 51)
    print(f"  {len(trades)} transactions on record\n")


def view_portfolio(username):
    """Display portfolio with USERNAME."""
    book = compute_portfolio(username)
    stocks = book["stocks"]

    print(f"\n  ╔ {username.upper()}'S PORTFOLIO ╗")
    print(f"  {'STOCK':<12}{'QTY':>6}{'AVG COST':>12}{'COST BASIS':>14}{'REALIZED P/L':>15}")
    print("  " + "-" * 59)
    
    for name in sorted(stocks):
        pos = stocks[name]
        pnl = pos["realized_pnl"]
        pnl_str = f"{'+' if pnl >= 0 else '-'}{fmt(abs(pnl))}"
        print(f"  {name:<12}{pos['quantity']:>6}{fmt(pos['average_cost']):>12}"
              f"{fmt(pos['total_cost']):>14}{pnl_str:>15}")
    
    print("  " + "-" * 59)

    open_positions = {n: p for n, p in stocks.items() if p["quantity"] > 0}
    invested = sum(p["total_cost"] for p in open_positions.values())
    
    print(f"\n  💰 CASH BALANCE    : {fmt(book['cash'])}")
    print(f"  📈 STILL INVESTED  : {fmt(invested)}  ({len(open_positions)} open position(s))")
    print(f"  ✓ REALIZED P&L    : {fmt(book['realized'])}")
    
    if book["oversells"]:
        print(f"\n  ⚠ WARNING: {book['oversells']} invalid sell(s) were skipped")
    print()


def view_stats(username):
    """Display performance stats with USERNAME."""
    book = compute_portfolio(username)
    sales = book["sales"]

    total_buy_qty = 0
    total_buy_value = 0.0
    total_sell_qty = 0
    total_sell_value = 0.0
    
    for stock, side, qty, price in load_transactions(username):
        if side == "BUY":
            total_buy_qty += qty
            total_buy_value += qty * price
        else:
            total_sell_qty += qty
            total_sell_value += qty * price

    print(f"\n  ╔ {username.upper()}'S PERFORMANCE STATS ╗")
    print("  " + "-" * 44)
    print(f"  Trades logged      : {len(load_transactions(username))}")
    print(f"  Shares bought      : {total_buy_qty}  ({fmt(total_buy_value)})")
    print(f"  Shares sold        : {total_sell_qty}  ({fmt(total_sell_value)})")

    if total_buy_qty:
        print(f"  Avg buy price      : {fmt(total_buy_value / total_buy_qty)}")
    if total_sell_qty:
        print(f"  Avg sell price     : {fmt(total_sell_value / total_sell_qty)}")

    print(f"  Realized P&L       : {fmt(book['realized'])}")

    invested_in_solds = total_sell_value - book["realized"]
    if invested_in_solds > 0:
        roi = (book["realized"] / invested_in_solds) * 100
        print(f"  ROI on closed hits : {roi:+.2f}%")

    if sales:
        wins = [s for s in sales if s[3] > 0]
        win_rate = (len(wins) / len(sales)) * 100
        print(f"  Win rate           : {len(wins)}/{len(sales)} sells profitable  ({win_rate:.0f}%)")
        best = max(sales, key=lambda s: s[3])
        worst = min(sales, key=lambda s: s[3])
        print(f"  Best trade         : SOLD {best[1]} x {best[0]} @ {fmt(best[2])}  →  +{fmt(best[3])}")
        if worst[3] < 0:
            print(f"  Worst trade        : SOLD {worst[1]} x {worst[0]} @ {fmt(worst[2])}  →  -{fmt(abs(worst[3]))}")
        else:
            print("  Worst trade        : every sell closed green 🟢")
    else:
        print("  No completed sells yet - stats will appear after your first sale.")
    print()


# ------------------------------------------------------------------
# Menu loop
# ------------------------------------------------------------------

MENU = """
  ╔════════════════════════════════════╗
  ║  TALLY - What do you want to do?   ║
  ╠════════════════════════════════════╣
  ║  1. View transactions              ║
  ║  2. Add transaction                ║
  ║  3. View portfolio                 ║
  ║  4. View performance stats         ║
  ║  5. Change username                ║
  ║  6. Exit                           ║
  ╚════════════════════════════════════╝
"""


def main():
    username = get_username()
    print(f"\n  ✓ Welcome, {username}! 🎉\n")
    
    while True:
        print(MENU)
        choice = input("  Enter your choice (1-6): ").strip()
        
        if choice == "1":
            view_transactions(username)
        elif choice == "2":
            add_transaction(username)
        elif choice == "3":
            view_portfolio(username)
        elif choice == "4":
            view_stats(username)
        elif choice == "5":
            username = get_username()
            print(f"\n  ✓ Switched to {username}!\n")
        elif choice == "6":
            print(f"\n  Bye {username} - tally ho. 👋\n")
            break
        else:
            print("  ! Invalid choice, pick 1-6.\n")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Bye - tally ho. 👋\n")
