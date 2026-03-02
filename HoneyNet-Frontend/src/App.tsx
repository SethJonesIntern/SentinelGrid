
import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";


import LoginPage from "./pages/Login";
import DashboardPage from "./pages/Dashboard";
import SessionsPage from "./pages/Sessions";
import SessionDetailPage from "./pages/SessionDetail";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Layout>
              <DashboardPage />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/sessions"
        element={
          <ProtectedRoute>
            <Layout>
              <SessionsPage />
            </Layout>
          </ProtectedRoute>
        }
      />
  <Route
  path="/sessions/:sessionId"
  element={
    <ProtectedRoute>
      <Layout>
        <SessionDetailPage />
      </Layout>
    </ProtectedRoute>
  }
/>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}