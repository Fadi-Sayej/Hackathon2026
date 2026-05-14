export function CategoryBars({ products }) {
  const categories = Object.values(
    products.reduce((acc, product) => {
      acc[product.category] ??= {
        category: product.category,
        sales: 0,
      }
      acc[product.category].sales += product.salesLast30Days
      return acc
    }, {}),
  )
    .sort((a, b) => b.sales - a.sales)
    .slice(0, 7)

  const maxSales = Math.max(...categories.map((category) => category.sales), 1)

  return (
    <div className="bar-list">
      {categories.map((category) => (
        <div className="bar-row" key={category.category}>
          <span>{category.category}</span>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(category.sales / maxSales) * 100}%` }} />
          </div>
          <strong>{category.sales}</strong>
        </div>
      ))}
    </div>
  )
}
