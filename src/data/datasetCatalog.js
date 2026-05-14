export const selectedDatasets = [
  {
    role: 'Primary MVP',
    name: 'Retail Store Inventory Forecasting Dataset',
    provider: 'Kaggle / anirudhchauhan',
    status: 'Chosen for Sprint 2 mapping',
    why:
      'Closest fit to stock, sales, and inventory-style reasoning for the first SmartShelf recommendation engine.',
  },
  {
    role: 'Secondary Analytics / RAG',
    name: 'FreshRetailNet-50K',
    provider: 'Hugging Face / Dingdong-Inc',
    status: 'Reserved for later summaries',
    why:
      'Useful as a richer secondary source for product context, retail knowledge extraction, and future RAG-oriented documents.',
  },
]

export const datasetCatalog = [
  {
    id: 'retail-store-inventory-forecasting',
    name: 'Retail Store Inventory Forecasting Dataset',
    provider: 'Kaggle / anirudhchauhan',
    type: 'Dataset',
    usage: 'Primary MVP candidate',
    priority: 'High',
    summary:
      'Best functional match for SmartShelf because it is already close to inventory forecasting and reorder logic.',
  },
  {
    id: 'grocery-sales-dataset',
    name: 'Grocery Sales Dataset',
    provider: 'Kaggle / andrexibiza',
    type: 'Dataset',
    usage: 'Backup MVP candidate',
    priority: 'High',
    summary:
      'Strong fallback if the primary MVP source has awkward columns or does not map cleanly into the SmartShelf schema.',
  },
  {
    id: 'freshretailnet-50k',
    name: 'FreshRetailNet-50K',
    provider: 'Hugging Face / Dingdong-Inc',
    type: 'Dataset',
    usage: 'Secondary analytics and RAG source',
    priority: 'Medium',
    summary:
      'Promising source for broader retail product context and later retrieval-oriented knowledge preparation.',
  },
  {
    id: 'm5-forecasting-accuracy',
    name: 'M5 Forecasting Accuracy',
    provider: 'Kaggle Competition',
    type: 'Competition',
    usage: 'Advanced analytics reference',
    priority: 'Low',
    summary:
      'Excellent forecasting benchmark, but too heavy and indirect for the first MVP data mapping step.',
  },
  {
    id: 'favorita-grocery-sales-forecasting',
    name: 'Favorita Grocery Sales Forecasting',
    provider: 'Kaggle Competition',
    type: 'Competition',
    usage: 'Future trend and seasonality reference',
    priority: 'Low',
    summary:
      'Useful later for heuristics and temporal patterns, not ideal as the first application-facing dataset.',
  },
  {
    id: 'demand-forecasting-kernels-only',
    name: 'Demand Forecasting Kernels Only',
    provider: 'Kaggle Competition',
    type: 'Competition',
    usage: 'Reference only',
    priority: 'Low',
    summary:
      'Helpful for model ideas and forecasting experimentation, but not the fastest route to SmartShelf MVP data.',
  },
  {
    id: 'retailrocket-ecommerce',
    name: 'Retailrocket Ecommerce Dataset',
    provider: 'Kaggle / retailrocket',
    type: 'Dataset',
    usage: 'Behavioral side reference',
    priority: 'Low',
    summary:
      'Interesting for customer behavior patterns, but less aligned with convenience-store inventory decisions.',
  },
]

export const storageBlueprint = [
  {
    path: 'data/raw/huggingface/',
    purpose: 'Original Hugging Face downloads kept unchanged for traceability.',
  },
  {
    path: 'data/raw/kaggle/',
    purpose: 'Original Kaggle files preserved exactly as downloaded.',
  },
  {
    path: 'data/processed/demo/',
    purpose: 'Small clean slices that will later feed src/data/demoProducts.js.',
  },
  {
    path: 'data/processed/analytics/',
    purpose: 'Normalized tables for rule tuning, comparisons, and derived metrics.',
  },
  {
    path: 'data/processed/rag/',
    purpose: 'Future summaries, chunks, and retrieval-ready documents kept separate from app data.',
  },
  {
    path: 'data/exports/sample-app-data/',
    purpose: 'Final export location for UI-ready JSON or CSV used by the SmartShelf frontend.',
  },
]
