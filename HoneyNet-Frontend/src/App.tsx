import { Routes, Route, Navigate } from "react-router-dom";

import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";

// Pages
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import Sessions from "./pages/Sessions";
import SessionDetail from "./pages/SessionDetail";
import AttackAnalytics from "./pages/AttackAnalytics";
import Distribution from "./pages/Distribution";
import Map from "./pages/Map";

export default function App() {
  return (
    <Routes>

      
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      {/* Default Redirect */}
      <Route path="/" element={<Navigate to="/login" replace />} />

      {/* Protected Routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Layout>
              <Dashboard />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/sessions"
        element={
          <ProtectedRoute>
            <Layout>
              <Sessions />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/sessions/:id"
        element={
          <ProtectedRoute>
            <Layout>
              <SessionDetail />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/analytics"
        element={
          <ProtectedRoute>
            <Layout>
              <AttackAnalytics />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/distribution"
        element={
          <ProtectedRoute>
            <Layout>
              <Distribution />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/location"
        element={
          <ProtectedRoute>
            <Layout>
              <Map />
            </Layout>
          </ProtectedRoute>
        }
      />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/login" replace />} />

    </Routes>
  );
}