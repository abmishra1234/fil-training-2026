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


def fee_for(order: Order) -> float:
    if order.type in FLAT_FEES:
        fee = FLAT_FEES[order.type]
    else:
        fee = order.notional * FEE_RATES.get(order.type, 0.0)
    return max(fee, MIN_FEE)


def process(orders: list[Order]) -> str:
    t = 0
    out = []
    for o in orders:
        f = fee_for(o)
        t = t + o.notional + f
        out.append(o.id + "," + str(round(f, 2)))
    out.append("TOTAL," + str(round(t, 2)))
    return "\n".join(out)
