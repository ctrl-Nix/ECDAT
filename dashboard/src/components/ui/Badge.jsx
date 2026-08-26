import PropTypes from 'prop-types';
import { cn } from '../../lib/utils';

export default function Badge({ children, variant = 'default', className = '' }) {
  const styles = {
    default: 'bg-slate-800 text-slate-200 border border-slate-700',
    critical: 'bg-red-500/10 text-red-300 border border-red-500/30',
    high: 'bg-amber-500/10 text-amber-300 border border-amber-500/30',
    medium: 'bg-blue-500/10 text-blue-300 border border-blue-500/30',
    low: 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30',
  };

  return (
    <span className={cn('inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium', styles[variant], className)}>
      {children}
    </span>
  );
}

Badge.propTypes = {
  children: PropTypes.node.isRequired,
  variant: PropTypes.oneOf(['default', 'critical', 'high', 'medium', 'low']),
  className: PropTypes.string,
};
