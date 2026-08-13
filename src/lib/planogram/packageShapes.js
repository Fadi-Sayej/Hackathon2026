/**
 * Package-shape catalogue — the SKU geometry layer of the planogram.
 *
 * WHY THIS EXISTS
 *   Shelf-space allocation is a packing problem: how many facings of a product
 *   fit across a shelf run, and how many units sit behind each facing. That
 *   question is unanswerable without physical dimensions, and the YomYom POS
 *   export has none. It has a department, a name, and a price.
 *
 *   So we go through archetypes. There are perhaps fifty package shapes in a
 *   convenience store, and a 1.5L water bottle is 9cm wide whoever bottled it.
 *   Each product is matched to an archetype, and the archetype carries both the
 *   drawing recipe and the real-world centimetres.
 *
 * TWO SETS OF NUMBERS, DO NOT CONFUSE THEM
 *   `w`/`h`           — percentages, for DRAWING only. How much of its slot the
 *                       package fills on screen. Ported from the design file.
 *   `widthCm` etc.    — real centimetres, for the ALLOCATION ENGINE. These are
 *                       archetype estimates, not measurements of a specific SKU,
 *                       and every product placed through them is flagged
 *                       `estimatedGeometry: true` so the UI can say so.
 *
 *   A product whose true package differs from its archetype gets the wrong
 *   facing count. That is a known and accepted error until real dimensions are
 *   available; it is bounded by the archetype, which is far better than the
 *   `shelfCapacity: 10` constant it replaces.
 */

import { shade } from './format.js'

/**
 * @param label      Arabic display name of the archetype
 * @param group      catalogue section, for the shape-library UI
 * @param color      body colour
 * @param w,h        drawing size, percent of the slot
 * @param bodyR      body border-radius
 * @param cap        [widthPct, heightPx, radius] or null
 * @param neck       [widthPct, heightPx] or null
 * @param dims       [widthCm, heightCm, depthCm] — real-world estimate
 */
const shape = (label, group, color, w, h, bodyR, cap, neck, dims) => ({
  label,
  group,
  color,
  w,
  h,
  bodyR,
  cap,
  neck,
  widthCm: dims[0],
  heightCm: dims[1],
  depthCm: dims[2],
})

