export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-6 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p>© {new Date().getFullYear()} Rural Health Assistant · AI-Driven Healthcare Assistance Platform</p>
        <p>Milestone 1 · Patient &amp; Healthcare Information Management</p>
      </div>
    </footer>
  )
}
