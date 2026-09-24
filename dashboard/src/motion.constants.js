/** Shared framer-motion vocabulary for dashboard interfaces. */
export const easing = {
  easeInOut: [0.4, 0, 0.2, 1],
  easeOut: [0, 0, 0.2, 1],
  easeIn: [0.4, 0, 1, 1],
  bounce: 'circOut',
};

export const transitions = {
  snappy: { duration: 0.2, ease: easing.easeInOut },
  standard: { duration: 0.3, ease: easing.easeInOut },
  deliberate: { duration: 0.5, ease: easing.easeInOut },
  slow: { duration: 0.8, ease: easing.easeInOut },
  bounce: { type: 'spring', stiffness: 300, damping: 20, mass: 1 },
};

/** Reveal an element by fading and sliding down into place. */
export const fadeSlideDown = {
  hidden: { opacity: 0, y: -16 },
  visible: { opacity: 1, y: 0, transition: transitions.standard },
};
/** Reveal an element by fading and sliding up into place. */
export const fadeSlideUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: transitions.standard },
};
/** Minimal opacity-only transition for dense lists and data. */
export const fadeOnly = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: transitions.snappy },
};
/** Spring entrance for compact status badges. */
export const scaleUp = {
  hidden: { opacity: 0, scale: 0.92 },
  visible: { opacity: 1, scale: 1, transition: transitions.bounce },
};
/** Fade a loading skeleton container in without moving its layout. */
export const skeletonFade = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: transitions.snappy },
};
/** Restrained repeating pulse for critical live status indicators only. */
export const pulse = {
  hidden: { opacity: 0.4 },
  visible: { opacity: [0.4, 1, 0.4], transition: { duration: 2, repeat: Infinity, ease: 'easeInOut' } },
};
/** Parent variant that staggers child transitions by 50 milliseconds. */
export const staggerContainer = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.05, delayChildren: 0 } },
};
/** Small opacity and vertical reveal for children of staggerContainer. */
export const staggerItem = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: transitions.snappy },
};
export const durations = {
  instant: 0.15,
  quick: 0.25,
  normal: 0.3,
  slow: 0.5,
  deliberate: 0.8,
  long: 1.2,
};
export const viewportConfig = { once: true, amount: 0.2, margin: '50px' };
