import argparse
import datetime
import csv
import json

from time import sleep
from urllib import request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("date_of_sale")
    parser.add_argument("price_at_sale")
    parser.add_argument("date_of_transfer")
    parser.add_argument("filename")

    args = parser.parse_args()

    with open(args.filename) as f:
        reader = csv.DictReader(f)
        data = list(reader)

    if "Record Type" in data[0]:
        data = convert_to_internal(data)

    data = format_rows(data)

    needed_rates = set(row["Vest date"] for row in data)
    needed_rates.add(args.date_of_sale)
    needed_rates.add(args.date_of_transfer)

    exchange_rates = get_exchange_rates(needed_rates)
    data = calculate_derived_fields(data)
    data = calculate_sek_fields(data, exchange_rates)

    print_tax(data, exchange_rates, args.date_of_sale, args.price_at_sale, args.date_of_transfer)

    write_outfile(args.filename.removesuffix(".csv") + ".out.csv", data)


def convert_to_internal(data):
    intermediate = dict()
    for row in data:
        if row["Record Type"] == "Vest Schedule":
            update = {
                "Vest date": datetime.datetime.strptime(row["Vest Date"], "%m/%d/%Y").date().isoformat(),
                "Vested Qty.": row["Vested Qty."],
                "Withholding amount": row["Total Taxes Paid"],
            }
        elif row["Record Type"] == "Tax Withholding":
            update = {
                "Taxable gain": row["Taxable Gain"]
            }
        else:
            continue

        if row_id(row) not in intermediate:
            intermediate[row_id(row)] = update
        else:
            intermediate[row_id(row)].update(update)

    out = []
    for key, row in intermediate.items():
        if row["Vested Qty."] == "0":
            continue

        row["Shares traded for taxes"] = int(int(row["Vested Qty."]) * float(row["Withholding amount"]) / float(row["Taxable gain"]) )
        out.append(row)

    return out


def row_id(row):
    return f"{row['Grant Number']}-{row['Vest Period']}"


def format_rows(data):
    for row in data:
        row["Vested Qty."] = int(row["Vested Qty."])
        row["Taxable gain"] = float(row["Taxable gain"])
        row["Withholding amount"] = float(row["Withholding amount"])
        row["Shares traded for taxes"] = int(row["Shares traded for taxes"])

    return data


def get_exchange_rates(dates):
    out = dict()

    try:
        with open("exchange_rates.json") as f:
            rates = json.load(f)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        rates = dict()

    try:
        for date in dates:
            if date not in rates:
                rates[date] = get_exchange_rate(date)
                sleep(60.0/5) # Rate limit to 5 reqs/min

            out[date] = rates[date]
    finally:
        with open("exchange_rates.json", "w") as f:
            json.dump(rates, f)

    return out


def get_exchange_rate(date):
    start = str(datetime.date.fromisoformat(date) - datetime.timedelta(days=3))

    print(f"Fetching exchange rates for {start} to {date}")
    with request.urlopen(f"https://api.riksbank.se/swea/v1/Observations/SEKUSDPMI/{start}/{date}/") as f:
        response = json.load(f)

    if response[-1]["date"] != date:
        print(f"WARNING: Using exchange rate from {response[-1]['date']} for {date}")

    return response[-1]["value"]


def calculate_derived_fields(data):
    for row in data:
        row["Share value"] = row["Taxable gain"] / row["Vested Qty."]
        row["Shares received"] = row["Vested Qty."] - row["Shares traded for taxes"]
        row["Tax rate"] = row["Withholding amount"] / row["Taxable gain"] * 100
        row["Company due"] = row["Shares traded for taxes"] * row["Share value"] - row["Withholding amount"]

    return data


def calculate_sek_fields(data, exchange_rates):
    for row in data:
        row["Exchange rate (SEK/USD)"] = exchange_rates[row["Vest date"]]
        row["Acquisition value (SEK)"] = row["Shares received"] * row["Share value"] * row["Exchange rate (SEK/USD)"]

    return data

def print_tax(data, exchange_rates, date_of_sale, price_at_sale, date_of_transfer):
    shares = 0
    acc_acq_value = 0
    for row in data:
        shares += row["Shares received"]
        acc_acq_value += row["Acquisition value (SEK)"]

    if datetime.date.fromisoformat(date_of_transfer) - datetime.date.fromisoformat(date_of_sale) < datetime.timedelta(days=30):
        print("Applying 30 day rule")
        close_value = shares * float(price_at_sale) * exchange_rates[date_of_transfer]
        print(f"Acquisition value: {acc_acq_value}kr")
        print(f"Closing value: {close_value}kr")
        print(f"Taxable gains: {close_value - acc_acq_value}kr")
    else:
        close_value = shares * float(price_at_sale) * exchange_rates[date_of_sale]
        print(f"Acquisition value (holdings): {acc_acq_value}kr")
        print(f"Closing value (holdings): {close_value}kr")
        print(f"Taxable gains (holdings): {close_value - acc_acq_value}kr")

        transfer_value = shares * float(price_at_sale) * exchange_rates[date_of_transfer]
        print(f"Acquisition value (currency): {close_value}kr")
        print(f"Closing value (currency): {transfer_value}kr")
        print(f"Taxable gains (currency): {transfer_value - close_value}kr")


def write_outfile(filename, data):
    fields = ["Vest date", "Vested Qty.", "Taxable gain", "Withholding amount", "Shares traded for taxes", "Share value", "Shares received", "Tax rate", "Company due", "Exchange rate (SEK/USD)", "Acquisition value (SEK)"]
    with open(filename, "w") as f:
        writer = csv.DictWriter(f, fields)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


if __name__ == "__main__":
    main()