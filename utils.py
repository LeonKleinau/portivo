def euro(amount, decimals=0):
    s = f"{amount:,.{decimals}f}"
    return "€ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def percent(value, decimals=2):
    return f"{value:.{decimals}f} %".replace(".", ",")


def german_date(iso):
    y, m, d = iso.split("-")
    return f"{d}.{m}.{y}"
