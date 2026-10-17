"""Risk/Reward Support/Resistance Zone — LONG ONLY (IDX tidak bisa short).

Semua kandidat skenario dikembalikan, baik yang lolos filter maupun gugur.
Field "lolos" + "alasan_gugur" menandai status masing-masing.

Aturan entry harus DEKAT dengan harga saat ini:
  - BUY at Support : harga tidak boleh > 5% dari zona support
  - BREAKOUT BUY   : trigger breakout tidak boleh > 5% dari harga saat ini
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.supres import get_support_resistance

DEFAULT_MODAL          = 10_000_000
DEFAULT_RISK_PER_TRADE = 0.01
DEFAULT_ATR_BUFFER     = 0.5
DEFAULT_MIN_RR         = 1.5
DEFAULT_MAX_JARAK_ATR  = 1.0
DEFAULT_MAX_JARAK_PCT  = 5.0    # max 5% jarak harga → entry (untuk both setup)
DEFAULT_FEE_BUY        = 0.0015
DEFAULT_FEE_SELL       = 0.0025


def _round_tick(price):
    if price < 200:
        return round(price)
    elif price < 500:
        return round(price / 2) * 2
    elif price < 2000:
        return round(price / 5) * 5
    elif price < 5000:
        return round(price / 10) * 10
    else:
        return round(price / 25) * 25


def _net_rr_long(entry, sl, tp, fee_buy, fee_sell):
    buy_cost    = entry * (1 + fee_buy)
    sl_proceeds = sl    * (1 - fee_sell)
    tp_proceeds = tp    * (1 - fee_sell)
    net_risk    = buy_cost - sl_proceeds
    net_reward  = tp_proceeds - buy_cost
    if net_risk <= 0:
        return 0.0
    return net_reward / net_risk


def _lot_from_risk(entry, sl, modal, risk_pct, fee_buy, fee_sell):
    risk_per_share = entry * (1 + fee_buy) - sl * (1 - fee_sell)
    if risk_per_share <= 0:
        return 0
    return max(int((modal * risk_pct) / (risk_per_share * 100)), 1)


def _build(tipe, deskripsi, entry_mid, entry_confirm, entry_avg,
           sl, tp1, tp2, zone_entry, target1, target2,
           confirm_needed, current, modal, risk_per_trade,
           fee_buy, fee_sell):
    rr1 = _net_rr_long(entry_avg, sl, tp1, fee_buy, fee_sell) if tp1 else 0.0
    rr2 = _net_rr_long(entry_avg, sl, tp2, fee_buy, fee_sell) if tp2 else 0.0

    lot = _lot_from_risk(entry_avg, sl, modal, risk_per_trade, fee_buy, fee_sell)

    return {
        "tipe": tipe,
        "deskripsi": deskripsi,
        "zona_entry": (zone_entry[0], zone_entry[1]),
        "entry_mid": entry_mid,
        "entry_confirm": entry_confirm,
        "entry": entry_avg,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "rr": round(rr1, 2),
        "rr_tp1": round(rr1, 2),
        "rr_tp2": round(rr2, 2) if rr2 > 0 else None,
        "risk_per_share": abs(entry_avg - sl),
        "risk_pct": round(abs(entry_avg - sl) / entry_avg * 100, 2),
        "lot": lot,
        "target1": target1,
        "target2": target2,
        "direction": "long",
        "confirm_needed": confirm_needed,
        "jarak_entry_pct": round((entry_avg - current) / current * 100, 2),
        "lolos": False,
        "alasan_gugur": None,
    }


def hitung_rr_skenario(kode, timeframe="daily",
                       modal=DEFAULT_MODAL,
                       risk_per_trade=DEFAULT_RISK_PER_TRADE,
                       atr_buffer=DEFAULT_ATR_BUFFER,
                       min_rr=DEFAULT_MIN_RR,
                       max_jarak_atr=DEFAULT_MAX_JARAK_ATR,
                       max_jarak_pct=DEFAULT_MAX_JARAK_PCT,
                       fee_buy=DEFAULT_FEE_BUY,
                       fee_sell=DEFAULT_FEE_SELL):
    sr = get_support_resistance(kode, timeframe=timeframe)
    if not sr:
        return None

    current     = sr["current_price"]
    atr         = sr["atr"]
    supports    = sr["supports"]
    resistances = sr["resistances"]

    scenarios = []

    # ========================================================
    # 1) BUY at Support
    # ========================================================
    if supports:
        s = supports[0]
        z_lo, z_hi = s["lower"], s["upper"]
        entry_mid     = _round_tick((z_lo + z_hi) / 2)
        entry_confirm = _round_tick(z_hi)
        entry_avg     = _round_tick((entry_mid + entry_confirm) / 2)
        sl            = _round_tick(z_lo - atr_buffer * atr)

        res_above = [x for x in resistances
                     if _round_tick(x["lower"]) > entry_avg]
        t1 = res_above[0] if len(res_above) >= 1 else None
        t2 = res_above[1] if len(res_above) >= 2 else None
        tp1 = _round_tick(t1["lower"]) if t1 else None
        tp2 = _round_tick(t2["lower"]) if t2 else None

        sc = _build(
            tipe="BUY at Support",
            deskripsi=(f"Buy limit zona {z_lo:,.0f}–{z_hi:,.0f} "
                       f"(50% mid {entry_mid:,.0f}, "
                       f"50% konfirmasi close > {z_hi:,.0f})"),
            entry_mid=entry_mid, entry_confirm=entry_confirm,
            entry_avg=entry_avg, sl=sl, tp1=tp1, tp2=tp2,
            zone_entry=(z_lo, z_hi), target1=t1, target2=t2,
            confirm_needed=False,
            current=current, modal=modal, risk_per_trade=risk_per_trade,
            fee_buy=fee_buy, fee_sell=fee_sell,
        )

        # Jarak harga saat ini ke entry
        jarak_pct = abs(current - entry_avg) / current * 100

        # Tentukan status
        if current < z_lo:
            sc["alasan_gugur"] = (
                f"support sudah tembus — harga {current:,.0f} di bawah zona {z_lo:,.0f}"
            )
        elif current > z_hi + max_jarak_atr * atr:
            sc["alasan_gugur"] = (
                f"harga terlalu jauh di atas zona "
                f"(>{max_jarak_atr:.1f}×ATR dari batas atas)"
            )
        elif jarak_pct > max_jarak_pct:
            sc["alasan_gugur"] = (
                f"harga {current:,.0f} terlalu jauh dari zona support "
                f"{z_lo:,.0f}–{z_hi:,.0f} ({jarak_pct:.1f}% > {max_jarak_pct:.1f}%)"
            )
        elif tp1 is None:
            sc["alasan_gugur"] = "tidak ada resistance di atas entry untuk TP"
        elif sc["rr_tp1"] < min_rr:
            sc["alasan_gugur"] = (
                f"RR TP1 {sc['rr_tp1']:.2f} < {min_rr} "
                f"(reward terlalu tipis setelah fee)"
            )
        else:
            sc["lolos"] = True

        scenarios.append(sc)

    # ========================================================
    # 2) BREAKOUT BUY
    # ========================================================
    if resistances:
        r = resistances[0]
        z_lo, z_hi = r["lower"], r["upper"]
        entry_trigger = _round_tick(z_hi + atr_buffer * atr)
        sl            = _round_tick(z_lo - atr_buffer * atr)
        entry_avg     = entry_trigger

        res_after = [x for x in resistances[1:]
                     if _round_tick(x["lower"]) > entry_avg]
        t1 = res_after[0] if len(res_after) >= 1 else None
        t2 = res_after[1] if len(res_after) >= 2 else None
        tp1 = _round_tick(t1["lower"]) if t1 else None
        tp2 = _round_tick(t2["lower"]) if t2 else None

        sc = _build(
            tipe="BREAKOUT BUY",
            deskripsi=(f"Buy stop jika close > {z_hi:,.0f} "
                       f"(trigger {entry_trigger:,.0f})"),
            entry_mid=entry_trigger, entry_confirm=entry_trigger,
            entry_avg=entry_avg, sl=sl, tp1=tp1, tp2=tp2,
            zone_entry=(z_lo, z_hi), target1=t1, target2=t2,
            confirm_needed=True,
            current=current, modal=modal, risk_per_trade=risk_per_trade,
            fee_buy=fee_buy, fee_sell=fee_sell,
        )

        # Jarak harga saat ini ke trigger breakout
        jarak_pct = (entry_trigger - current) / current * 100

        if current >= entry_trigger:
            sc["alasan_gugur"] = (
                f"harga sudah breakout — {current:,.0f} ≥ trigger "
                f"{entry_trigger:,.0f} (setup sudah terlewat)"
            )
        elif jarak_pct > max_jarak_pct:
            sc["alasan_gugur"] = (
                f"resistance masih terlalu jauh — trigger {entry_trigger:,.0f} "
                f"butuh naik {jarak_pct:.1f}% dari harga {current:,.0f} "
                f"(> {max_jarak_pct:.1f}%)"
            )
        elif tp1 is None:
            sc["alasan_gugur"] = "tidak ada resistance lanjutan untuk TP"
        elif sc["rr_tp1"] < min_rr:
            sc["alasan_gugur"] = (
                f"RR TP1 {sc['rr_tp1']:.2f} < {min_rr} "
                f"(resistance berikutnya terlalu dekat)"
            )
        else:
            sc["lolos"] = True

        scenarios.append(sc)

    if not scenarios:
        return None

    # Urutkan: yang lolos dulu (RR desc), lalu yang gugur (RR desc)
    scenarios = sorted(
        scenarios,
        key=lambda x: (0 if x["lolos"] else 1, -x["rr"]),
    )

    n_lolos = sum(1 for x in scenarios if x["lolos"])

    return {
        "kode": kode,
        "current_price": current,
        "atr": atr,
        "n_supports": len(supports),
        "n_resistances": len(resistances),
        "scenarios": scenarios,
        "n_lolos": n_lolos,
        "n_gugur": len(scenarios) - n_lolos,
    }