export const PACKAGE_SHAPES = {
  water_s: shape('زجاجة ماء صغيرة', 'مشروبات', '#8ecae6', 46, 86, '6px 6px 4px 4px', [34, 6, '2px'], [44, 9], [6.5, 22, 6.5]),
  water_l: shape('زجاجة ماء كبيرة', 'مشروبات', '#4ea8d8', 62, 96, '7px 7px 5px 5px', [36, 7, '2px'], [48, 10], [9, 32, 9]),
  soda_bottle: shape('زجاجة مشروب غازي', 'مشروبات', '#b03a2e', 56, 92, '9px 9px 6px 6px', [34, 6, '2px'], [46, 11], [9, 33, 9]),
  soda_can: shape('علبة مشروب معدنية', 'مشروبات', '#c0392b', 52, 58, '3px 3px 5px 5px', [100, 6, '20px 20px 2px 2px'], null, [6.6, 11.5, 6.6]),
  juice_s: shape('عصير كرتون صغير', 'مشروبات', '#e58a1f', 44, 56, '2px', [26, 8, '2px 2px 0 0'], null, [4, 10.5, 4]),
  juice_l: shape('عصير كرتون كبير', 'مشروبات', '#e07b1f', 56, 88, '2px', [54, 10, '2px 7px 1px 1px'], null, [7, 20, 7]),
  milk_carton: shape('حليب كرتون', 'ألبان', '#e6ecf1', 56, 92, '2px', [30, 8, '3px'], [50, 6], [7, 20, 7]),
  drink_yogurt: shape('لبن للشرب', 'ألبان', '#f0e2d0', 48, 84, '8px', [36, 7, '2px'], [46, 8], [6.5, 19, 6.5]),
  yogurt_cup: shape('كوب زبادي', 'ألبان', '#f2c1c8', 58, 44, '0 0 8px 8px', [100, 5, '3px 3px 0 0'], null, [9.5, 7, 9.5]),
  white_cheese: shape('علبة جبنة بيضاء', 'ألبان', '#f5efe0', 72, 40, '0 0 4px 4px', [100, 5, '3px 3px 0 0'], null, [11, 5.5, 11]),
  cheese_slices: shape('جبنة شرائح', 'ألبان', '#f6c445', 76, 30, '4px', null, null, [13, 3, 10]),
  butter: shape('زبدة / مارجرين', 'ألبان', '#f7e08a', 70, 28, '3px', null, null, [10, 4, 7]),
  eggs: shape('علبة بيض', 'ألبان', '#d8c3a5', 78, 34, '2px 2px 8px 8px', [96, 6, '6px 6px 0 0'], null, [15, 7.5, 30]),
  bread_fresh: shape('خبز طازج', 'مخبوزات', '#c88f4e', 80, 58, '0 0 10px 10px', [70, 12, '18px 18px 0 0'], null, [20, 12, 14]),
  toast_bag: shape('توست مغلف', 'مخبوزات', '#e7d6b8', 70, 66, '0 0 8px 8px', [52, 10, '10px 10px 0 0'], null, [14, 12, 22]),
  biscuit_pack: shape('بسكويت باكيت', 'مخبوزات', '#b5651d', 84, 34, '5px', null, null, [16, 5, 6]),
  biscuit_box: shape('بسكويت صندوق', 'مخبوزات', '#8d5524', 62, 60, '3px', null, null, [12, 12, 6]),
  chips: shape('رقائق / شيبس', 'سناكات', '#f0a202', 72, 74, '0 0 12px 12px', [54, 10, '8px 8px 0 0'], null, [18, 28, 8]),
  popcorn: shape('فشار / سناك منتفخ', 'سناكات', '#e8c547', 78, 80, '0 0 14px 14px', [58, 12, '10px 10px 0 0'], null, [18, 30, 9]),
  choco_bar: shape('لوح شوكولاتة', 'سناكات', '#5a3921', 86, 22, '3px', null, null, [15, 3, 8]),
  choco_small: shape('شوكولاتة صغيرة', 'سناكات', '#7b4a2d', 40, 26, '3px', null, null, [6, 4, 3]),
  gum: shape('علكة', 'سناكات', '#2f8f5b', 38, 18, '2px', null, null, [5, 2.5, 2]),
  candy_bag: shape('سكاكر كيس', 'سناكات', '#d64550', 62, 62, '0 0 10px 10px', [46, 9, '8px 8px 0 0'], null, [14, 20, 6]),
  rice: shape('رز', 'مواد جافة', '#dfd3b0', 66, 78, '0 0 5px 5px', [54, 10, '7px 7px 0 0'], null, [22, 32, 12]),
  sugar: shape('سكر', 'مواد جافة', '#eae3d2', 58, 66, '0 0 3px 3px', [50, 8, '4px 4px 0 0'], null, [11, 16, 7]),
  flour: shape('طحين', 'مواد جافة', '#d9c9a8', 68, 80, '0 0 4px 4px', [56, 10, '6px 6px 0 0'], null, [13, 22, 8]),
  pasta: shape('معكرونة', 'مواد جافة', '#e0c070', 52, 88, '3px', null, null, [8, 22, 5]),
  legumes: shape('بقوليات جافة', 'مواد جافة', '#c2a76b', 58, 64, '0 0 8px 8px', [44, 8, '6px 6px 0 0'], null, [10, 16, 6]),
  spice: shape('بهارات صغيرة', 'مواد جافة', '#b5651d', 34, 34, '3px', [60, 6, '2px'], null, [4.5, 9, 4.5]),
  sauce_jar: shape('مرطبان صلصة', 'معلبات', '#a8342a', 56, 64, '5px 5px 8px 8px', [68, 8, '3px'], [58, 4], [8, 14, 8]),
  tomato_paste: shape('رب بندورة', 'معلبات', '#c0392b', 42, 34, '0 0 3px 3px', [100, 5, '3px 3px 0 0'], null, [7, 8, 7]),
  canned_veg: shape('معلبات خضار', 'معلبات', '#2f7d4f', 52, 52, '2px 2px 4px 4px', [100, 6, '18px 18px 2px 2px'], null, [7.5, 11, 7.5]),
  tuna: shape('معلبات تونة', 'معلبات', '#34689b', 58, 22, '0 0 3px 3px', [100, 4, '10px 10px 0 0'], null, [8.5, 3, 8.5]),
  pickles: shape('مخللات مرطبان', 'معلبات', '#6b8e23', 52, 78, '4px 4px 7px 7px', [70, 8, '3px'], [62, 5], [9, 18, 9]),
  cooking_oil: shape('زيت طبخ', 'زيوت وصلصات', '#d7a520', 52, 92, '5px', [32, 7, '2px'], [44, 9], [8, 26, 8]),
  olive_oil: shape('زيت زيتون', 'زيوت وصلصات', '#4a7c2f', 42, 94, '5px 5px 4px 4px', [28, 7, '2px'], [36, 12], [7, 28, 7]),
  squeeze_sauce: shape('صلصة ضغط', 'زيوت وصلصات', '#d63c2f', 46, 72, '10px 10px 6px 6px', [34, 9, '3px 3px 1px 1px'], [40, 5], [7, 18, 5]),
  coffee: shape('قهوة', 'مشروبات ساخنة', '#6f4e37', 54, 60, '4px', [76, 8, '3px'], null, [9, 13, 9]),
  tea_box: shape('شاي', 'مشروبات ساخنة', '#7a9c3f', 56, 54, '3px', null, null, [9, 9, 6]),
  tissue_box: shape('مناديل ورقية', 'ورقيات', '#6aa9d8', 80, 36, '3px', [30, 4, '6px'], null, [22, 9, 11]),
  toilet_paper: shape('ورق تواليت', 'ورقيات', '#d98cae', 86, 64, '10px', null, null, [24, 22, 12]),
  dish_soap: shape('صابون جلي', 'تنظيف', '#2f9e8f', 46, 82, '8px 8px 5px 5px', [30, 9, '3px 3px 1px 1px'], [38, 7], [7, 22, 7]),
  floor_cleaner: shape('منظف أرضيات', 'تنظيف', '#2f8fa8', 56, 94, '6px 6px 4px 4px', [34, 10, '3px'], [44, 6], [10, 28, 10]),
  toilet_cleaner: shape('منظف حمام', 'تنظيف', '#5a63b0', 48, 84, '8px 8px 5px 5px', [40, 9, '9px 2px 2px 2px'], [36, 8], [8, 24, 8]),
  spray: shape('بخاخ تنظيف', 'تنظيف', '#3aa17e', 52, 80, '4px', [70, 11, '3px 9px 2px 2px'], [42, 7], [8, 24, 8]),
  laundry_powder: shape('مسحوق غسيل', 'تنظيف', '#4a63b8', 72, 82, '3px', null, null, [22, 26, 12]),
  laundry_liquid: shape('سائل غسيل', 'تنظيف', '#7d5ba6', 66, 86, '8px 8px 6px 6px', [26, 8, '3px'], [34, 6], [14, 26, 11]),
  shampoo: shape('شامبو / صابون جسم', 'عناية', '#c86b9e', 44, 78, '10px 10px 6px 6px', [36, 9, '6px 6px 2px 2px'], [34, 5], [6.5, 20, 6.5]),
  diapers: shape('حفاضات / فوط', 'عناية', '#6cc0d8', 88, 70, '12px', null, null, [30, 22, 18]),
  cigarettes: shape('سجائر', 'أخرى', '#8a8f98', 40, 48, '3px', null, null, [5.5, 9, 2.5]),
  retail_box: shape('علبة كرتون عامة', 'أخرى', '#b0a58f', 64, 56, '3px', null, null, [12, 14, 8]),
  blister_pack: shape('تغليف معلّق', 'أخرى', '#9fb3c8', 54, 62, '3px 3px 2px 2px', [70, 5, '6px 6px 0 0'], null, [9, 16, 3]),
  produce_crate: shape('صندوق خضار', 'أخرى', '#8fc17a', 92, 34, '2px', null, null, [30, 12, 40]),
}

