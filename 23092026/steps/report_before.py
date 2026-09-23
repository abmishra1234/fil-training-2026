def process(orders):
    t = 0
    out = []
    for o in orders:
        if o["type"] == "EQ":
            f = o["qty"] * o["px"] * 0.0025
        elif o["type"] == "FI":
            f = o["qty"] * o["px"] * 0.0010
        elif o["type"] == "FX":
            f = 5.0
        else:
            f = 0
        if f < 1:
            f = 1
        t = t + o["qty"] * o["px"] + f
        out.append(o["id"] + "," + str(round(f, 2)))
    out.append("TOTAL," + str(round(t, 2)))
    return "\n".join(out)
