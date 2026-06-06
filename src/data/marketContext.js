export const marketContext = {
  currentDate: new Date().toISOString().split('T')[0],
  weather: 'hot',
  weekend: true,
  holiday: false,
  localEvent: 'football match nearby',
  season: 'summer',
  demandSignals: {
    'Cold Drinks': 1.18,
    'Energy Drinks': 1.16,
    Water: 1.2,
    Snacks: 1.1,
    'Ice Cream': 1.15,
  },
}
