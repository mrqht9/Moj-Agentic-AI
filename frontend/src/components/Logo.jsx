import logoDark from '../assets/logos/logo-dark.png'
import logoLight from '../assets/logos/logo-light.png'

export const Logo = ({ size = 'md', className = '' }) => {
  const sizes = {
    sm: 'h-7',
    md: 'h-9',
    lg: 'h-12',
  }

  const heightClass = sizes[size] ?? sizes.md

  return (
    <div className={`flex items-center ${className}`}>
      <img
        src={logoDark}
        alt="MWJ"
        className={`${heightClass} w-auto dark:hidden`}
        draggable={false}
      />
      <img
        src={logoLight}
        alt="MWJ"
        className={`${heightClass} hidden w-auto dark:block`}
        draggable={false}
      />
    </div>
  )
}