export const DEFAULT_SHAPE_KEY = 'pasta'

/**
 * Exact category matches, checked first.
 *
 * Two vocabularies land in `product.category`: the twelve English labels that
 * `standardizeCategory()` in scripts/normalize-datasets.mjs maps onto, and any
 * Hebrew department name that fell through it unchanged.
 */
const CATEGORY_TO_SHAPE = {
  // English canonical categories
  'Cold Drinks': 'soda_bottle',
  'Energy Drinks': 'soda_can',
  Water: 'water_l',
  Snacks: 'chips',
  Chocolate: 'choco_bar',
  'Gum & Candy': 'gum',
  Dairy: 'yogurt_cup',
  Bakery: 'bread_fresh',
  Coffee: 'coffee',
  Cigarettes: 'cigarettes',
  'Ice Cream': 'yogurt_cup',
  'Car Accessories': 'spray',

  // Departments as they actually appear in the YomYom export, by row count.
  // These strings were read off the data, not guessed — a department renamed at
  // the till silently falls through to the keyword scan below, which is the
  // intended degradation rather than a bug.
  'מוצרי מכולת': 'pasta', // 2,472 rows — dry grocery
  'חטיפים מתוקים': 'choco_bar', // 848
  'משקאות': 'soda_bottle', // 500
  'מוצרי מקרר': 'yogurt_cup', // 457 — chilled
  'חטיפים מלוחים': 'chips', // 347
  'מוצרי בית': 'tissue_box', // 329 — household
  'אבזרי סלולר ו חשמל': 'blister_pack', // 278 — phone/electrical accessories
  'גלידות': 'yogurt_cup', // 205 — ice cream
  'מוצרי ניקיון ו טיפוח אישי': 'floor_cleaner', // 185 — cleaning & personal care
  'מוצרי יום הולדת ו מתנות': 'retail_box', // 171 — party & gifts
  'מוצרי חצר תחנה': 'spray', // 144 — forecourt / car care
  'תכשיטים לילדות קטנות': 'blister_pack', // 131 — children's jewellery
  'מוצרי שימוש מטבח -חנות': 'retail_box', // 126 — kitchenware
  'פירות וירקות': 'produce_crate', // 115 — produce
  'כל הסיגריות': 'cigarettes', // 113
}

