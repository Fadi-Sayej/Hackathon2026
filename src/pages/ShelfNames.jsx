/** A list of names, each isolated so a Hebrew name inside Arabic text keeps its own direction. */
export function Names({ barcodes, nameOf }) {
  return barcodes.map((b, i) => (
    <span key={b}>{i ? ' · ' : ''}<bdi>{nameOf(b)}</bdi></span>
  ))
}
