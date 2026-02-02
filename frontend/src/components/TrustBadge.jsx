export const TrustBadge = ({ icon: Icon, label }) => {
  return (
    <div className="flex items-center gap-2 rounded-full border border-border-light/60 bg-card-light px-4 py-2 text-sm dark:border-border-dark/60 dark:bg-card-dark">
      {Icon ? <Icon className="h-4 w-4 text-primary" /> : null}
      <span className="font-medium">{label}</span>
    </div>
  )
}
