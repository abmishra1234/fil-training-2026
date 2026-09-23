FEE_RATES = {"EQ": 0.0025, "FI": 0.0010}
FLAT_FEES = {"FX": 5.0}
MIN_FEE = 1  # int on purpose: legacy output prints "1", not "1.0"


def process(orders):
    t = 0
    out = []
    for o in orders:
        if o["type"] == "EQ":
            f = o["qty"] * o["px"] * FEE_RATES["EQ"]
        elif o["type"] == "FI":
            f = o["qty"] * o["px"] * FEE_RATES["FI"]
        elif o["type"] == "FX":
            f = FLAT_FEES["FX"]
        else:
            f = 0
        if f < MIN_FEE:
            f = MIN_FEE
        t = t + o["qty"] * o["px"] + f
        out.append(o["id"] + "," + str(round(f, 2)))
    out.append("TOTAL," + str(round(t, 2)))
    return "\n".join(out)
