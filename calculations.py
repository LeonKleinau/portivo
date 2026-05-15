def gross_yield(annual_rent, purchase_price):
    if purchase_price <= 0:
        return 0.0
    return (annual_rent / purchase_price) * 100


def net_yield(annual_rent, annual_opex, total_acquisition_cost):
    if total_acquisition_cost <= 0:
        return 0.0
    return ((annual_rent - annual_opex) / total_acquisition_cost) * 100
