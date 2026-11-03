Extract the order from the email below as JSON.

Use exactly these fields:

- kind: "order" or "refund"
- merchant: the shop's name
- order_id: the order number as written, or null if the email doesn't give one
- order_date: the date the order was placed, as YYYY-MM-DD, or null if unknown
- currency: the ISO 4217 code, such as EUR, GBP or USD
- items: a list of line items, each with description, quantity (a whole number), unit_price (the price of one unit, or null if the email doesn't state it) and line_total
- discount: the total discount, as a positive number, or 0
- shipping: the shipping charged, or 0
- tax: tax added on top of the item prices, or 0 if the prices already include it
- total: the amount charged or refunded, as a positive number

Return only the JSON.
