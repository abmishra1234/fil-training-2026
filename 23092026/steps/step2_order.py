from dataclasses import dataclass

FEE_RATES = {"EQ": 0.0025, "FI": 0.0010}
FLAT_FEES = {"FX": 5.0}
MIN_FEE = 1  # int on purpose: legacy output prints "1", not "1.0"


@dataclass(frozen=True)
class Order:
    id: str
    type: str
    qty: int
    px: float

    @property
    def notional(self) -> float:
        return self.qty * self.px


def process(orders: list[Order]) -> str:
    t = 0
    out = []
    for o in orders:
        if o.type == "EQ":
            f = o.notional * FEE_RATES["EQ"]
        elif o.type == "FI":
            f = o.notional * FEE_RATES["FI"]
        elif o.type == "FX":
            f = FLAT_FEES["FX"]
        else:
            f = 0
        if f < MIN_FEE:
            f = MIN_FEE
        t = t + o.notional + f
        out.append(o.id + "," + str(round(f, 2)))
    out.append("TOTAL," + str(round(t, 2)))
    return "\n".join(out)
