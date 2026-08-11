// GENERATED — do not edit by hand.
// Source: configs/market_params.yaml + configs/archetypes.yaml
// Regenerate: python3 scripts/export_market_params.py
// Generated: 2026-08-11T23:05:19+00:00

// 109 parameters across 12 families, 58 active.
// Inactive parameters sit at neutral 1.0 and change nothing.

export const MARKET_PARAM_REGISTRY = {
  "clamp": [
    0.2,
    3.0
  ],
  "families": {
    "weather": {
      "weight": 1.0,
      "params": [
        {
          "id": "temp_max_c",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "temp_min_c",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "apparent_temp_c",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "temp_delta_vs_yday",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "precipitation_mm",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "humidity_pct",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "wind_speed_kmh",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "uv_index",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "heatwave_day",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "first_hot_day",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "first_cold_day",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "dust_storm",
          "type": "multiplier",
          "active": false
        }
      ]
    },
    "calendar_hebrew": {
      "weight": 1.0,
      "params": [
        {
          "id": "pesach_chametz_window",
          "type": "gate",
          "active": true
        },
        {
          "id": "pesach_day",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "erev_chag",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "shabbat_eve",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "rosh_hashanah",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "yom_kippur_fast",
          "type": "gate",
          "active": true
        },
        {
          "id": "sukkot",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "hanukkah",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "purim",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "minor_fast_day",
          "type": "multiplier",
          "active": false
        }
      ]
    },
    "calendar_islamic": {
      "weight": 1.0,
      "params": [
        {
          "id": "ramadan_daytime",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "ramadan_iftar",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "ramadan_suhoor",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "ramadan_last_10",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "eid_al_fitr",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "eid_al_adha",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "eid_eve",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "ashura",
          "type": "multiplier",
          "active": false
        }
      ]
    },
    "calendar_civil": {
      "weight": 0.8,
      "params": [
        {
          "id": "school_day",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "school_holiday",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "exam_period",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "summer_break",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "national_holiday",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "memorial_day",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "election_day",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "municipal_event",
          "type": "signal",
          "active": false
        }
      ]
    },
    "time_cycles": {
      "weight": 1.0,
      "params": [
        {
          "id": "day_of_week",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "weekend_fri_sat",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "pre_weekend_thu",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "hour_of_day",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "payday_window",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "month_start",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "month_end",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "season",
          "type": "multiplier",
          "active": true
        }
      ]
    },
    "competitor_presence": {
      "weight": 1.0,
      "params": [
        {
          "id": "coverage_ratio",
          "type": "signal",
          "active": true
        },
        {
          "id": "branches_carrying",
          "type": "signal",
          "active": true
        },
        {
          "id": "newly_appeared",
          "type": "signal",
          "active": false
        },
        {
          "id": "disappeared",
          "type": "signal",
          "active": false
        },
        {
          "id": "disappearance_concentration",
          "type": "signal",
          "active": false
        },
        {
          "id": "days_since_first_seen",
          "type": "signal",
          "active": false
        },
        {
          "id": "days_since_last_seen",
          "type": "signal",
          "active": false
        },
        {
          "id": "coverage_acceleration",
          "type": "signal",
          "active": false
        },
        {
          "id": "stockout_like",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "delisting_like",
          "type": "gate",
          "active": false
        }
      ]
    },
    "competitor_price": {
      "weight": 0.9,
      "params": [
        {
          "id": "price_gap_vs_median",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "competitor_price_min",
          "type": "signal",
          "active": true
        },
        {
          "id": "competitor_price_med",
          "type": "signal",
          "active": true
        },
        {
          "id": "competitor_price_max",
          "type": "signal",
          "active": true
        },
        {
          "id": "promo_active",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "promo_depth",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "promo_density",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "promo_cycle_phase",
          "type": "signal",
          "active": false
        },
        {
          "id": "price_volatility",
          "type": "signal",
          "active": false
        },
        {
          "id": "price_changepoint",
          "type": "signal",
          "active": false
        }
      ]
    },
    "trend": {
      "weight": 0.6,
      "params": [
        {
          "id": "wolt_most_ordered",
          "type": "signal",
          "active": true
        },
        {
          "id": "wolt_rank_in_category",
          "type": "signal",
          "active": true
        },
        {
          "id": "rank_delta",
          "type": "signal",
          "active": false
        },
        {
          "id": "is_online_available",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "google_trends_index",
          "type": "signal",
          "active": false
        },
        {
          "id": "google_trends_slope",
          "type": "signal",
          "active": false
        },
        {
          "id": "social_mentions",
          "type": "signal",
          "active": false
        },
        {
          "id": "adoption_curve_phase",
          "type": "signal",
          "active": false
        }
      ]
    },
    "location_mobility": {
      "weight": 0.7,
      "params": [
        {
          "id": "highway_traffic_index",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "competitor_open_now",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "nearby_event",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "roadworks_nearby",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "public_transport_gap",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "fuel_station_footfall",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "holiday_travel_peak",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "weather_travel_damper",
          "type": "multiplier",
          "active": false
        }
      ]
    },
    "macro": {
      "weight": 0.4,
      "params": [
        {
          "id": "fuel_price_ils",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "fuel_price_delta",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "usd_ils_rate",
          "type": "signal",
          "active": false
        },
        {
          "id": "cpi_food",
          "type": "signal",
          "active": false
        },
        {
          "id": "cpi_general",
          "type": "signal",
          "active": false
        },
        {
          "id": "minimum_wage_day",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "national_strike",
          "type": "multiplier",
          "active": false
        }
      ]
    },
    "store_internal": {
      "weight": 1.2,
      "params": [
        {
          "id": "current_stock",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "days_of_cover",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "days_to_expiry",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "expired",
          "type": "gate",
          "active": true
        },
        {
          "id": "margin_rate",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "below_cost",
          "type": "signal",
          "active": true
        },
        {
          "id": "negative_stock",
          "type": "gate",
          "active": true
        },
        {
          "id": "stock_reconciles",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "supplier_lead_time",
          "type": "multiplier",
          "active": false
        },
        {
          "id": "supplier_min_order",
          "type": "signal",
          "active": false
        }
      ]
    },
    "product_intrinsic": {
      "weight": 1.0,
      "params": [
        {
          "id": "archetype",
          "type": "signal",
          "active": true
        },
        {
          "id": "pack_class",
          "type": "signal",
          "active": true
        },
        {
          "id": "is_impulse",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "is_on_the_go",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "is_perishable",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "is_chametz",
          "type": "signal",
          "active": true
        },
        {
          "id": "is_kitniyot",
          "type": "signal",
          "active": false
        },
        {
          "id": "store_fit",
          "type": "multiplier",
          "active": true
        },
        {
          "id": "price_band",
          "type": "signal",
          "active": true
        },
        {
          "id": "segment",
          "type": "signal",
          "active": true
        }
      ]
    }
  },
  "gates": {
    "pesach_chametz_window": {
      "requiresFlag": "is_chametz",
      "requiresHumanReview": true
    },
    "expired": {
      "requiresFlag": null,
      "requiresHumanReview": false
    },
    "negative_stock": {
      "requiresFlag": null,
      "requiresHumanReview": false
    }
  }
}

