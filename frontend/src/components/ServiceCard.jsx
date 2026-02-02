export const ServiceCard = ({ icon: Icon, title, description, delay = 0 }) => {
  return (
    <div
      className="animate-fade-in rounded-2xl border border-border-light/60 bg-card-light p-4 shadow-sm dark:border-border-dark/60 dark:bg-card-dark"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-accent-light text-primary dark:bg-navy-medium dark:text-text-primary-dark">
        {Icon ? <Icon className="h-5 w-5" /> : null}
      </div>
      <h3 className="mb-1 text-sm font-bold sm:text-base">{title}</h3>
      <p className="text-xs text-text-secondary-light dark:text-text-secondary-dark sm:text-sm">{description}</p>
    </div>
  )
}