/**
 * Departments that hold no shelvable goods.
 *
 * The YomYom till rings up car washes, wash subscriptions and drive-through
 * meal deals as products, and the export cannot tell them apart from a bag of
 * crisps — they have a price, a cost and a stock figure. A car wash allocated
 * eight facings of eye-level space is not a rounding error, it is a screen the
 * manager stops trusting.
 *
 * Kept as an explicit department list rather than a name heuristic: the
 * departments are stable and inspectable, whereas guessing from product names
 * would silently drop real merchandise.
 */
const NON_MERCHANDISE_CATEGORIES = new Set([
  'קופה שטיפה (הכל )', // car-wash register: services and subscriptions
  'בדיקה', // literally "test" — POS test rows
  'מחלקת drive', // drive-through combo deals, not shelf stock
])

/** Whether a catalogue row represents something that can sit on a shelf. */
export function isShelvable(product) {
  return !NON_MERCHANDISE_CATEGORIES.has(String(product?.category ?? ''))
}

/**
 * Keyword fallback, scanned over category + product name.
 *
 * Ordered most-specific first: 'מים מינרלים' must reach `water_l` before the
 * generic drink rule claims it. Hebrew and English keys are mixed deliberately
 * — a product name may be either.
 */
const KEYWORD_TO_SHAPE = [
  [['מים', 'water', 'mineral'], 'water_l'],
  [['פחית', 'can ', 'energy'], 'soda_can'],
  [['קולה', 'סודה', 'משקה', 'cola', 'soda'], 'soda_bottle'],
  [['מיץ', 'juice', 'nectar'], 'juice_l'],
  [['חלב', 'milk'], 'milk_carton'],
  [['יוגורט', 'yogurt', 'לבן'], 'yogurt_cup'],
  [['גבינה', 'cheese'], 'white_cheese'],
  [['ביצים', 'egg'], 'eggs'],
  [['חמאה', 'butter', 'margarine'], 'butter'],
  [['לחם', 'פיתה', 'bread', 'pita'], 'bread_fresh'],
  [['טוסט', 'toast'], 'toast_bag'],
  [['עוגיות', 'ביסקוויט', 'biscuit', 'cookie'], 'biscuit_pack'],
  [['במבה', 'ביסלי', 'צ׳יפס', "צ'יפס", 'chips', 'crisps'], 'chips'],
  [['פופקורן', 'popcorn'], 'popcorn'],
  [['שוקולד', 'chocolate'], 'choco_bar'],
  [['מסטיק', 'gum'], 'gum'],
  [['סוכריות', 'candy', 'sweets'], 'candy_bag'],
  [['אורז', 'rice'], 'rice'],
  [['סוכר', 'sugar'], 'sugar'],
  [['קמח', 'flour'], 'flour'],
  [['פסטה', 'ספגטי', 'pasta', 'spaghetti', 'noodle'], 'pasta'],
  [['עדשים', 'חומוס', 'קטניות', 'lentil', 'chickpea', 'beans'], 'legumes'],
  [['תבלין', 'spice', 'pepper'], 'spice'],
  [['רסק', 'paste'], 'tomato_paste'],
  [['טונה', 'tuna', 'sardine'], 'tuna'],
  [['חמוצים', 'מלפפון חמוץ', 'pickle'], 'pickles'],
  [['רוטב', 'sauce', 'ketchup', 'mayo'], 'squeeze_sauce'],
  [['שימורי', 'canned', 'תירס', 'corn'], 'canned_veg'],
  [['שמן זית', 'olive oil'], 'olive_oil'],
  [['שמן', 'oil'], 'cooking_oil'],
  [['קפה', 'coffee', 'nescafe'], 'coffee'],
  [['תה', 'tea'], 'tea_box'],
  [['ממחטות', 'מגבונים', 'tissue', 'wipes'], 'tissue_box'],
  [['נייר טואלט', 'toilet paper'], 'toilet_paper'],
  [['אבקת כביסה', 'detergent powder'], 'laundry_powder'],
  [['כביסה', 'laundry', 'softener'], 'laundry_liquid'],
  [['כלים', 'dish'], 'dish_soap'],
  [['רצפה', 'floor'], 'floor_cleaner'],
  [['אסלה', 'toilet cleaner'], 'toilet_cleaner'],
  [['ספריי', 'spray'], 'spray'],
  [['שמפו', 'סבון', 'shampoo', 'soap'], 'shampoo'],
  [['חיתולים', 'diaper', 'pad'], 'diapers'],
  [['סיגריות', 'cigarette', 'tobacco'], 'cigarettes'],
]

