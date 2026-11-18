import { Navigate, Route, Routes } from 'react-router-dom'
import Footer from './components/Footer'
import Navbar from './components/Navbar'
import ProtectedRoute from './components/ProtectedRoute'
import AdminDashboard from './pages/AdminDashboard'
import Assistant from './pages/Assistant'
import DocumentInsight from './pages/DocumentInsight'
import CareTeam from './pages/CareTeam'
import Documents from './pages/Documents'
import HealthInfo from './pages/HealthInfo'
import Home from './pages/Home'
import Login from './pages/Login'
import MedicalHistory from './pages/MedicalHistory'
import NotFound from './pages/NotFound'
import PatientDashboard from './pages/PatientDashboard'
import Profile from './pages/Profile'
import Register from './pages/Register'
import VerifyPhone from './pages/VerifyPhone'
import WorkerDashboard from './pages/WorkerDashboard'
import WorkerPatientView from './pages/WorkerPatientView'

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify-phone" element={<VerifyPhone />} />
          <Route path="/health-info" element={<HealthInfo />} />

          <Route element={<ProtectedRoute />}>
            <Route path="/profile" element={<Profile />} />
          </Route>

          <Route element={<ProtectedRoute roles={['PATIENT']} />}>
            <Route path="/patient" element={<PatientDashboard />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/history" element={<MedicalHistory />} />
            <Route path="/care-team" element={<CareTeam />} />
          </Route>

          <Route element={<ProtectedRoute roles={['PATIENT', 'HEALTHCARE_WORKER']} />}>
            <Route path="/assistant" element={<Assistant />} />
            <Route path="/documents/:documentId/explain" element={<DocumentInsight />} />
          </Route>

          <Route element={<ProtectedRoute roles={['HEALTHCARE_WORKER']} />}>
            <Route path="/worker" element={<WorkerDashboard />} />
            <Route path="/worker/patients/:patientId" element={<WorkerPatientView />} />
          </Route>

          <Route element={<ProtectedRoute roles={['ADMIN']} />}>
            <Route path="/admin" element={<AdminDashboard />} />
          </Route>

          <Route path="/dashboard" element={<Navigate to="/" replace />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
