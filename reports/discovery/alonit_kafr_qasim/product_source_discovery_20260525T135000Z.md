# Alonit Kafr Qasim Product Source Discovery

- Status: No product-level source found yet.
- Confidence: medium-high
- Store-registry-only: yes
- JSON report: `C:\Users\mshar\Desktop\hackathonsj\reports\discovery\alonit_kafr_qasim\product_source_discovery_20260525T135000Z.json`

## Scope

This report checks whether Alonit Kafr Qasim / Al-Madina 2 has any product-level source for price files or catalog availability.

## Dor Alon Stores Search

- Latest raw Stores file used: `C:\Users\mshar\Desktop\hackathonsj\data\external\raw\alonit\2026\05\25\alonit_20260525T133754.xml`
- Total parsed store rows inspected: 157
- Searched aliases: כפר קאסם, קאסם, אלמדינה, אל מדינה, kafr qasim, kfar qasem, al-madina
- Result: No Dor Alon Stores match found for Kafr Qasim aliases in the latest parsed raw Stores XML.

- No matching rows found for Kafr Qasim aliases.

## Coordinate Check

- No latitude/longitude fields found in the parsed Dor Alon Stores XML evidence.
- Rows with coordinates: 0

## Source Registry

- No configs/sources.yaml file exists in this repository.

## Network Discovery

- Result: Existing Kafr Qasim network discovery evidence did not reveal a clear product catalog or price API.
- Candidate URLs:
  - https://easy.co.il/n/jsons/ddata?bizid=26305054
  - https://easy.co.il/n/jsons/ddata?bizid=26797254
  - https://easy.co.il/en/list/Alonit?region=1058
  - https://easy.co.il/en/page/26305054
  - https://www.doralon.co.il/station/

- Prepared commands:
  - `npm run discover:alonit-network -- --max-linked 2 --wait-ms 1500 --url alonit_kafr_qasim_easy_list=https://easy.co.il/en/list/Alonit?region=1058`
  - `npm run discover:alonit-network -- --max-linked 2 --wait-ms 1500 --url alonit_kafr_qasim_easy_page=https://easy.co.il/en/page/26305054`

## Next Manual Checks

- Open the Easy business page candidate at https://easy.co.il/en/page/26305054 and confirm whether it is the Kafr Qasim / Al-Madina 2 branch.
- If the Easy page is correct, inspect visible external website or order links before any further crawling.
- Check whether the branch is published under a different Dor Alon / Alonit / Super Alonit store name in any updated store registry export.
- If a direct order page is confirmed, run targeted discovery only for that URL with npm run discover:alonit-network.
- Manually test Wolt, TenBis, and Cibus search for the confirmed branch name and address; only build a connector if a direct venue URL exists.

## Final Status

No product-level source found yet.
