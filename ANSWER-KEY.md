# Answer key — Exercise 03

The correct extraction for each sample email, following the rules in `prompts/prompt-only.md` and `src/schema.py`. Under each one: the trap, what falling for it would look like, and whether `check` would notice.

`check` only catches an answer that contradicts itself. Most of these traps produce an answer that adds up and is still wrong, so only a comparison with the email catches them.

---

## 01-bookshop (the control)

```json
{"kind": "order", "merchant": "Marlowe & Finch Books", "order_id": "MF-20481",
 "order_date": "2026-10-05", "currency": "GBP",
 "items": [
   {"description": "The Overstory (paperback)", "quantity": 1, "unit_price": 10.99, "line_total": 10.99},
   {"description": "Field Notes, 3-pack", "quantity": 2, "unit_price": 9.50, "line_total": 19.00}],
 "discount": 0, "shipping": 3.95, "tax": 0, "total": 33.94}
```

No trap. If this one fails, look at the parsing, not the reading.

## 02-mercearia: VAT already included

```json
{"kind": "order", "merchant": "Mercearia do Bairro", "order_id": "7731",
 "order_date": "2026-10-10", "currency": "EUR",
 "items": [
   {"description": "Azeite virgem extra 750ml", "quantity": 2, "unit_price": 7.49, "line_total": 14.98},
   {"description": "Pão de centeio", "quantity": 1, "unit_price": 3.20, "line_total": 3.20},
   {"description": "Queijo da Serra (meio)", "quantity": 1, "unit_price": 18.90, "line_total": 18.90}],
 "discount": 0, "shipping": 4.50, "tax": 0, "total": 41.58}
```

"IVA incluído ... 2,10 €" means the VAT is already inside the prices, so `tax` is 0. The email is also in Portuguese, with comma decimals.

- **Wrong:** `tax: 2.10`, total 41.58. `check` **catches it**: the sum is off by 2.10.
- **Wrong:** `tax: 2.10`, total 43.68. `check` **misses it**: it adds up, but the email says 41.58.

## 03-forwarded: a correction replaces the original

```json
{"kind": "order", "merchant": "Kettle & Thread", "order_id": "KT-55902",
 "order_date": "2026-10-12", "currency": "EUR",
 "items": [
   {"description": "Stoneware mug, speckled", "quantity": 4, "unit_price": 12.00, "line_total": 48.00},
   {"description": "Tea towel set", "quantity": 1, "unit_price": 15.00, "line_total": 15.00}],
 "discount": 0, "shipping": 0, "tax": 0, "total": 63.00}
```

The linen apron was removed and refunded. The order was placed on 12 October. The 14th is the update and the 15th is the forward.

- **Wrong:** the original order, apron included, total 87.00. `check` **misses it**: the original adds up too.
- **Wrong:** `order_date` 2026-10-14 or 2026-10-15. `check` **misses it**.
- **Defensible:** keeping the apron with `kind: "order"` and listing the refund separately. The schema has no way to say "order with a partial refund", so this is a schema limit, not a reading error.

## 04-deskwerk: quote marks and a backslash

```json
{"kind": "order", "merchant": "Deskwerk", "order_id": "DW-1093-B",
 "order_date": "2026-10-19", "currency": "EUR",
 "items": [
   {"description": "Monitor arm 27\" (heavy-duty)", "quantity": 1, "unit_price": 89.00, "line_total": 89.00},
   {"description": "Cable tray \"Slim\", black", "quantity": 2, "unit_price": 14.50, "line_total": 29.00},
   {"description": "Desk mat 90x40cm \\ felt / grey", "quantity": 1, "unit_price": 22.00, "line_total": 22.00}],
 "discount": 14.00, "shipping": 6.90, "tax": 0, "total": 132.90}
```

The trap is at the parsing level. An unescaped `"` or `\` breaks `json.loads`, and `check` **catches it**. "Prices are per item", so the cable trays are 2 × 14.50.

- **Wrong:** a description with the quote marks dropped or mangled, such as `Monitor arm 27 (heavy-duty)`. `check` **misses it**.
- **Wrong:** `unit_price: 14.50, line_total: 14.50` for the trays. `check` **catches it**: 2 × 14.50 is not 14.50.
- **Wrong:** `discount: -14.00`. `check` **catches it**: the rule says positive.

## 05-trailhead: the date written the American way

```json
{"kind": "order", "merchant": "Trailhead Outfitters", "order_id": "TH-88214",
 "order_date": "2026-11-02", "currency": "USD",
 "items": [
   {"description": "Merino socks (3-pack)", "quantity": 2, "unit_price": null, "line_total": 38.00},
   {"description": "Headlamp 400lm", "quantity": 1, "unit_price": 29.99, "line_total": 29.99},
   {"description": "Water filter bottle", "quantity": 1, "unit_price": 34.50, "line_total": 34.50}],
 "discount": 0, "shipping": 0, "tax": 8.46, "total": 110.95}
```

11/02/2026 with EST and $ is 2 November. Here the sales tax really is added on top, unlike 02.

- **Wrong:** `order_date: 2026-02-11`. `check` **misses it**: it's a valid date.
- **Wrong:** `tax: 0`, total 110.95. `check` **catches it**.
- **Against the rule, not a trap:** socks `unit_price: 19.00`. The email doesn't state a unit price, and the rule says null. 19.00 is correct arithmetic but breaks the rule. `check` accepts both.
- **Ambiguous:** `order_id: "#TH-88214"`. That's "as written", but probably not what a system matching order numbers wants. Decide, then enforce it in `validate.py`.

## 06-refund: no order number

```json
{"kind": "refund", "merchant": "Lumen Audio", "order_id": null,
 "order_date": null, "currency": "GBP",
 "items": [
   {"description": "Lumen Over-Ear ANC headphones", "quantity": 1, "unit_price": 149.00, "line_total": 149.00}],
 "discount": 0, "shipping": 0, "tax": 0, "total": 149.00}
```

There's no order number and no order date. 23 October is when the refund was processed, not when the order was placed.

- **Wrong:** `kind: "order"`. `check` **misses it**.
- **Wrong:** an invented order number, or the card ending `4417` used as one. `check` **misses it**.
- **Wrong:** `order_date: 2026-10-23`. `check` **misses it**.
- **Wrong:** a negative total. `check` **catches it**: the rule says positive.
