import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import ClaimDetailPage from './pages/ClaimDetailPage'
import ClaimsQueue from './pages/ClaimsQueue'
import CustomerUpload from './pages/CustomerUpload'
import NewClaim from './pages/NewClaim'

const Logo = () => (
  <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden>
    <rect width="32" height="32" rx="8" fill="var(--accent)" />
    <path d="M16 6l8 3v6c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10V9z" fill="none" stroke="#fff" strokeWidth="2" />
    <path d="M12.5 15.5l2.5 2.5 4.5-5" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

const Footer = () => (
  <footer className="footer">
    Demo environment: all claims, people, devices and policies are synthetic. Recommendations are decision support for a human
    reviewer and are not real insurance decisions.
  </footer>
)

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/customer-upload/:token" element={<><main className="container"><CustomerUpload /></main><Footer /></>} />
        <Route path="*" element={
          <>
            <nav className="nav">
              <Link to="/" className="brand"><Logo />VeriClaim</Link>
              <span className="tagline">Evidence-based claim review</span>
              <span className="pill" title="All data in this environment is synthetic">Demo data</span>
            </nav>
            <main className="container">
              <Routes>
                <Route path="/" element={<ClaimsQueue />} />
                <Route path="/claims/new" element={<NewClaim />} />
                <Route path="/claims/:id" element={<ClaimDetailPage />} />
                <Route path="*" element={<p>Page not found. <Link to="/">Back to claims</Link></p>} />
              </Routes>
            </main>
            <Footer />
          </>
        } />
      </Routes>
    </BrowserRouter>
  )
}
