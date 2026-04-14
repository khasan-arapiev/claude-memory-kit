// Checkout handler (modern version)
export function checkout(cart) {
  return fetch("/api/checkout/v2", { method: "POST", body: JSON.stringify(cart) });
}