/**
 * Pick the package archetype for a product.
 *
 * Returns the shape key plus whether the match was confident. `matched: false`
 * means the product fell through to the default and its facing count is a
 * guess dressed as a number — the UI must not present it as measured.
 */
/**
 * Shortest keyword that may outrank a department.
 *
 * Hebrew is dense: `תה` (tea) is a substring of `פיתה` (pita), so a two-letter
 * keyword allowed to override a department turns pita bread into a tea box.
 * Three characters is the point where a match stops being coincidence. Shorter
 * keywords still run, but only after the department has had its say.
 */
const STRONG_KEYWORD_LENGTH = 3

/**
 * Pick the package archetype for a product.
 *
 * Order matters, and it is the opposite of what it looks like it should be.
 * The department is the coarse signal — `מוצרי מכולת` covers 2,472 products from
 * pasta to rice to cooking oil, and letting it win produced a shelf of 2,472
 * identical boxes. A distinctive word in the product name is far stronger
 * evidence, so it goes first.
 *
 * Returns the shape key plus whether the match was confident. `matched: false`
 * means the product fell through to the default and its facing count is a guess
 * dressed as a number — the UI must not present it as measured.
 */
export function resolvePackageShape(product) {
  const category = String(product?.category ?? '')
  const name = String(product?.name ?? '')
  const nameHaystack = name.toLowerCase()

  // 1. A distinctive word in the product name beats the department.
  for (const [keywords, key] of KEYWORD_TO_SHAPE) {
    const strong = keywords.filter((keyword) => keyword.trim().length >= STRONG_KEYWORD_LENGTH)
    if (strong.some((keyword) => nameHaystack.includes(keyword.toLowerCase()))) {
      return { key, matched: true }
    }
  }

  // 2. Otherwise the department, which always has an answer for a known one.
  const exact = CATEGORY_TO_SHAPE[category]
  if (exact) return { key: exact, matched: true }

  // 3. Last, the short keywords, now that they cannot outrank a department.
  const haystack = `${category} ${name}`.toLowerCase()
  for (const [keywords, key] of KEYWORD_TO_SHAPE) {
    if (keywords.some((keyword) => haystack.includes(keyword.toLowerCase()))) {
      return { key, matched: true }
    }
  }

  return { key: DEFAULT_SHAPE_KEY, matched: false }
}

