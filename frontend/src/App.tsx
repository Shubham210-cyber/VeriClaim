import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import ClaimDetailPage from './pages/ClaimDetailPage'
import ClaimsQueue from './pages/ClaimsQueue'
import CustomerUpload from './pages/CustomerUpload'
import NewClaim from './pages/NewClaim'

export default function App() {
  return (
    <BrowserRouter>
      <div className="banner" role="note">Synthetic Hackathon Data — Not a Real Insurance Decision</div>
      <Routes>
        <Route path="/customer-upload/:token" element={<main className="container"><CustomerUpload /></main>} />
        <Route path="*" element={
          <>
            <nav className="nav"><Link to="/" className="brand">ClaimProof</Link><span className="muted small">Evidence-based claim review · reviewer workspace</span></nav>
            <main className="container">
              <Routes>
                <Route path="/" element={<ClaimsQueue />} />
                <Route path="/claims/new" element={<NewClaim />} />
                <Route path="/claims/:id" element={<ClaimDetailPage />} />
                <Route path="*" element={<p>Page not found. <Link to="/">Back to queue</Link></p>} />
              </Routes>
            </main>
          </>
        } />
      </Routes>
    </BrowserRouter>
  )
}
