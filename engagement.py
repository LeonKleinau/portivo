from datetime import date


MARKET_RATE_PCT = 3.8


def _months_between(start, end):
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return months


def prolongation_alert(loan, market_rate_pct=MARKET_RATE_PCT, today=None):
    if not loan:
        return None
    today = today or date.today()
    zb_end = date.fromisoformat(loan["zinsbindung_end"])
    days_left = (zb_end - today).days

    if days_left < 0:
        severity = "urgent"
        title = "Zinsbindung abgelaufen — Anschlussfinanzierung überfällig"
        months_left = _months_between(zb_end, today)
    else:
        months_left = _months_between(today, zb_end)
        if months_left <= 6:
            severity = "urgent"
            title = f"Anschlussfinanzierung in {months_left} Monaten fällig"
        elif months_left <= 12:
            severity = "warning"
            title = f"Anschlussfinanzierung in {months_left} Monaten"
        elif months_left <= 18:
            severity = "info"
            title = f"Anschlussfinanzierung in {months_left} Monaten"
        else:
            return None

    delta = market_rate_pct - loan["zinssatz_pct"]
    sign = "+" if delta >= 0 else "−"
    detail = (
        f"Aktueller Zinssatz: {loan['zinssatz_pct']:.2f} %. "
        f"Marktzins heute: {market_rate_pct:.2f} %. "
        f"Differenz: {sign}{abs(delta):.2f} %-Punkte."
    ).replace(".", ",")

    return {
        "id": "prolongation",
        "title": title,
        "severity": severity,
        "months_left": months_left,
        "current_rate_pct": loan["zinssatz_pct"],
        "market_rate_pct": market_rate_pct,
        "delta_pct": delta,
        "detail": detail,
    }


def geg_alerts(prop, today=None):
    alerts = []
    today = today or date.today()

    ea_date_str = prop.get("energieausweis_date")
    if ea_date_str:
        ea_issue = date.fromisoformat(ea_date_str)
        ea_expiry = date(ea_issue.year + 10, ea_issue.month, ea_issue.day)
        days_to_expiry = (ea_expiry - today).days
        if days_to_expiry < 0:
            alerts.append(
                {
                    "id": "energieausweis_expired",
                    "title": "Energieausweis abgelaufen",
                    "severity": "urgent",
                    "detail": (
                        f"Ablaufdatum: {ea_expiry.strftime('%d.%m.%Y')}. "
                        f"Erneuerung gesetzlich erforderlich vor Neuvermietung oder Verkauf."
                    ),
                }
            )
        else:
            months_to_expiry = _months_between(today, ea_expiry)
            if months_to_expiry <= 18:
                alerts.append(
                    {
                        "id": "energieausweis_expiring",
                        "title": f"Energieausweis läuft in {months_to_expiry} Monaten ab",
                        "severity": "warning",
                        "detail": (
                            f"Ablaufdatum: {ea_expiry.strftime('%d.%m.%Y')}. "
                            f"Frühzeitig erneuern lassen, um Lücken bei Vermietung zu vermeiden."
                        ),
                    }
                )

    heizungsart = (prop.get("heizungsart") or "").lower()
    install_year = prop.get("heizung_installation_year")
    fossil = any(keyword in heizungsart for keyword in ["gas", "öl", "oel"])
    if install_year and fossil and install_year < 2024:
        alerts.append(
            {
                "id": "geg_heating",
                "title": "GEG-relevante Heizung",
                "severity": "info",
                "detail": (
                    f"{prop['heizungsart']} (Einbau {install_year}). "
                    f"Bei Defekt oder regulärem Austausch ist seit 2024 eine Heizung mit "
                    f"≥ 65 % erneuerbarer Energie vorgeschrieben. Spätestens 2045 ist die "
                    f"vollständige Umstellung verpflichtend."
                ),
            }
        )

    return alerts


def mietspiegel_alert(prop):
    mietspiegel = prop.get("mietspiegel_eur_per_sqm")
    wohnflaeche = prop.get("wohnflaeche_sqm", 0)
    if not mietspiegel or wohnflaeche <= 0:
        return None
    current_per_sqm = prop["kaltmiete_monthly"] / wohnflaeche
    gap_eur = mietspiegel - current_per_sqm
    gap_pct = (gap_eur / mietspiegel) * 100
    if gap_pct < 5:
        return None
    monthly_uplift = gap_eur * wohnflaeche
    detail = (
        f"Aktuelle Kaltmiete: {current_per_sqm:.2f} €/m². "
        f"Mietspiegel: {mietspiegel:.2f} €/m². "
        f"Lücke: {gap_pct:.1f} %, Potenzial ≈ {monthly_uplift:.0f} € pro Monat. "
        f"Mieterhöhung im Rahmen von Kappungsgrenze und Mietpreisbremse prüfen."
    ).replace(".", ",")
    return {
        "id": "mietspiegel",
        "title": "Mieterhöhungspotenzial",
        "severity": "info",
        "current_per_sqm": current_per_sqm,
        "mietspiegel_per_sqm": mietspiegel,
        "gap_pct": gap_pct,
        "monthly_uplift_potential": monthly_uplift,
        "detail": detail,
    }


def spekulationsfrist_alert(prop, today=None):
    if not prop.get("purchase_date"):
        return None
    today = today or date.today()
    purchase = date.fromisoformat(prop["purchase_date"])
    spek_end = date(purchase.year + 10, purchase.month, purchase.day)
    days_diff = (spek_end - today).days

    if days_diff < -365:
        return None

    if days_diff < 0:
        return {
            "id": "spekulationsfrist_open",
            "title": "Spekulationsfrist abgelaufen — steuerfreier Verkauf möglich",
            "severity": "info",
            "detail": (
                f"10-Jahres-Frist erreicht am {spek_end.strftime('%d.%m.%Y')}. "
                f"Bei Vermietungsobjekten ist ein Verkauf seitdem ohne "
                f"Veräußerungsgewinnbesteuerung möglich. Verkaufsstrategie prüfen, falls relevant."
            ),
        }

    months_left = _months_between(today, spek_end)
    if months_left > 24:
        return None

    if months_left <= 6:
        severity = "warning"
        title_suffix = "Verkaufsstrategie prüfen"
    elif months_left <= 12:
        severity = "info"
        title_suffix = "steuerfreier Verkauf bald möglich"
    else:
        severity = "info"
        title_suffix = "Vorbereitung auf Verkaufsmöglichkeit"

    return {
        "id": "spekulationsfrist",
        "title": f"Spekulationsfrist in {months_left} Monaten — {title_suffix}",
        "severity": severity,
        "months_left": months_left,
        "detail": (
            f"10-Jahres-Frist endet am {spek_end.strftime('%d.%m.%Y')}. "
            f"Danach ist ein Verkauf ohne Veräußerungsgewinnbesteuerung möglich "
            f"(bei Vermietung; bei Eigennutzung gelten andere Regeln)."
        ),
    }


def all_alerts(prop, loan, today=None):
    alerts = []
    pa = prolongation_alert(loan, today=today)
    if pa:
        alerts.append(pa)
    alerts.extend(geg_alerts(prop, today=today))
    ms = mietspiegel_alert(prop)
    if ms:
        alerts.append(ms)
    sa = spekulationsfrist_alert(prop, today=today)
    if sa:
        alerts.append(sa)
    severity_order = {"urgent": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 99))
    return alerts