/**
 * Nominal content of each archetype, in millilitres (grams counted as
 * millilitres — close enough for a package envelope).
 *
 * Only the archetypes whose products routinely state a size in the name are
 * listed. An archetype with no entry here is never scaled, which is the correct
 * behaviour for things like nappies or cigarettes where the printed number says
 * nothing about the box.
 */
const SHAPE_REFERENCE_ML = {
  water_s: 500,
  water_l: 1500,
  soda_bottle: 1500,
  soda_can: 330,
  juice_s: 200,
  juice_l: 1000,
  milk_carton: 1000,
  drink_yogurt: 1000,
  yogurt_cup: 150,
  chips: 150,
  popcorn: 100,
  choco_bar: 100,
  candy_bag: 200,
  rice: 5000,
  sugar: 1000,
  flour: 1000,
  pasta: 500,
  legumes: 500,
  cooking_oil: 1000,
  olive_oil: 750,
  sauce_jar: 500,
  pickles: 700,
  coffee: 200,
  dish_soap: 750,
  floor_cleaner: 2000,
  laundry_liquid: 2000,
  laundry_powder: 3000,
  shampoo: 400,
  spray: 500,
}

/** Size tokens as they appear in Hebrew and English product names. */
const SIZE_PATTERNS = [
  [/(\d+(?:[.,]\d+)?)\s*(?:ליטר|ל'|liter|litre|lt\b|l\b)/i, 1000],
  [/(\d+(?:[.,]\d+)?)\s*(?:מ["״']?ל|ml\b)/i, 1],
  [/(\d+(?:[.,]\d+)?)\s*(?:ק["״']?ג|קילו|kg\b)/i, 1000],
  [/(\d+(?:[.,]\d+)?)\s*(?:גרם|ג'|גר\b|g\b|gr\b)/i, 1],
  [/(\d+(?:[.,]\d+)?)\s*ג(?![א-ת])/, 1], // "80ג" — no space, no following letter
]

/**
 * Read the package size out of a product name.
 *
 * Hebrew grocery names carry the size far more reliably than any column in the
 * export does: "ספרייט ZERO לימון נענע 1.5 ליטר", "תפוצ'יפס טבעי 50 גרם".
 * Returns null when nothing parses, which is the common case and not an error.
 */
export function parsePackageSizeMl(name) {
  const text = String(name ?? '')
  for (const [pattern, multiplier] of SIZE_PATTERNS) {
    const match = pattern.exec(text)
    if (!match) continue
    const value = Number(match[1].replace(',', '.'))
    if (Number.isFinite(value) && value > 0) return value * multiplier
  }
  return null
}

/**
 * How far a package's dimensions may be scaled from its archetype.
 *
 * A 250ml can and a 1.5L bottle are both "משקאות" and would otherwise share a
 * 2.7-litre envelope — which made energy drinks read as heavy goods and sent
 * them to the bottom shelf. Volume scales as the cube of a linear dimension, so
 * the linear correction is the cube root. Clamped because a 20ml perfume sample
 * is not one-fourth the width of a bottle; packaging has a floor.
 */
const SCALE_RANGE = [0.55, 1.8]

/** Real-world geometry for a product, in centimetres. */
export function packageGeometry(product) {
  const { key, matched } = resolvePackageShape(product)
  const shapeDef = PACKAGE_SHAPES[key]

  const referenceMl = SHAPE_REFERENCE_ML[key]
  const actualMl = referenceMl ? parsePackageSizeMl(product?.name) : null
  const scale = actualMl
    ? clamp((actualMl / referenceMl) ** (1 / 3), SCALE_RANGE[0], SCALE_RANGE[1])
    : 1

  return {
    shapeKey: key,
    widthCm: round1(shapeDef.widthCm * scale),
    heightCm: round1(shapeDef.heightCm * scale),
    depthCm: round1(shapeDef.depthCm * scale),
    sizeMl: actualMl,
    // True when the archetype itself was a guess. A scaled-but-matched archetype
    // is still an estimate, but a far better one, so it is not flagged.
    estimatedGeometry: !matched,
  }
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function round1(value) {
  return Math.round(value * 10) / 10
}

/**
 * Drawing recipe for one archetype: everything the shelf renderer needs to put
 * a recognisable package on screen without knowing what a package is.
 */
export function shapeVisual(key) {
  const shapeDef = PACKAGE_SHAPES[key] ?? PACKAGE_SHAPES[DEFAULT_SHAPE_KEY]
  return {
    typeLabel: shapeDef.label,
    group: shapeDef.group,
    color: shapeDef.color,
    // Labels are only legible on a package tall enough to hold them.
    showName: shapeDef.h >= 45,
    showSku: shapeDef.h >= 62,
    faceW: `${shapeDef.w}%`,
    faceH: `${shapeDef.h}%`,
    hasCap: Boolean(shapeDef.cap),
    hasNeck: Boolean(shapeDef.neck),
    capW: shapeDef.cap ? `${shapeDef.cap[0]}%` : '0',
    capH: shapeDef.cap ? `${shapeDef.cap[1]}px` : '0',
    capR: shapeDef.cap ? shapeDef.cap[2] : '0',
    neckW: shapeDef.neck ? `${shapeDef.neck[0]}%` : '0',
    neckH: shapeDef.neck ? `${shapeDef.neck[1]}px` : '0',
    bodyR: shapeDef.bodyR,
    capColor: shade(shapeDef.color, 0.68),
    neckColor: shade(shapeDef.color, 0.84),
  }
}

/** The shape library grouped by section, for the catalogue panel. */
export function shapeCatalogue() {
  const groups = []
  for (const key of Object.keys(PACKAGE_SHAPES)) {
    const visual = shapeVisual(key)
    let group = groups.find((entry) => entry.name === visual.group)
    if (!group) {
      group = { name: visual.group, items: [] }
      groups.push(group)
    }
    group.items.push({ key, ...visual })
  }
  return groups
}
