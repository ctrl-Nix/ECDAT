import PropTypes from 'prop-types';
import { cn } from '../../lib/utils';

export default function Input({ className = '', error = false, ...props }) {
  return (
    <input
      className={cn(
        'w-full rounded-lg border bg-slate-900 px-3 py-2.5 text-sm text-slate-50 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-accent-blue',
        error ? 'border-red-500' : 'border-slate-700',
        className,
      )}
      {...props}
    />
  );
}

Input.propTypes = {
  className: PropTypes.string,
  error: PropTypes.bool,
};
