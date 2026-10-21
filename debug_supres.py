from quant.supres import _load_ohlcv, _atr, _find_swings, _impl
import traceback

print("=" * 60)
print("STEP 1: Load data BBCA")
print("=" * 60)
df = _load_ohlcv("BBCA")
print(f"  Type      : {type(df).__name__}")
print(f"  Is None   : {df is None}")
if df is not None:
    print(f"  Rows      : {len(df)}")
    print(f"  Columns   : {list(df.columns)}")
    print(f"  First date: {df['Date'].iloc[0]}")
    print(f"  Last date : {df['Date'].iloc[-1]}")
print()

print("=" * 60)
print("STEP 2: ATR")
print("=" * 60)
atr = _atr(df, 14) if df is not None else None
print(f"  ATR(14): {atr}")
print()

print("=" * 60)
print("STEP 3: Swings")
print("=" * 60)
if df is not None:
    lows, highs = _find_swings(df, window=5)
    print(f"  Swing lows : {len(lows)}")
    print(f"  Swing highs: {len(highs)}")
else:
    print("  SKIP (df is None)")
print()

print("=" * 60)
print("STEP 4: Current price")
print("=" * 60)
if df is not None and len(df) > 0:
    print(f"  Current: {float(df['Close'].iloc[-1])}")
else:
    print("  SKIP")
print()

print("=" * 60)
print("STEP 5: Full _impl() call")
print("=" * 60)
try:
    r = _impl("BBCA", "daily")
    print(f"  Result type : {type(r).__name__}")
    if r:
        print(f"  Supports    : {len(r.get('supports', []))}")
        print(f"  Resistances : {len(r.get('resistances', []))}")
    else:
        print("  r is None/False")
except Exception as e:
    print(f"  EXCEPTION: {type(e).__name__}: {e}")
    print()
    print("  Full traceback:")
    traceback.print_exc()
