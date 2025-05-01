# RSU Calculator
Utility for calculating Swedish gains tax from E*Trade Restricted Stock Units.

## Disclaimer
The author is not an accreditad accountant and does not guarantee that this
works correctly nor follows Swedish taxation laws. Use at your own risk and
always double-check the results.

### Techical disclaimer
This uses floating point arithmetic which is generally a no-go in financial
applications. It should be using fixed point but given time constraints this
will have to do. Also, sorry about how the API rate limiting is implemented.

## How to use
1.  Download the Benefit History or fill in the provided ODS file with data
    from E*Trade
2.  Save the sheet as a CSV file, not as shown
3.  Run `python3 rsucal.py <time of sale> <share value at sale> <date of transfer> <filename>`

The tool will output a `<filename>.out.csv` with verification information and
print the total aquisition  value, total sales value and taxable amount in SEK
and gains tax in SEK.

### Where to find Benefit History
1.   Click the "At Work" top menu item
2.   Under the "My Account" sub top menu, click "Benefit History"
3.   Click the "Download" button and select "Download Expanded"

## Assumptions
This tool assumes shares have been sold to cover Swedish benefit taxations at
the time the shares vested and that all shares were sold at the same time.

## How it works
This is based on the information available from [Skatteverket]
(https://www4.skatteverket.se/rattsligvagledning/edition/2025.2/2818.html)

1.  The aquisition value for shares is converted to SEK with the exchange
    rate of the vesting date.
2.  The sale value for the shares is converted to SEK with the exchange rate
    of the transfer date if the transfer date is within 30 days of the sale
    date. The difference between aquisition and sale value is added to to taxable amount.
3.  If the transfer date is above 30 days after the sale date, the difference
    between the sale USD value converted to SEK at time of sale and the sale
    USD value at time of transfer is converted to SEK and added as a separate
    taxable amount.
