import PropTypes from 'prop-types';
import { cn } from '../../lib/utils';

export default function Button({ children, variant = 'primary', className = '', ...props }) {
  const styles = {
    primary: 'bg-accent-blue text-slate-950 hover:bg-blue-400',
    secondary: 'bg-slate-800 text-white border border-slate-600 hover:bg-slate-700',
    ghost: 'bg-transparent text-slate-200 border border-slate-700 hover:bg-slate-800',
  };

  return (
    <button
      className={cn(
        'inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold shadow-sm focus:outline-none focus:ring-2 focus:ring-accent-blue focus:ring-offset-2 focus:ring-offset-slate-950',
        styles[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

Button.propTypes = {
  children: PropTypes.node.isRequired,
  variant: PropTypes.oneOf(['primary', 'secondary', 'ghost']),
  className: PropTypes.string,
};