export const PRODUCT_ARCHETYPES = {
  "water_bottle": {
    "labelAr": "مياه معبأة",
    "flags": {
      "isImpulse": true,
      "isOnTheGo": true
    },
    "sensitivities": {
      "temp_max_c": 1.45,
      "apparent_temp_c": 1.3,
      "heatwave_day": 1.6,
      "precipitation_mm": 0.85,
      "ramadan_iftar": 1.55,
      "ramadan_daytime": 0.7,
      "highway_traffic_index": 1.35,
      "summer_break": 1.2
    },
    "confidence": "assumed"
  },
  "cold_drink_single": {
    "labelAr": "مشروب بارد فردي",
    "flags": {
      "isImpulse": true,
      "isOnTheGo": true
    },
    "sensitivities": {
      "temp_max_c": 1.4,
      "heatwave_day": 1.5,
      "precipitation_mm": 0.85,
      "ramadan_iftar": 1.45,
      "ramadan_daytime": 0.55,
      "pre_weekend_thu": 1.15,
      "school_day": 1.15
    },
    "confidence": "assumed"
  },
  "energy_drink": {
    "labelAr": "مشروب طاقة",
    "flags": {
      "isImpulse": true,
      "isOnTheGo": true
    },
    "sensitivities": {
      "temp_max_c": 1.25,
      "highway_traffic_index": 1.4,
      "exam_period": 1.3,
      "pre_weekend_thu": 1.2,
      "hour_of_day": 1.15,
      "ramadan_daytime": 0.45
    },
    "confidence": "assumed"
  },
  "juice_carton": {
    "labelAr": "عصير",
    "flags": {
      "isPerishable": true
    },
    "sensitivities": {
      "temp_max_c": 1.2,
      "ramadan_iftar": 1.7,
      "eid_eve": 1.35,
      "school_day": 1.2
    },
    "confidence": "assumed"
  },
  "hot_beverage": {
    "labelAr": "مشروب ساخن",
    "flags": {
      "isOnTheGo": true
    },
    "sensitivities": {
      "temp_max_c": 0.6,
      "temp_min_c": 1.45,
      "precipitation_mm": 1.35,
      "first_cold_day": 1.5,
      "highway_traffic_index": 1.25
    },
    "confidence": "assumed"
  },
  "chametz_snack": {
    "labelAr": "وجبة خفيفة تحتوي حمץ",
    "flags": {
      "isChametz": true,
      "isImpulse": true,
      "isOnTheGo": true
    },
    "sensitivities": {
      "school_day": 1.3,
      "pre_weekend_thu": 1.15,
      "summer_break": 1.15,
      "ramadan_daytime": 0.4
    },
    "confidence": "assumed"
  },
  "chametz_bakery": {
    "labelAr": "مخبوزات تحتوي حمץ",
    "flags": {
      "isChametz": true,
      "isPerishable": true
    },
    "sensitivities": {
      "shabbat_eve": 1.25,
      "erev_chag": 1.2,
      "ramadan_suhoor": 1.4,
      "ramadan_daytime": 0.35
    },
    "confidence": "assumed"
  },
  "salty_snack": {
    "labelAr": "وجبة خفيفة مالحة",
    "flags": {
      "isImpulse": true,
      "isOnTheGo": true
    },
    "sensitivities": {
      "school_day": 1.25,
      "pre_weekend_thu": 1.2,
      "weekend_fri_sat": 1.15,
      "ramadan_daytime": 0.4,
      "ramadan_iftar": 1.2
    },
    "confidence": "assumed"
  },
  "impulse_chocolate": {
    "labelAr": "شوكولاتة",
    "flags": {
      "isImpulse": true
    },
    "sensitivities": {
      "temp_max_c": 0.8,
      "eid_eve": 1.45,
      "hanukkah": 1.3,
      "purim": 1.4,
      "school_day": 1.2,
      "ramadan_daytime": 0.4
    },
    "confidence": "assumed"
  },
  "candy_gum": {
    "labelAr": "حلوى وعلكة",
    "flags": {
      "isImpulse": true,
      "isOnTheGo": true
    },
    "sensitivities": {
      "school_day": 1.3,
      "highway_traffic_index": 1.25,
      "ramadan_daytime": 0.5
    },
    "confidence": "assumed"
  },
  "nuts_seeds": {
    "labelAr": "مكسرات وبذور",
    "flags": {
      "isImpulse": true
    },
    "sensitivities": {
      "ramadan_iftar": 1.5,
      "eid_al_fitr": 1.4,
      "weekend_fri_sat": 1.2,
      "temp_max_c": 1.05
    },
    "confidence": "assumed"
  },
  "protein_health_snack": {
    "labelAr": "وجبة بروتين صحية",
    "flags": {
      "isImpulse": true,
      "isOnTheGo": true
    },
    "sensitivities": {
      "highway_traffic_index": 1.25,
      "school_day": 1.1,
      "ramadan_daytime": 0.55
    },
    "confidence": "assumed"
  },
  "ice_cream": {
    "labelAr": "مثلجات",
    "flags": {
      "isImpulse": true,
      "isPerishable": true
    },
    "sensitivities": {
      "temp_max_c": 1.7,
      "heatwave_day": 1.9,
      "first_hot_day": 1.6,
      "temp_min_c": 0.5,
      "precipitation_mm": 0.65,
      "summer_break": 1.4,
      "ramadan_daytime": 0.4
    },
    "confidence": "assumed"
  },
  "ramadan_iftar_staple": {
    "labelAr": "أساسيات الإفطار",
    "flags": {},
    "sensitivities": {
      "ramadan_iftar": 2.2,
      "ramadan_daytime": 1.6,
      "ramadan_last_10": 1.35,
      "eid_eve": 1.3
    },
    "confidence": "assumed"
  },
  "dates_dried_fruit": {
    "labelAr": "تمر وفواكه مجففة",
    "flags": {},
    "sensitivities": {
      "ramadan_iftar": 2.4,
      "ramadan_daytime": 1.8,
      "eid_al_fitr": 1.5,
      "rosh_hashanah": 1.3
    },
    "confidence": "assumed"
  },
  "holiday_gift_item": {
    "labelAr": "هدايا الأعياد",
    "flags": {},
    "sensitivities": {
      "eid_eve": 1.8,
      "erev_chag": 1.7,
      "rosh_hashanah": 1.5,
      "hanukkah": 1.4
    },
    "confidence": "assumed"
  },
  "dairy_fresh": {
    "labelAr": "ألبان طازجة",
    "flags": {
      "isPerishable": true
    },
    "sensitivities": {
      "days_to_expiry": 1.4,
      "shabbat_eve": 1.25,
      "ramadan_suhoor": 1.45,
      "school_day": 1.15
    },
    "confidence": "assumed"
  },
  "ready_meal": {
    "labelAr": "وجبة جاهزة",
    "flags": {
      "isPerishable": true,
      "isOnTheGo": true
    },
    "sensitivities": {
      "highway_traffic_index": 1.45,
      "hour_of_day": 1.3,
      "ramadan_daytime": 0.3,
      "ramadan_iftar": 1.4,
      "school_day": 1.15
    },
    "confidence": "assumed"
  },
  "bread_fresh": {
    "labelAr": "خبز طازج",
    "flags": {
      "isChametz": true,
      "isPerishable": true
    },
    "sensitivities": {
      "shabbat_eve": 1.35,
      "ramadan_suhoor": 1.5,
      "erev_chag": 1.3
    },
    "confidence": "assumed"
  },
  "grocery_staple": {
    "labelAr": "سلع أساسية",
    "flags": {},
    "sensitivities": {
      "payday_window": 1.25,
      "month_start": 1.2,
      "ramadan_daytime": 1.3,
      "eid_eve": 1.35
    },
    "confidence": "assumed"
  },
  "household_bulk": {
    "labelAr": "عبوات كبيرة منزلية",
    "flags": {},
    "sensitivities": {
      "payday_window": 1.4,
      "month_start": 1.3,
      "store_fit": 0.5,
      "highway_traffic_index": 0.7
    },
    "confidence": "assumed"
  },
  "cleaning_supplies": {
    "labelAr": "مواد تنظيف",
    "flags": {},
    "sensitivities": {
      "payday_window": 1.25,
      "erev_chag": 1.5,
      "pesach_day": 1.6
    },
    "confidence": "assumed"
  },
  "tobacco": {
    "labelAr": "تبغ",
    "flags": {
      "isImpulse": true
    },
    "sensitivities": {
      "highway_traffic_index": 1.4,
      "hour_of_day": 1.2,
      "ramadan_daytime": 0.6,
      "ramadan_iftar": 1.5
    },
    "confidence": "assumed"
  },
  "alcohol_beer": {
    "labelAr": "بيرة",
    "flags": {},
    "sensitivities": {
      "temp_max_c": 1.45,
      "heatwave_day": 1.55,
      "pre_weekend_thu": 1.35,
      "weekend_fri_sat": 1.3,
      "ramadan_daytime": 0.3
    },
    "confidence": "assumed"
  },
  "alcohol_spirits": {
    "labelAr": "مشروبات روحية",
    "flags": {},
    "sensitivities": {
      "erev_chag": 1.4,
      "pre_weekend_thu": 1.25,
      "payday_window": 1.2
    },
    "confidence": "assumed"
  },
  "car_accessory": {
    "labelAr": "مستلزمات السيارة",
    "flags": {
      "isOnTheGo": true
    },
    "sensitivities": {
      "highway_traffic_index": 1.6,
      "holiday_travel_peak": 1.5,
      "summer_break": 1.3,
      "precipitation_mm": 1.25
    },
    "confidence": "assumed"
  },
  "phone_accessory": {
    "labelAr": "ملحقات الهاتف",
    "flags": {
      "isImpulse": true
    },
    "sensitivities": {
      "highway_traffic_index": 1.3,
      "payday_window": 1.15
    },
    "confidence": "assumed"
  },
  "personal_care": {
    "labelAr": "عناية شخصية",
    "flags": {},
    "sensitivities": {
      "payday_window": 1.2,
      "erev_chag": 1.25,
      "temp_max_c": 1.1
    },
    "confidence": "assumed"
  },
  "baby_care": {
    "labelAr": "مستلزمات الأطفال",
    "flags": {},
    "sensitivities": {
      "payday_window": 1.25,
      "month_start": 1.2
    },
    "confidence": "assumed"
  },
  "pharmacy_otc": {
    "labelAr": "أدوية بلا وصفة",
    "flags": {},
    "sensitivities": {
      "first_cold_day": 1.5,
      "temp_min_c": 1.3,
      "heatwave_day": 1.25,
      "dust_storm": 1.4
    },
    "confidence": "assumed"
  },
  "high_ticket_electronics": {
    "labelAr": "إلكترونيات مرتفعة الثمن",
    "flags": {},
    "sensitivities": {
      "store_fit": 0.3,
      "payday_window": 1.3,
      "holiday_gift_season": 1.4,
      "highway_traffic_index": 0.6
    },
    "confidence": "assumed"
  },
  "summer_seasonal": {
    "labelAr": "موسمي صيفي",
    "flags": {},
    "sensitivities": {
      "temp_max_c": 1.6,
      "season": 1.5,
      "summer_break": 1.45,
      "first_hot_day": 1.7,
      "temp_min_c": 0.5
    },
    "confidence": "assumed"
  },
  "winter_seasonal": {
    "labelAr": "موسمي شتوي",
    "flags": {},
    "sensitivities": {
      "temp_min_c": 1.6,
      "precipitation_mm": 1.5,
      "first_cold_day": 1.7,
      "temp_max_c": 0.5
    },
    "confidence": "assumed"
  },
  "school_seasonal": {
    "labelAr": "موسمي مدرسي",
    "flags": {},
    "sensitivities": {
      "school_day": 1.5,
      "summer_break": 0.4,
      "school_holiday": 0.5
    },
    "confidence": "assumed"
  },
  "unclassified": {
    "labelAr": "غير مصنّف",
    "flags": {},
    "sensitivities": {},
    "confidence": "none"
  }
}

export const MARKET_PARAM_STATS = {
  "total": 109,
  "active": 58,
  "families": 12,
  "archetypes": 35
}
