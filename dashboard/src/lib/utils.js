export function cn(...classes) {
  return classes.filter(Boolean).join(' ');
}

export function formatNumber(value) {
  return new Intl.NumberFormat('en-US').format(Number(value || 0));
}

export function classNames(...classes) {
  return classes.filter(Boolean).join(' ');
}
