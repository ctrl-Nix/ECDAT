import PropTypes from 'prop-types';
import { cn } from '../../lib/utils';

export default function Card({ children, className = '', ...props }) {
  return (
    <div
      className={cn(
        'rounded-12 border border-slate-700 bg-slate-900/80 shadow-sm',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

Card.propTypes = {
  children: PropTypes.node.isRequired,
  className: PropTypes.string,
};
