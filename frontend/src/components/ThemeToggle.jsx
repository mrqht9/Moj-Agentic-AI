import { Moon, Sun } from 'lucide-react'
import { Button } from './ui/button'

export const ThemeToggle = ({ darkMode, setDarkMode }) => {
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => setDarkMode(!darkMode)}
      aria-label="Toggle theme"
    >
      {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  )
}
