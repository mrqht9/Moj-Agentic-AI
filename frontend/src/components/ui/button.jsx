export const Button = ({
  className = '',
  variant = 'default',
  size = 'md',
  type = 'button',
  onClick,
  children,
  disabled,
}) => {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-60 disabled:pointer-events-none'

  const variants = {
    default:
      'bg-primary text-white hover:opacity-95',
    ghost:
      'bg-transparent text-text-primary-light hover:bg-accent-light dark:text-text-primary-dark dark:hover:bg-card-dark',
    hero:
      'bg-primary text-white hover:opacity-95 shadow-sm',
    'hero-outline':
      'border border-border-light bg-transparent text-text-primary-light hover:bg-accent-light dark:border-border-dark dark:text-text-primary-dark dark:hover:bg-card-dark',
  }

  const sizes = {
    sm: 'h-9 px-3 text-sm',
    md: 'h-10 px-4 text-sm',
    lg: 'h-12 px-6 text-base',
  }

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${variants[variant] ?? variants.default} ${sizes[size] ?? sizes.md} ${className}`}
    >
      {children}
    </button>
  )
}
