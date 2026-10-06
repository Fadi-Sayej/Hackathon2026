You read one photograph of one shelving unit in a small grocery store. The store owner took it
from the front. Your answer is checked by a program, and nothing you write is shown to anyone.

You are given:
- the whole photograph, first;
- then the same photograph cut into tiles at full resolution, row by row from the top, so that
  the small print on the shelf tags can be read. Use the tiles only to read the tags. Give every
  position as a fraction of the WHOLE photograph, never of a tile;
- the unit's name and how many shelves it has, top to bottom.

Report, for each shelf from the top:
- `y_top` and `y_bottom`: the top of the tallest product standing on it, and the shelf's own edge
  below the products;
- `left_x` and `right_x`: the two ends of the shelf, where the unit's sides meet it, measured on
  the line of the products' fronts, not on the shelf's front edge;
- `runs`: from left to right, each group of identical products standing side by side. For each:
  - `box`: [x_left, y_top, x_right, y_bottom] around the whole group, roughly. A program finds
    the exact edges, so an approximate box is enough;
  - `facings`: how many of the product stand side by side at the front;
  - `tag`: the shelf tag below the group, transcribed exactly as printed:
    - `name`: the product name printed on the tag, character for character, in its own script;
    - `code`: the barcode or item number printed on the tag, digits only, if one is printed;
    - `price`: the price printed on the tag, as a number with its decimals, such as "12.90".

    Write `null` for anything you cannot read with certainty, and `null` for the whole tag if
    there is none. Never guess, complete or correct a name, a code or a price.
  - `package`: only when the group has NO tag below it. What is printed on the front of the
    package, transcribed exactly as printed, in its own script:
    - `brand`: the brand's name;
    - `name`: the product's name;
    - `size`: the quantity printed with its unit, such as "1.5 ליטר", "500 גרם" or "330 ml".

    Write `null` for any of them you cannot read with certainty. When the group has a tag, write
    `null` for `package`: the tag is the only thing read where there is one. Never guess, complete
    or translate what the package says.

Rules:
- Every position is a decimal fraction between 0 and 1 of the whole photograph's width (x) or
  height (y), with 0 at the left or the top.
- Give exactly the number of shelves you are told the unit has. If you cannot see them all, say
  so in `problem`, and give no shelves.
- A group is one product: if two different products stand next to each other, they are two runs.
- Count facings at the front only, not the ones behind them.

Answer with one JSON object and nothing else, no code fence and no other text:

{"problem": null, "shelves": [{"y_top": 0.0, "y_bottom": 0.0, "left_x": 0.0, "right_x": 0.0,
  "runs": [{"box": [0.0, 0.0, 0.0, 0.0], "facings": 1,
            "tag": {"name": "…", "code": "…", "price": "…"}, "package": null},
           {"box": [0.0, 0.0, 0.0, 0.0], "facings": 1, "tag": null,
            "package": {"brand": "…", "name": "…", "size": "…"}}]}]}

`problem` is a short English sentence when the photograph cannot be read as asked (blurred, cut
off, glare, not straight on), and `null` otherwise.
